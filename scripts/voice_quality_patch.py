#!/usr/bin/env python3
"""Patch a pinned VoiceStudio Android checkout for a separate, experimental voice lab.
This script is intentionally strict: unexpected upstream source causes a build failure.
Source: debpalash/VoiceStudio at 429f1e5bb2703ac5b928ab8ba6f60159167e9c44.
"""
from pathlib import Path
import json
import re
import sys
import urllib.request

root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path("voicestudio").resolve()

def patch(relative, before, after):
    p = root / relative
    s = p.read_text()
    assert s.count(before) == 1, f"Expected exactly one anchor in {relative}: {before[:110]!r} (found {s.count(before)})"
    p.write_text(s.replace(before, after))

local_base = "mobile/android/core/local/src/main/kotlin/com/voicestudio/mobile/local/"
feature_base = "mobile/android/features/src/main/kotlin/com/voicestudio/mobile/features/"

(root / (local_base + "SmartVoiceReference.kt")).write_text(r'''package com.voicestudio.mobile.local

import kotlin.math.abs
import kotlin.math.ln
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

/** The 90-second recording is a source pool, not 90 seconds sent to a TTS model.
 * Candidate selection is a signal heuristic, not speech recognition or speaker verification.
 */
object SmartVoiceReference {
    data class Choice(val audio: LocalAudio, val startSeconds: Int, val note: String)
    private data class Window(val start: Int, val score: Double)
    fun select(source: LocalAudio, candidate: Int = 0, cleanup: Boolean = true): Choice {
        require(source.sampleRate == 24000 && source.samples.isNotEmpty())
        require(source.samples.size <= 90 * 24000)
        require(candidate in 0..2)
        val data = source.samples
        val length = min(data.size, 12 * source.sampleRate)
        val stride = 2 * source.sampleRate
        val positions = if (data.size <= length) listOf(0) else
            ((0..(data.size-length) step stride).toList() + (data.size-length)).distinct()
        val windows = positions.map {start -> Window(start, score(data, start, length))}.sortedByDescending {it.score}
        val distinct = mutableListOf<Window>()
        for (window in windows) {
            if (distinct.none { abs(it.start-window.start) < 6*source.sampleRate }) distinct.add(window)
            if (distinct.size == 3) break
        }
        val chosen = distinct.getOrElse(candidate) {distinct.first()}
        val segment = data.copyOfRange(chosen.start, chosen.start+length)
        val maxPeak = segment.maxOf {abs(it)}
        val clipped = segment.count {abs(it) > .985f}
        var note = when {
            clipped > segment.size/250 -> "Potential clipping: try a quieter recording"
            chosen.score < .1 -> "Weak or uneven signal: try recording closer to the microphone"
            else -> "Selected a speech-rich passage from your recording"
        }
        if (cleanup) {
            // Gentle DC subtraction and fades; no aggressive denoiser that would alter timbre.
            var baseline = 0f
            for (i in segment.indices) {
                baseline = baseline*.997f + segment[i]*.003f
                segment[i] -= baseline
            }
            val peak = segment.maxOf {abs(it)}
            val gain = if(peak > .05f && peak < .65f) min(1.8f,.78f/peak) else 1f
            val fade = min(240,segment.size/3)
            for (i in segment.indices) {
                val edge = min(i,segment.lastIndex-i)
                val multiplier = if (edge < fade) edge.toFloat()/max(1,fade) else 1f
                segment[i] = (segment[i]*gain*multiplier).coerceIn(-1f,1f)
            }
        }
        return Choice(LocalAudio(segment,source.sampleRate),chosen.start/source.sampleRate,note)
    }
    private fun score(audio:FloatArray,start:Int,length:Int):Double {
        val frameSize = 2400 // 100 ms
        val rms = mutableListOf<Double>()
        var clipping = 0
        var points = 0
        for (at in start until start+length step frameSize) {
            var sq=0.0
            val end=min(at+frameSize,start+length)
            for (i in at until end step 5) {
                val v=audio[i]
                sq += v*v
                if (abs(v) >= .985f) clipping++
                points++
            }
            rms.add(sqrt(sq/max(1,(end-at+4)/5)))
        }
        val peak = rms.maxOrNull() ?: return -1.0
        val voiced = rms.count {it > max(.006,peak*.15) }.toDouble()/max(1,rms.size)
        val average = rms.average()
        val variability = if(average>0) rms.map{abs(it-average)}.average()/average else 2.0
        return voiced*3.0 + min(1.0,average*12.0) - min(1.2,variability*.35) -
            (clipping.toDouble()/max(1,points))*35.0
    }

    /** Rough F0 proximity of reference and preview, NOT speaker-identity confidence. */
    fun pitchProximity(reference: LocalAudio, output: LocalAudio): Int? {
        val a=medianPitch(reference)
        val b=medianPitch(output)
        if (a == null || b == null) return null
        val semitones = 12.0*abs(ln(a/b))/ln(2.0)
        return (100.0-7.0*semitones).toInt().coerceIn(0,100)
    }
    private fun medianPitch(audio:LocalAudio):Double? {
        if(audio.sampleRate != 24000) return null
        val samples=audio.samples
        val results=mutableListOf<Double>()
        val window=1920
        for (offset in 0..max(0,samples.size-window) step 12000) {
            if(offset+window>samples.size) break
            var energy=0.0
            for(i in 0 until window step 4) energy+=samples[offset+i]*samples[offset+i]
            if(energy < .002) continue
            var best=0.0
            var lag=0
            for(candidate in 80..300 step 2) {
                var numerator=0.0;var denom=0.0
                for(i in 300 until window step 3) {
                    val x=samples[offset+i].toDouble()
                    val y=samples[offset+i-candidate].toDouble()
                    numerator+=x*y
                    denom+=x*x+y*y
                }
                val corr=if(denom>0) (2*numerator/denom) else 0.0
                if(corr>best) {best=corr;lag=candidate}
            }
            if(best>.52&&lag>0) results.add(24000.0/lag)
        }
        if(results.size<2) return null
        return results.sorted()[results.size/2]
    }
}
''')

