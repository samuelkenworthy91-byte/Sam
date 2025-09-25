from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, date, time, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os
import uuid
import asyncio
import math
from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Workflow Organizer API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "workflow_organizer")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Pydantic models
class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    deadline: str  # ISO format date
    priority: str = "medium"  # low, medium, high
    complexity: str = "medium"  # small, medium, large
    estimated_hours: float = 0
    actual_hours: Optional[float] = None
    status: str = "pending"  # pending, in_progress, completed
    tags: List[str] = []
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ai_analysis: Optional[str] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[str] = None
    priority: Optional[str] = None
    actual_hours: Optional[float] = None
    status: Optional[str] = None

class Schedule(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    day_of_week: str  # monday, tuesday, etc.
    start_time: str  # HH:MM format
    end_time: str  # HH:MM format
    activity_type: str  # work, teaching, break
    description: Optional[str] = None

class DailyRecommendation(BaseModel):
    date: str
    tasks: List[Dict[str, Any]]
    total_hours: float
    available_hours: float
    workload_status: str  # light, moderate, heavy, overloaded

class LearningData(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    estimated_hours: float
    actual_hours: float
    accuracy_ratio: float  # actual/estimated
    complexity: str
    tags: List[str]
    completion_date: str
    notes: Optional[str] = None

# AI Helper Functions
async def get_ai_task_analysis(title: str, description: str, deadline: str) -> Dict[str, Any]:
    """Use AI to analyze task and provide estimates"""
    try:
        # Initialize LLM chat
        chat = LlmChat(
            api_key=os.getenv("EMERGENT_LLM_KEY"),
            session_id=f"task_analysis_{uuid.uuid4()}",
            system_message="You are an expert project manager and time estimation specialist. Analyze tasks and provide accurate time estimates and complexity assessments."
        ).with_model("openai", "gpt-4o-mini")
        
        # Prepare analysis prompt
        days_until_deadline = (datetime.fromisoformat(deadline.replace('Z', '+00:00')) - datetime.now(timezone.utc)).days
        
        prompt = f"""
        Analyze this task and provide a JSON response with the following structure:
        {{
            "estimated_hours": <number>,
            "complexity": "small|medium|large",
            "suggested_tags": ["tag1", "tag2"],
            "breakdown": "Brief explanation of time estimate",
            "priority_suggestion": "low|medium|high",
            "daily_effort": <hours per day recommended>
        }}
        
        Task Details:
        - Title: {title}
        - Description: {description}
        - Deadline: {deadline} (in {days_until_deadline} days)
        
        Consider:
        1. Task complexity based on description keywords
        2. Reasonable working pace (not burnout schedule)
        3. Buffer time for unexpected issues
        4. Working hours constraint: 8 AM - 4 PM (8 hours/day max)
        5. Account for teaching breaks and reduced availability
        
        Provide only the JSON response, no additional text.
        """
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        # Parse AI response (basic JSON extraction)
        import json
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                ai_result = json.loads(response[json_start:json_end])
                return ai_result
        except:
            pass
            
        # Fallback if JSON parsing fails
        return {
            "estimated_hours": 8.0,
            "complexity": "medium",
            "suggested_tags": ["general"],
            "breakdown": "AI analysis unavailable, using default estimate",
            "priority_suggestion": "medium",
            "daily_effort": 2.0
        }
            
    except Exception as e:
        print(f"AI analysis error: {e}")
        # Fallback rule-based estimation
        return rule_based_estimation(title, description, deadline)

def rule_based_estimation(title: str, description: str, deadline: str) -> Dict[str, Any]:
    """Fallback rule-based estimation"""
    
    # Keywords for complexity assessment
    large_keywords = ['project', 'develop', 'build', 'create', 'research', 'analyze', 'comprehensive']
    medium_keywords = ['review', 'write', 'prepare', 'design', 'plan', 'organize']
    small_keywords = ['call', 'email', 'check', 'update', 'quick', 'simple']
    
    text = f"{title} {description}".lower()
    
    # Determine complexity
    if any(keyword in text for keyword in large_keywords):
        complexity = "large"
        base_hours = 12.0
    elif any(keyword in text for keyword in medium_keywords):
        complexity = "medium"  
        base_hours = 6.0
    elif any(keyword in text for keyword in small_keywords):
        complexity = "small"
        base_hours = 2.0
    else:
        complexity = "medium"
        base_hours = 6.0
    
    # Calculate days until deadline
    days_until = (datetime.fromisoformat(deadline.replace('Z', '+00:00')) - datetime.now(timezone.utc)).days
    
    # Adjust priority based on deadline urgency
    if days_until <= 1:
        priority = "high"
    elif days_until <= 3:
        priority = "medium"
    else:
        priority = "low"
    
    # Calculate daily effort needed
    work_days_available = max(1, days_until)
    daily_effort = min(6.0, base_hours / work_days_available)  # Cap at 6 hours/day
    
    # Generate suggested tags
    tags = []
    if 'teaching' in text or 'class' in text or 'lesson' in text:
        tags.append('teaching')
    if 'meeting' in text or 'presentation' in text:
        tags.append('meeting')
    if 'research' in text or 'study' in text:
        tags.append('research')
    if 'admin' in text or 'paperwork' in text:
        tags.append('admin')
    if not tags:
        tags = ['general']
    
    return {
        "estimated_hours": base_hours,
        "complexity": complexity,
        "suggested_tags": tags,
        "breakdown": f"Rule-based estimate: {complexity} complexity task requiring {base_hours} hours",
        "priority_suggestion": priority,
        "daily_effort": daily_effort
    }

def calculate_learning_insights(learning_data: List[Dict]) -> Dict[str, Any]:
    """Calculate insights from historical task completion data"""
    if not learning_data:
        return {"pace_factor": 1.0, "complexity_adjustments": {}, "tag_insights": {}}
    
    # Calculate overall pace factor (how user performs vs estimates)
    total_estimated = sum(item['estimated_hours'] for item in learning_data)
    total_actual = sum(item['actual_hours'] for item in learning_data)
    
    pace_factor = total_actual / total_estimated if total_estimated > 0 else 1.0
    
    # Calculate complexity-specific adjustments
    complexity_adjustments = {}
    for complexity in ['small', 'medium', 'large']:
        complexity_items = [item for item in learning_data if item['complexity'] == complexity]
        if complexity_items:
            est_sum = sum(item['estimated_hours'] for item in complexity_items)
            act_sum = sum(item['actual_hours'] for item in complexity_items)
            complexity_adjustments[complexity] = act_sum / est_sum if est_sum > 0 else 1.0
    
    # Tag-based insights
    tag_insights = {}
    all_tags = set()
    for item in learning_data:
        all_tags.update(item['tags'])
    
    for tag in all_tags:
        tag_items = [item for item in learning_data if tag in item['tags']]
        if tag_items:
            est_sum = sum(item['estimated_hours'] for item in tag_items)
            act_sum = sum(item['actual_hours'] for item in tag_items)
            tag_insights[tag] = act_sum / est_sum if est_sum > 0 else 1.0
    
    return {
        "pace_factor": pace_factor,
        "complexity_adjustments": complexity_adjustments,
        "tag_insights": tag_insights
    }

# Helper functions
def prepare_for_mongo(data):
    """Convert data for MongoDB storage"""
    if isinstance(data, dict):
        return {k: prepare_for_mongo(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [prepare_for_mongo(item) for item in data]
    elif isinstance(data, datetime):
        return data.isoformat()
    elif isinstance(data, date):
        return data.isoformat()
    elif isinstance(data, time):
        return data.strftime('%H:%M:%S')
    return data

def parse_from_mongo(item):
    """Parse data from MongoDB"""
    from bson import ObjectId
    if isinstance(item, dict):
        # Remove MongoDB's _id field to avoid ObjectId serialization issues
        return {k: parse_from_mongo(v) for k, v in item.items() if k != '_id'}
    elif isinstance(item, list):
        return [parse_from_mongo(i) for i in item]
    elif isinstance(item, ObjectId):
        return str(item)
    return item

# API Routes

@app.get("/")
async def root():
    return {"message": "Workflow Organizer API is running!"}

@app.post("/api/tasks", response_model=Task)
async def create_task(task: Task):
    try:
        # Get AI analysis for the task
        ai_analysis = await get_ai_task_analysis(task.title, task.description, task.deadline)
        
        # Update task with AI insights
        task.estimated_hours = ai_analysis.get('estimated_hours', task.estimated_hours)
        task.complexity = ai_analysis.get('complexity', task.complexity)
        if ai_analysis.get('suggested_tags'):
            task.tags.extend(ai_analysis['suggested_tags'])
        task.ai_analysis = ai_analysis.get('breakdown', '')
        
        # Prepare for database
        task_data = prepare_for_mongo(task.dict())
        
        # Insert into database
        result = await db.tasks.insert_one(task_data)
        if result.inserted_id:
            return task
        else:
            raise HTTPException(status_code=500, detail="Failed to create task")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating task: {str(e)}")

@app.get("/api/tasks", response_model=List[Task])
async def get_tasks():
    try:
        tasks = await db.tasks.find().to_list(length=None)
        return [Task(**parse_from_mongo(task)) for task in tasks]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tasks: {str(e)}")

@app.get("/api/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str):
    try:
        task = await db.tasks.find_one({"id": task_id})
        if task:
            return Task(**parse_from_mongo(task))
        else:
            raise HTTPException(status_code=404, detail="Task not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching task: {str(e)}")

@app.put("/api/tasks/{task_id}", response_model=Task)
async def update_task(task_id: str, task_update: TaskUpdate):
    try:
        # Get existing task
        existing_task = await db.tasks.find_one({"id": task_id})
        if not existing_task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Prepare update data
        update_data = {k: v for k, v in task_update.dict().items() if v is not None}
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # If task is being completed with actual hours, store learning data
        if task_update.status == "completed" and task_update.actual_hours is not None:
            learning_record = LearningData(
                task_id=task_id,
                estimated_hours=existing_task['estimated_hours'],
                actual_hours=task_update.actual_hours,
                accuracy_ratio=task_update.actual_hours / existing_task['estimated_hours'],
                complexity=existing_task['complexity'],
                tags=existing_task['tags'],
                completion_date=datetime.now(timezone.utc).isoformat(),
                notes=f"Task: {existing_task['title']}"
            )
            
            learning_data = prepare_for_mongo(learning_record.dict())
            await db.learning_data.insert_one(learning_data)
        
        # Update task
        prepared_update = prepare_for_mongo(update_data)
        result = await db.tasks.update_one({"id": task_id}, {"$set": prepared_update})
        
        if result.matched_count:
            updated_task = await db.tasks.find_one({"id": task_id})
            return Task(**parse_from_mongo(updated_task))
        else:
            raise HTTPException(status_code=404, detail="Task not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating task: {str(e)}")

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    try:
        result = await db.tasks.delete_one({"id": task_id})
        if result.deleted_count:
            return {"message": "Task deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Task not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting task: {str(e)}")

@app.get("/api/recommendations/daily")
async def get_daily_recommendations():
    try:
        # Get all pending and in-progress tasks
        tasks = await db.tasks.find({"status": {"$in": ["pending", "in_progress"]}}).to_list(length=None)
        
        if not tasks:
            return DailyRecommendation(
                date=datetime.now().date().isoformat(),
                tasks=[],
                total_hours=0,
                available_hours=8,
                workload_status="light"
            )
        
        # Get user's learning insights
        learning_data = await db.learning_data.find().to_list(length=None)
        insights = calculate_learning_insights(learning_data)
        
        # Sort tasks by urgency and priority
        def task_urgency_score(task):
            deadline = datetime.fromisoformat(task['deadline'].replace('Z', '+00:00'))
            days_until = (deadline - datetime.now(timezone.utc)).days
            
            priority_weight = {"high": 3, "medium": 2, "low": 1}
            priority_score = priority_weight.get(task.get('priority', 'medium'), 2)
            
            # Urgency decreases as days increase
            urgency_score = max(1, 10 / max(1, days_until))
            
            return urgency_score * priority_score
        
        sorted_tasks = sorted(tasks, key=task_urgency_score, reverse=True)
        
        # Calculate daily recommendations
        available_hours = 6.0  # 8-4 with teaching breaks
        total_allocated = 0
        recommended_tasks = []
        
        for task in sorted_tasks:
            if total_allocated >= available_hours:
                break
                
            # Adjust estimated hours based on learning data
            base_estimate = task['estimated_hours']
            
            # Apply complexity-specific adjustment
            complexity_factor = insights['complexity_adjustments'].get(task['complexity'], 1.0)
            
            # Apply tag-specific adjustments
            tag_factor = 1.0
            if task['tags']:
                tag_factors = [insights['tag_insights'].get(tag, 1.0) for tag in task['tags']]
                tag_factor = sum(tag_factors) / len(tag_factors)
            
            # Apply overall pace factor
            adjusted_estimate = base_estimate * insights['pace_factor'] * complexity_factor * tag_factor
            
            # Calculate days until deadline
            deadline = datetime.fromisoformat(task['deadline'].replace('Z', '+00:00'))
            days_until = max(1, (deadline - datetime.now(timezone.utc)).days)
            
            # Calculate minimum daily effort needed
            min_daily_effort = min(available_hours, adjusted_estimate / days_until)
            
            # Allocate time for this task
            allocated_time = min(min_daily_effort, available_hours - total_allocated)
            
            if allocated_time > 0.5:  # Only include if at least 30 minutes
                recommended_tasks.append({
                    "id": task['id'],
                    "title": task['title'],
                    "allocated_hours": round(allocated_time, 1),
                    "priority": task.get('priority', 'medium'),
                    "deadline": task['deadline'],
                    "complexity": task['complexity'],
                    "progress_percentage": round((allocated_time / adjusted_estimate) * 100, 1) if adjusted_estimate > 0 else 0
                })
                
                total_allocated += allocated_time
        
        # Determine workload status
        if total_allocated <= 3:
            workload_status = "light"
        elif total_allocated <= 5:
            workload_status = "moderate"
        elif total_allocated <= 7:
            workload_status = "heavy"
        else:
            workload_status = "overloaded"
        
        return DailyRecommendation(
            date=datetime.now().date().isoformat(),
            tasks=recommended_tasks,
            total_hours=round(total_allocated, 1),
            available_hours=available_hours,
            workload_status=workload_status
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")

@app.get("/api/schedule", response_model=List[Schedule])
async def get_schedule():
    try:
        schedules = await db.schedule.find().to_list(length=None)
        return [Schedule(**parse_from_mongo(schedule)) for schedule in schedules]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching schedule: {str(e)}")

@app.post("/api/schedule", response_model=Schedule)
async def create_schedule_item(schedule: Schedule):
    try:
        schedule_data = prepare_for_mongo(schedule.dict())
        result = await db.schedule.insert_one(schedule_data)
        if result.inserted_id:
            return schedule
        else:
            raise HTTPException(status_code=500, detail="Failed to create schedule item")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating schedule: {str(e)}")

@app.get("/api/analytics/learning")
async def get_learning_analytics():
    try:
        learning_data_raw = await db.learning_data.find().to_list(length=None)
        learning_data = [parse_from_mongo(item) for item in learning_data_raw]
        insights = calculate_learning_insights(learning_data)
        
        # Calculate additional analytics
        recent_tasks = sorted(learning_data, key=lambda x: x['completion_date'], reverse=True)[:10]
        
        analytics = {
            "total_completed_tasks": len(learning_data),
            "overall_pace_factor": round(insights['pace_factor'], 2),
            "complexity_insights": {k: round(v, 2) for k, v in insights['complexity_adjustments'].items()},
            "tag_performance": {k: round(v, 2) for k, v in insights['tag_insights'].items()},
            "recent_completions": [parse_from_mongo(task) for task in recent_tasks[:5]],
            "accuracy_trend": [
                {
                    "task_title": task.get('notes', 'Unknown'),
                    "estimated": task['estimated_hours'],
                    "actual": task['actual_hours'],
                    "accuracy": round(task['accuracy_ratio'], 2)
                }
                for task in recent_tasks
            ]
        }
        
        return analytics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching analytics: {str(e)}")

@app.post("/api/schedule/teaching")
async def add_teaching_schedule(teaching_times: List[Dict[str, str]]):
    """Add teaching schedule to block out unavailable times"""
    try:
        for item in teaching_times:
            schedule = Schedule(
                day_of_week=item['day'],
                start_time=item['start_time'],
                end_time=item['end_time'],
                activity_type="teaching",
                description=item.get('description', 'Teaching time')
            )
            
            schedule_data = prepare_for_mongo(schedule.dict())
            await db.schedule.insert_one(schedule_data)
        
        return {"message": f"Added {len(teaching_times)} teaching schedule items"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding teaching schedule: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)