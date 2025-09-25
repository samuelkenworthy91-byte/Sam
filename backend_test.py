#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Workflow Organizer App
Tests all API endpoints including AI integration, CRUD operations, and analytics
"""

import requests
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any
import uuid

# Configuration
BASE_URL = "https://taskoptimizer.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

class WorkflowOrganizerTester:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = []
        self.created_task_ids = []
        self.created_schedule_ids = []
        
    def log_test(self, test_name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "response_data": response_data
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
        if not success and response_data:
            print(f"   Response: {response_data}")
        print()

    def test_health_check(self):
        """Test basic server health check"""
        try:
            # Test the tasks endpoint as a health check since root is served by frontend
            response = self.session.get(f"{API_BASE}/tasks", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("Health Check", True, f"API responding: tasks endpoint returned {len(data)} tasks")
                    return True
                else:
                    self.log_test("Health Check", False, f"Unexpected response format: {data}")
                    return False
            else:
                self.log_test("Health Check", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Health Check", False, f"Connection error: {str(e)}")
            return False

    def test_create_task_with_ai(self):
        """Test task creation with AI analysis"""
        try:
            # Test with a realistic research task
            task_data = {
                "title": "Research Machine Learning Algorithms for Student Assessment",
                "description": "Conduct comprehensive research on ML algorithms suitable for automated student assessment systems. Need to analyze accuracy, bias, and implementation complexity of different approaches including neural networks, decision trees, and ensemble methods.",
                "deadline": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                "priority": "high"
            }
            
            response = self.session.post(f"{API_BASE}/tasks", json=task_data, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["id", "title", "description", "estimated_hours", "complexity", "ai_analysis"]
                
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    self.log_test("Create Task with AI", False, f"Missing fields: {missing_fields}", data)
                    return False
                
                # Verify AI analysis worked
                if data.get("estimated_hours", 0) > 0 and data.get("ai_analysis"):
                    self.created_task_ids.append(data["id"])
                    self.log_test("Create Task with AI", True, 
                                f"Task created with AI analysis. Estimated: {data['estimated_hours']}h, "
                                f"Complexity: {data['complexity']}, Analysis: {data['ai_analysis'][:100]}...")
                    return True
                else:
                    self.log_test("Create Task with AI", False, "AI analysis not working properly", data)
                    return False
            else:
                self.log_test("Create Task with AI", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Create Task with AI", False, f"Error: {str(e)}")
            return False

    def test_create_additional_tasks(self):
        """Create additional tasks for testing recommendations and analytics"""
        tasks = [
            {
                "title": "Prepare Advanced Statistics Lecture",
                "description": "Create comprehensive lecture materials for advanced statistics course covering hypothesis testing, ANOVA, and regression analysis. Include interactive examples and practice problems.",
                "deadline": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
                "priority": "medium"
            },
            {
                "title": "Grade Midterm Examinations",
                "description": "Grade 45 midterm exams for Introduction to Data Science course. Provide detailed feedback on each student's performance and identify common areas of difficulty.",
                "deadline": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
                "priority": "high"
            },
            {
                "title": "Update Course Curriculum",
                "description": "Review and update the machine learning course curriculum to include latest industry trends and technologies. Add modules on transformer models and ethical AI.",
                "deadline": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
                "priority": "low"
            }
        ]
        
        success_count = 0
        for i, task_data in enumerate(tasks):
            try:
                response = self.session.post(f"{API_BASE}/tasks", json=task_data, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    self.created_task_ids.append(data["id"])
                    success_count += 1
                else:
                    self.log_test(f"Create Additional Task {i+1}", False, f"HTTP {response.status_code}: {response.text}")
            except Exception as e:
                self.log_test(f"Create Additional Task {i+1}", False, f"Error: {str(e)}")
        
        if success_count == len(tasks):
            self.log_test("Create Additional Tasks", True, f"Successfully created {success_count} additional tasks")
            return True
        else:
            self.log_test("Create Additional Tasks", False, f"Only created {success_count}/{len(tasks)} tasks")
            return False

    def test_get_all_tasks(self):
        """Test fetching all tasks"""
        try:
            response = self.session.get(f"{API_BASE}/tasks", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) >= len(self.created_task_ids):
                    self.log_test("Get All Tasks", True, f"Retrieved {len(data)} tasks")
                    return True
                else:
                    self.log_test("Get All Tasks", False, f"Expected list with at least {len(self.created_task_ids)} tasks, got: {type(data)} with {len(data) if isinstance(data, list) else 'unknown'} items")
                    return False
            else:
                self.log_test("Get All Tasks", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Get All Tasks", False, f"Error: {str(e)}")
            return False

    def test_get_single_task(self):
        """Test fetching a single task by ID"""
        if not self.created_task_ids:
            self.log_test("Get Single Task", False, "No task IDs available for testing")
            return False
            
        try:
            task_id = self.created_task_ids[0]
            response = self.session.get(f"{API_BASE}/tasks/{task_id}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("id") == task_id:
                    self.log_test("Get Single Task", True, f"Retrieved task: {data.get('title', 'Unknown')}")
                    return True
                else:
                    self.log_test("Get Single Task", False, f"Task ID mismatch. Expected: {task_id}, Got: {data.get('id')}")
                    return False
            else:
                self.log_test("Get Single Task", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Get Single Task", False, f"Error: {str(e)}")
            return False

    def test_update_task(self):
        """Test updating a task including completion with actual hours"""
        if not self.created_task_ids:
            self.log_test("Update Task", False, "No task IDs available for testing")
            return False
            
        try:
            task_id = self.created_task_ids[-1]  # Use last created task
            
            # First update - mark as in progress
            update_data = {
                "status": "in_progress",
                "priority": "high"
            }
            
            response = self.session.put(f"{API_BASE}/tasks/{task_id}", json=update_data, timeout=10)
            
            if response.status_code != 200:
                self.log_test("Update Task", False, f"HTTP {response.status_code}: {response.text}")
                return False
            
            # Second update - complete with actual hours (for learning system)
            completion_data = {
                "status": "completed",
                "actual_hours": 6.5
            }
            
            response = self.session.put(f"{API_BASE}/tasks/{task_id}", json=completion_data, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "completed" and data.get("actual_hours") == 6.5:
                    self.log_test("Update Task", True, f"Task completed with actual hours: {data.get('actual_hours')}h")
                    return True
                else:
                    self.log_test("Update Task", False, f"Update not reflected properly: {data}")
                    return False
            else:
                self.log_test("Update Task", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Update Task", False, f"Error: {str(e)}")
            return False

    def test_daily_recommendations(self):
        """Test daily work recommendations"""
        try:
            response = self.session.get(f"{API_BASE}/recommendations/daily", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["date", "tasks", "total_hours", "available_hours", "workload_status"]
                
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    self.log_test("Daily Recommendations", False, f"Missing fields: {missing_fields}", data)
                    return False
                
                # Verify recommendation logic
                if isinstance(data["tasks"], list) and data["total_hours"] >= 0:
                    workload_statuses = ["light", "moderate", "heavy", "overloaded"]
                    if data["workload_status"] in workload_statuses:
                        self.log_test("Daily Recommendations", True, 
                                    f"Generated recommendations: {len(data['tasks'])} tasks, "
                                    f"{data['total_hours']}h total, status: {data['workload_status']}")
                        return True
                    else:
                        self.log_test("Daily Recommendations", False, f"Invalid workload status: {data['workload_status']}")
                        return False
                else:
                    self.log_test("Daily Recommendations", False, "Invalid recommendation format", data)
                    return False
            else:
                self.log_test("Daily Recommendations", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Daily Recommendations", False, f"Error: {str(e)}")
            return False

    def test_create_schedule(self):
        """Test creating schedule items"""
        try:
            schedule_data = {
                "day_of_week": "monday",
                "start_time": "09:00",
                "end_time": "11:00",
                "activity_type": "work",
                "description": "Research and writing block"
            }
            
            response = self.session.post(f"{API_BASE}/schedule", json=schedule_data, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("day_of_week") == "monday" and data.get("activity_type") == "work":
                    self.created_schedule_ids.append(data.get("id"))
                    self.log_test("Create Schedule", True, f"Schedule created: {data.get('description')}")
                    return True
                else:
                    self.log_test("Create Schedule", False, "Schedule data not saved properly", data)
                    return False
            else:
                self.log_test("Create Schedule", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Create Schedule", False, f"Error: {str(e)}")
            return False

    def test_get_schedule(self):
        """Test fetching schedule"""
        try:
            response = self.session.get(f"{API_BASE}/schedule", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("Get Schedule", True, f"Retrieved {len(data)} schedule items")
                    return True
                else:
                    self.log_test("Get Schedule", False, f"Expected list, got: {type(data)}")
                    return False
            else:
                self.log_test("Get Schedule", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Get Schedule", False, f"Error: {str(e)}")
            return False

    def test_teaching_schedule(self):
        """Test adding teaching schedule"""
        try:
            teaching_data = [
                {
                    "day": "tuesday",
                    "start_time": "10:00",
                    "end_time": "12:00",
                    "description": "Advanced Statistics Course"
                },
                {
                    "day": "thursday",
                    "start_time": "14:00",
                    "end_time": "16:00",
                    "description": "Machine Learning Seminar"
                }
            ]
            
            response = self.session.post(f"{API_BASE}/schedule/teaching", json=teaching_data, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "2" in data["message"]:
                    self.log_test("Teaching Schedule", True, f"Added teaching schedule: {data['message']}")
                    return True
                else:
                    self.log_test("Teaching Schedule", False, "Unexpected response format", data)
                    return False
            else:
                self.log_test("Teaching Schedule", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Teaching Schedule", False, f"Error: {str(e)}")
            return False

    def test_learning_analytics(self):
        """Test learning analytics endpoint"""
        try:
            # Wait a moment for learning data to be processed
            time.sleep(2)
            
            response = self.session.get(f"{API_BASE}/analytics/learning", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["total_completed_tasks", "overall_pace_factor", "complexity_insights", "tag_performance"]
                
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    self.log_test("Learning Analytics", False, f"Missing fields: {missing_fields}", data)
                    return False
                
                # Verify analytics data structure
                if (isinstance(data["complexity_insights"], dict) and 
                    isinstance(data["tag_performance"], dict) and
                    isinstance(data["overall_pace_factor"], (int, float))):
                    
                    self.log_test("Learning Analytics", True, 
                                f"Analytics generated: {data['total_completed_tasks']} completed tasks, "
                                f"pace factor: {data['overall_pace_factor']}")
                    return True
                else:
                    self.log_test("Learning Analytics", False, "Invalid analytics data structure", data)
                    return False
            else:
                self.log_test("Learning Analytics", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Learning Analytics", False, f"Error: {str(e)}")
            return False

    def test_delete_task(self):
        """Test deleting a task"""
        if not self.created_task_ids:
            self.log_test("Delete Task", False, "No task IDs available for testing")
            return False
            
        try:
            task_id = self.created_task_ids[0]
            response = self.session.delete(f"{API_BASE}/tasks/{task_id}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "deleted" in data["message"].lower():
                    self.log_test("Delete Task", True, f"Task deleted: {data['message']}")
                    self.created_task_ids.remove(task_id)
                    return True
                else:
                    self.log_test("Delete Task", False, "Unexpected response format", data)
                    return False
            else:
                self.log_test("Delete Task", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Delete Task", False, f"Error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Comprehensive Backend API Testing")
        print("=" * 60)
        
        # Core API tests
        self.test_health_check()
        
        # Task management tests
        self.test_create_task_with_ai()
        self.test_create_additional_tasks()
        self.test_get_all_tasks()
        self.test_get_single_task()
        self.test_update_task()
        
        # Advanced features
        self.test_daily_recommendations()
        self.test_learning_analytics()
        
        # Schedule management
        self.test_create_schedule()
        self.test_get_schedule()
        self.test_teaching_schedule()
        
        # Cleanup
        self.test_delete_task()
        
        # Summary
        print("=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if total - passed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['details']}")
        
        return passed == total

if __name__ == "__main__":
    tester = WorkflowOrganizerTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed! Backend is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the details above.")