# Keep saved voices <=30 seconds even when the source recording is 90 seconds.
voice = local_base + "PhoneVoices.kt"
patch(voice,
'''    val modelRepo: String? = null, val modelRevision: String? = null, val designInstruction: String? = null, val designSeed: Long? = null,val sourceAttribution: Map<String,String>?=null)''',
'''    val modelRepo: String? = null, val modelRevision: String? = null, val designInstruction: String? = null, val designSeed: Long? = null,val sourceAttribution: Map<String,String>?=null,
    val selectedFromSecond: Int? = null, val referenceNote: String? = null, val pitchProximity: Int? = null)''')
patch(voice,
'''        decoder: AudioDecoder = AndroidAudioDecoder(), progress: (Float)->Unit = {}): PhoneVoice = withContext(Dispatchers.IO) {''',
'''        decoder: AudioDecoder = AndroidAudioDecoder(), progress: (Float)->Unit = {}, candidateIndex: Int = 0, cleanup: Boolean = true): PhoneVoice = withContext(Dispatchers.IO) {''')
patch(voice,
'''            val audio=decoder.decode(source,File(dir,"reference.pcm"),30) {progress(it*.25f)}
            val transcript=engine.transcribe(asr,audio.read(0,audio.frames.toInt())) {progress(.25f+it*.25f)}.trim()
            if(transcript.isEmpty()) throw ClientFailure("mobile.simple.no_speech")
            writeReferenceWave(audio.read(0,audio.frames.toInt()),File(dir,"reference.wav"))
            val preview=engine.clone(cloneModel,transcript,audio.read(0,audio.frames.toInt()),transcript) {progress(.5f+it*.5f)}''',
'''            val decoded=decoder.decode(source,File(dir,"reference.pcm"),90) {progress(it*.20f)}
            val chosen=SmartVoiceReference.select(decoded.read(0,decoded.frames.toInt()),candidateIndex,cleanup)
            val reference=chosen.audio
            writePcm(reference,File(dir,"reference.pcm"))
            val transcript=engine.transcribe(asr,reference) {progress(.20f+it*.30f)}.trim()
            if(transcript.isEmpty()) throw ClientFailure("mobile.simple.no_speech")
            writeReferenceWave(reference,File(dir,"reference.wav"))
            val preview=engine.clone(cloneModel,transcript,reference,transcript) {progress(.5f+it*.5f)}''')
patch(voice,
'''            val voice=PhoneVoice(id,name.trim(),transcript,now,now,modelRepo=cloneModel.repo,modelRevision=cloneModel.revision)''',
'''            val pitch=SmartVoiceReference.pitchProximity(reference,preview)
            val voice=PhoneVoice(id,name.trim(),transcript,now,now,modelRepo=cloneModel.repo,modelRevision=cloneModel.revision,
                selectedFromSecond=chosen.startSeconds,referenceNote=chosen.note,pitchProximity=pitch)''')

