#!/usr/bin/env python3
"""
Focused test for the new bulk import feature as requested in the review
"""

import requests
import json
from datetime import datetime, timezone

BASE_URL = "https://taskoptimizer.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

def test_specific_cases():
    """Test the exact cases mentioned in the review request"""
    session = requests.Session()
    
    print("🔍 Testing Specific Bulk Import Cases from Review Request")
    print("=" * 60)
    
    # Test Case 1 - Valid bulk input
    print("\n📝 Test Case 1: Valid bulk input")
    test_case_1 = {
        "task_text": "Opening Evening — 25 Sep 2025\nOpen Morning — 24 Sep 2025\nINSET Day — 26 Sep 2025\nGrade Midterm Examinations — 27 Sep 2025",
        "default_priority": "medium"
    }
    
    try:
        response = session.post(f"{API_BASE}/tasks/bulk-import", json=test_case_1, timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS: Created {data['tasks_created']} tasks")
            
            # Check AI analysis
            ai_count = sum(1 for task in data['tasks'] if task.get('ai_analysis') and task.get('estimated_hours', 0) > 0)
            print(f"   AI Analysis: {ai_count}/{len(data['tasks'])} tasks have AI analysis")
            
            # Check date parsing
            for task in data['tasks']:
                try:
                    parsed_date = datetime.fromisoformat(task['deadline'].replace('Z', '+00:00'))
                    print(f"   Task: '{task['title']}' -> Deadline: {parsed_date.strftime('%Y-%m-%d')}, Est: {task['estimated_hours']}h")
                except:
                    print(f"   ❌ Invalid date format for task: {task['title']}")
        else:
            print(f"❌ FAILED: HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
    
    # Test Case 2 - Different date formats
    print("\n📝 Test Case 2: Different date formats")
    test_case_2 = {
        "task_text": "Staff Meeting — Sep 30 2025\nParent Conference — 01/10/2025\nLecture Prep — 2025-10-05",
        "default_priority": "high"
    }
    
    try:
        response = session.post(f"{API_BASE}/tasks/bulk-import", json=test_case_2, timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS: Created {data['tasks_created']} tasks with different date formats")
            
            for task in data['tasks']:
                try:
                    parsed_date = datetime.fromisoformat(task['deadline'].replace('Z', '+00:00'))
                    print(f"   Task: '{task['title']}' -> Deadline: {parsed_date.strftime('%Y-%m-%d')}, Priority: {task['priority']}")
                except:
                    print(f"   ❌ Invalid date format for task: {task['title']}")
        else:
            print(f"❌ FAILED: HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
    
    # Test updated recommendations endpoint
    print("\n📝 Testing Updated Recommendations Endpoint")
    try:
        response = session.get(f"{API_BASE}/recommendations/daily", timeout=15)
        if response.status_code == 200:
            data = response.json()
            
            # Check for timetable field
            if 'timetable' in data:
                print(f"✅ SUCCESS: Recommendations include timetable field")
                print(f"   Timetable slots: {len(data['timetable'])}")
                
                if len(data['timetable']) > 0:
                    sample_slot = data['timetable'][0]
                    print(f"   Sample slot: {sample_slot['start_time']}-{sample_slot['end_time']} - {sample_slot['task_title']}")
                    
                    # Verify slot structure
                    required_fields = ['start_time', 'end_time', 'task_id', 'task_title', 'priority', 'complexity']
                    missing = [f for f in required_fields if f not in sample_slot]
                    if missing:
                        print(f"   ⚠️  Missing timetable fields: {missing}")
                    else:
                        print(f"   ✅ Timetable structure complete")
                else:
                    print(f"   ℹ️  Timetable empty (no tasks to schedule)")
            else:
                print(f"❌ FAILED: Timetable field missing from recommendations")
        else:
            print(f"❌ FAILED: HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
    
    print("\n" + "=" * 60)
    print("🎯 Focused Testing Complete")

if __name__ == "__main__":
    test_specific_cases()