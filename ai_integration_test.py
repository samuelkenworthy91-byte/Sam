#!/usr/bin/env python3
"""
AI Integration Specific Test - Verify LLM analysis works with different task types
"""

import requests
import json
from datetime import datetime, timedelta, timezone

BASE_URL = "https://taskoptimizer.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

def test_ai_analysis_variety():
    """Test AI analysis with different types of tasks"""
    session = requests.Session()
    
    test_tasks = [
        {
            "title": "Quick Email Response",
            "description": "Reply to student inquiry about assignment deadline",
            "deadline": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
            "expected_complexity": "small"
        },
        {
            "title": "Develop Neural Network Model",
            "description": "Build and train a deep learning model for image classification using TensorFlow. Include data preprocessing, model architecture design, hyperparameter tuning, and performance evaluation.",
            "deadline": (datetime.now(timezone.utc) + timedelta(days=21)).isoformat(),
            "expected_complexity": "large"
        },
        {
            "title": "Review Research Paper",
            "description": "Peer review a machine learning research paper on transformer architectures. Provide detailed feedback on methodology, experiments, and conclusions.",
            "deadline": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
            "expected_complexity": "medium"
        }
    ]
    
    results = []
    
    for i, task_data in enumerate(test_tasks):
        try:
            print(f"Testing AI analysis for task {i+1}: {task_data['title']}")
            
            response = session.post(f"{API_BASE}/tasks", json=task_data, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify AI analysis fields
                ai_fields = ["estimated_hours", "complexity", "ai_analysis", "tags"]
                has_ai_data = all(field in data and data[field] for field in ai_fields)
                
                if has_ai_data:
                    result = {
                        "task": task_data["title"],
                        "success": True,
                        "estimated_hours": data["estimated_hours"],
                        "complexity": data["complexity"],
                        "ai_analysis": data["ai_analysis"][:100] + "...",
                        "tags": data["tags"],
                        "expected_complexity": task_data["expected_complexity"],
                        "complexity_match": data["complexity"] == task_data["expected_complexity"]
                    }
                    print(f"✅ AI Analysis Success:")
                    print(f"   Estimated: {data['estimated_hours']}h")
                    print(f"   Complexity: {data['complexity']} (expected: {task_data['expected_complexity']})")
                    print(f"   Tags: {data['tags']}")
                    print(f"   Analysis: {data['ai_analysis'][:100]}...")
                else:
                    result = {
                        "task": task_data["title"],
                        "success": False,
                        "error": "Missing AI analysis fields"
                    }
                    print(f"❌ AI Analysis Failed: Missing fields")
                
                results.append(result)
                
                # Clean up - delete the task
                session.delete(f"{API_BASE}/tasks/{data['id']}")
                
            else:
                print(f"❌ Task creation failed: HTTP {response.status_code}")
                results.append({
                    "task": task_data["title"],
                    "success": False,
                    "error": f"HTTP {response.status_code}"
                })
                
        except Exception as e:
            print(f"❌ Error testing task {i+1}: {str(e)}")
            results.append({
                "task": task_data["title"],
                "success": False,
                "error": str(e)
            })
        
        print()
    
    # Summary
    successful = sum(1 for r in results if r["success"])
    total = len(results)
    
    print("=" * 60)
    print("🤖 AI INTEGRATION TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")
    print(f"Success Rate: {(successful/total)*100:.1f}%")
    
    if successful == total:
        print("\n🎉 AI Integration is working correctly!")
        print("✅ LLM analysis provides estimates and complexity assessment")
        print("✅ Different task types are properly analyzed")
        print("✅ AI-generated tags and breakdowns are working")
    else:
        print("\n⚠️ Some AI integration issues detected:")
        for result in results:
            if not result["success"]:
                print(f"  - {result['task']}: {result.get('error', 'Unknown error')}")
    
    return successful == total

if __name__ == "__main__":
    test_ai_analysis_variety()