# UI: longer recording, selectable reference windows, optional three-voice A/B creation.
voices_ui = feature_base + "voices/VoicesScreen.kt"
patch(voices_ui,
'''    var recording by remember {mutableStateOf(false)}
    var seconds by remember {mutableIntStateOf(0)}''',
'''    var recording by remember {mutableStateOf(false)}
    var seconds by remember {mutableIntStateOf(0)}
    var candidateIndex by rememberSaveable {mutableIntStateOf(0)}
    var cleanReference by rememberSaveable {mutableStateOf(true)}''')
patch(voices_ui,'''        if(seconds>=29)''','''        if(seconds>=89)''')
patch(voices_ui,
'''        if(sample!=null&&!recording) Text(tr("mobile.android.sample_ready"))
        Action("mobile.voices.new_clone",permission&&sample!=null&&name.isNotBlank()&&!state.busy&&!recording&&phone.progress==null&&(location==RunLocation.COMPUTER||cloneReady)) {
            if(location==RunLocation.COMPUTER) vm.clone(name,File(sample!!),hasConsent={permission&&cloning}) {if(cloning) {sample=null;name="";permission=false;cloning=false;onCreated()}}
            else vm.phone.clone(name,File(sample!!),asr!!,model!!,permission) {sample=null;name="";permission=false;cloning=false;onCreated()}
        }''',
'''        if(sample!=null&&!recording) {
            Text(tr("mobile.android.sample_ready"))
            if(location!=RunLocation.COMPUTER) {
                Text("Smart Voice Capture uses up to 90 seconds, choosing a 12-second passage for the model.",style=MaterialTheme.typography.bodySmall)
                Text("Reference passage",style=MaterialTheme.typography.titleSmall)
                Row(horizontalArrangement=Arrangement.spacedBy(6.dp)) {
                    listOf("Best","Alternate 2","Alternate 3").forEachIndexed {index,label ->
                        FilterChip(selected=candidateIndex==index,onClick={candidateIndex=index},label={Text(label)})
                    }
                }
                Row(verticalAlignment=Alignment.CenterVertically) {
                    Checkbox(checked=cleanReference,onCheckedChange={cleanReference=it})
                    Text("Gentle cleanup: reduce rumble and correct low volume",style=MaterialTheme.typography.bodySmall)
                }
            }
        }
        Action("mobile.voices.new_clone",permission&&sample!=null&&name.isNotBlank()&&!state.busy&&!recording&&phone.progress==null&&(location==RunLocation.COMPUTER||cloneReady)) {
            if(location==RunLocation.COMPUTER) vm.clone(name,File(sample!!),hasConsent={permission&&cloning}) {if(cloning) {sample=null;name="";permission=false;cloning=false;onCreated()}}
            else vm.phone.clone(name,File(sample!!),asr!!,model!!,permission,
                created={sample=null;name="";permission=false;cloning=false;onCreated()},
                candidateIndex=candidateIndex,cleanup=cleanReference)
        }
        if(location!=RunLocation.COMPUTER && sample!=null && !recording) {
            Text("Voice comparison creates three independent saved profiles, so you can listen and choose. Initial setup is approximately three times slower.",style=MaterialTheme.typography.bodySmall)
            Button(enabled=permission&&name.isNotBlank()&&!state.busy&&cloneReady&&phone.progress==null,
                onClick={vm.phone.cloneVariants(name,File(sample!!),asr!!,model!!,permission,
                    created={sample=null;name="";permission=false;cloning=false;onCreated()},cleanup=cleanReference)}) {
                Text("Create 3 voice candidates")
            }
        }''')
patch(voices_ui,
'''                        LocationBadge(local(profile)!=null)
                    }''',
'''                        LocationBadge(local(profile)!=null)
                        local(profile)?.selectedFromSecond?.let {start ->
                            Text("Reference selected at "+start+"s",style=MaterialTheme.typography.bodySmall,color=role("textMuted"))
                        }
                        local(profile)?.referenceNote?.let {note ->
                            Text(note,style=MaterialTheme.typography.bodySmall,color=role("textMuted"))
                        }
                        local(profile)?.pitchProximity?.let {score ->
                            Text("Pitch proximity ~"+score+"% (NOT a voice identity score)",style=MaterialTheme.typography.bodySmall,color=role("textMuted"))
                        }
                    }''')
# Imported/uploaded clone can also be 90s, but only 12 seconds will persist after selection.
patch(voices_ui,'''        if(recording) {
            Text(tr("mobile.voices.recording",mapOf("seconds" to seconds)))''',
'''        if(recording) {
            Text("Recording "+seconds+" / 90 seconds")
            Text(tr("mobile.voices.recording",mapOf("seconds" to seconds)))''')

phone_studio = feature_base + "PhoneStudio.kt"
patch(phone_studio,
'''    fun speak(model: PhoneModel, text: String, speaker: Int, voice: PhoneVoice? = null, language: String? = null) {''',
'''    fun speak(model: PhoneModel, text: String, speaker: Int, voice: PhoneVoice? = null, language: String? = null, qualitySteps: Int? = null) {''')
patch(phone_studio,
'''                val audio=if(voice==null) engine.synthesize(model,text,speaker,language=language,progress=report)
                    else engine.clone(model,text,voices.reference(voice),voice.transcript,progress=report)''',
'''                // Quality only affects generation; model files, signature and licences remain identical.
                val chosenModel = if (model.option("model_type")=="pocket" && qualitySteps in setOf(4,10,20))
                    model.copy(config=kotlinx.serialization.json.JsonObject(model.config + ("num_steps" to kotlinx.serialization.json.JsonPrimitive(qualitySteps!!))))
                    else model
                val audio=if(voice==null) engine.synthesize(chosenModel,text,speaker,language=language,progress=report)
                    else engine.clone(chosenModel,text,voices.reference(voice),voice.transcript,progress=report)''')
patch(phone_studio,
'''retryFailure(e) {speak(model,text,speaker,voice,language)}''',
'''retryFailure(e) {speak(model,text,speaker,voice,language,qualitySteps)}''')
patch(phone_studio,
'''    fun clone(name: String, file: File, model: PhoneModel, cloneModel: PhoneModel, consent: Boolean, created: ()->Unit = {}) {''',
'''    fun clone(name: String, file: File, model: PhoneModel, cloneModel: PhoneModel, consent: Boolean,
        created: ()->Unit = {}, candidateIndex: Int = 0, cleanup: Boolean = true) {''')
patch(phone_studio,
'''try {voices.create(name,file,consent,model,cloneModel,engine,progress={p -> mutable.update {it.copy(progress=p)}});refresh();withContext(Dispatchers.IO) {file.delete()};created()}
            catch(e:CancellationException) {throw e} catch(e:Exception) {retryFailure(e) {clone(name,file,model,cloneModel,consent,created)}}''',
'''try {voices.create(name,file,consent,model,cloneModel,engine,
                    progress={p -> mutable.update {it.copy(progress=p)}},candidateIndex=candidateIndex,cleanup=cleanup)
                refresh();withContext(Dispatchers.IO) {file.delete()};created()}
            catch(e:CancellationException) {throw e} catch(e:Exception) {retryFailure(e) {clone(name,file,model,cloneModel,consent,created,candidateIndex,cleanup)}}''')
patch(phone_studio,
'''    fun renameVoice(voice: PhoneVoice, name: String) {scope.launch''',
'''    /** An explicit A/B experiment. Only short selected references are sent to the engine. */
    fun cloneVariants(name: String,file: File,asr: PhoneModel,cloneModel: PhoneModel,consent:Boolean,
        created:()->Unit={},cleanup:Boolean=true) {
        if(inference?.isActive==true) return
        inference=scope.launch {
            mutable.update {it.copy(progress=0f)}
            try {
                val names=listOf("Best reference","Alternate 2","Alternate 3")
                for (index in 0..2) {
                    ensureActive()
                    voices.create(name+" - "+names[index],file,consent,asr,cloneModel,engine,
                        progress={p -> mutable.update {it.copy(progress=(index+p)/3f)}},
                        candidateIndex=index,cleanup=cleanup)
                    refresh()
                }
                withContext(Dispatchers.IO) {file.delete()}
                created()
            } catch(e:CancellationException) {throw e}
            catch(e:Exception) {retryFailure(e) {}}
            finally {mutable.update {it.copy(progress=null)}}
        }
    }
    fun renameVoice(voice: PhoneVoice, name: String) {scope.launch''')

speak = feature_base + "speak/SpeakScreen.kt"
patch(speak,
'''            var language by rememberSaveable {mutableStateOf("en")}''',
'''            var language by rememberSaveable {mutableStateOf("en")}
            var qualitySteps by rememberSaveable {mutableIntStateOf(10)}''')
patch(speak,
'''vm.phone.speak(selected!!,text,speaker.toIntOrNull() ?: 0,voice,language.takeUnless {it=="auto"})''',
'''vm.phone.speak(selected!!,text,speaker.toIntOrNull() ?: 0,voice,language.takeUnless {it=="auto"},
                         qualitySteps=if(selected!!.option("model_type")=="pocket") qualitySteps else null)''')
patch(speak,
'''                com.voicestudio.mobile.features.models.ModelRamWarning(vm,listOfNotNull(selected))''',
'''                if(selected?.option("model_type")=="pocket") {
                    Text("Pocket TTS quality / speed",style=MaterialTheme.typography.titleSmall)
                    Text("More steps may smooth speech, but cannot guarantee closer voice resemblance.",style=MaterialTheme.typography.bodySmall,color=role("textMuted"))
                    Row(horizontalArrangement=Arrangement.spacedBy(6.dp)) {
                        listOf(4 to "Fast",10 to "Balanced",20 to "Detailed").forEach {(steps,label) ->
                            FilterChip(selected=qualitySteps==steps,onClick={qualitySteps=steps},label={Text(label)})
                        }
                    }
                    Text("Quick comparison: generate identical text with the same voice and each setting.",style=MaterialTheme.typography.bodySmall)
                }
                com.voicestudio.mobile.features.models.ModelRamWarning(vm,listOfNotNull(selected))''')

# The catalogue already offers ZipVoice, which is a meaningful alternative model.
# Add an OPTIONAL full-precision Pocket model with revision and exact file hashes from Hugging Face.
# If the hub is unavailable, leave the tested INT8 engine operational instead of publishing guesses.
catalog = root / "mobile/contract/models.json"
data = json.loads(catalog.read_text())
assert any(m["id"]=="pocket-tts-int8-en" for m in data["models"])
assert any(m["id"]=="zipvoice-distill-int8-zh-en" for m in data["models"])
try:
    repo = "csukuangfj2/sherpa-onnx-pocket-tts-2026-01-26"
    with urllib.request.urlopen("https://huggingface.co/api/models/"+repo,timeout=25) as r:
        metadata=json.load(r)
    revision=metadata["sha"]
    assert re.fullmatch(r"[0-9a-f]{40}",revision)
    assert revision.startswith("96d1e53"), "Upstream precision model changed; manual review required"
    with urllib.request.urlopen("https://huggingface.co/api/models/"+repo+"/tree/"+revision+"?recursive=true",timeout=25) as r:
        entries=json.load(r)
    by_path={e["path"]:e for e in entries}
    filenames={
      "lm_flow.onnx":"lm-flow","lm_main.onnx":"lm-main","encoder.onnx":"encoder",
      "decoder.onnx":"decoder","text_conditioner.onnx":"text-conditioner",
      "vocab.json":"vocab","token_scores.json":"token-scores"}
    files=[]
    for filename,role in filenames.items():
        item=by_path[filename]
        sha=(item.get("lfs") or {}).get("oid") or item.get("oid")
        size=item.get("size")
        if not sha and filename in ("token_scores.json","vocab.json"):
            original=next(x for x in next(m for m in data["models"] if m["id"]=="pocket-tts-int8-en")["files"] if x["path"]==filename)
            assert original["size"] == size, "Changed vocabulary metadata requires review"
            sha=original["sha256"]
        assert re.fullmatch("[0-9a-f]{64}",str(sha)) and isinstance(size,int) and size>0, f"Missing verified metadata for {filename}"
        files.append({"path":filename,"size":size,"sha256":sha,"role":role})
    base=next(m for m in data["models"] if m["id"]=="pocket-tts-int8-en")
    variant=json.loads(json.dumps(base))
    variant.update({
        "id":"pocket-tts-fp32-en",
        "name":"Pocket TTS Quality (FP32)",
        "repo":repo,
        "revision":revision,
        "files":files,
        "total_bytes":sum(f["size"] for f in files),
        "min_ram_gb":4
    })
    variant["config"]["num_steps"]=10
    variant["licence"]["terms"]["source_url"]="https://huggingface.co/"+repo
    variant["licence"]["terms"]["evidence_url"]="https://huggingface.co/"+repo+"/blob/"+revision+"/README.md"
    import hashlib
    terms=variant["licence"]["terms"]
    terms["notes"]="Optional FP32 ONNX conversion; reference voice permission required; non-commercial restriction remains."
    variant["licence"]["terms_fingerprint"]=hashlib.sha256(json.dumps(terms,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    data["models"].append(variant)
    print("Added pinned FP32 Pocket TTS option; total bytes",variant["total_bytes"])
except Exception as error:
    print("INFO: FP32 catalogue unavailable; keeping verified INT8, ZipVoice and OmniVoice only:",repr(error))
catalog.write_text(json.dumps(data,indent=2)+"\n")
print("Applied VoiceStudio voice lab patch: 90s source capture, best 12s reference, gentle cleanup, 3 candidates, pitch proximity estimate, Pocket quality controls, ZipVoice comparison, optional FP32.")
