import React, { useState, useEffect } from 'react';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

function App() {
  const [tasks, setTasks] = useState([]);
  const [recommendations, setRecommendations] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [loading, setLoading] = useState(false);

  // Form states
  const [newTask, setNewTask] = useState({
    title: '',
    description: '',
    deadline: '',
    priority: 'medium'
  });

  const [bulkTaskText, setBulkTaskText] = useState('');
  const [bulkPriority, setBulkPriority] = useState('medium');

  const [teachingSchedule, setTeachingSchedule] = useState([
    { day: 'monday', start_time: '', end_time: '', description: '' }
  ]);

  // Fetch data on component mount
  useEffect(() => {
    fetchTasks();
    fetchRecommendations();
    fetchAnalytics();
  }, []);

  const fetchTasks = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/tasks`);
      if (response.ok) {
        const data = await response.json();
        setTasks(data);
      }
    } catch (error) {
      console.error('Error fetching tasks:', error);
    }
  };

  const fetchRecommendations = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/recommendations/daily`);
      if (response.ok) {
        const data = await response.json();
        setRecommendations(data);
      }
    } catch (error) {
      console.error('Error fetching recommendations:', error);
    }
  };

  const fetchAnalytics = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/analytics/learning`);
      if (response.ok) {
        const data = await response.json();
        setAnalytics(data);
      }
    } catch (error) {
      console.error('Error fetching analytics:', error);
    }
  };

  const createTask = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await fetch(`${BACKEND_URL}/api/tasks`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newTask),
      });

      if (response.ok) {
        setNewTask({ title: '', description: '', deadline: '', priority: 'medium' });
        await fetchTasks();
        await fetchRecommendations();
      } else {
        alert('Failed to create task');
      }
    } catch (error) {
      console.error('Error creating task:', error);
      alert('Error creating task');
    } finally {
      setLoading(false);
    }
  };

  const bulkImportTasks = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await fetch(`${BACKEND_URL}/api/tasks/bulk-import`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          task_text: bulkTaskText,
          default_priority: bulkPriority
        }),
      });

      if (response.ok) {
        const result = await response.json();
        setBulkTaskText('');
        await fetchTasks();
        await fetchRecommendations();
        alert(`Successfully imported ${result.tasks_created} tasks!`);
      } else {
        alert('Failed to import tasks');
      }
    } catch (error) {
      console.error('Error importing tasks:', error);
      alert('Error importing tasks');
    } finally {
      setLoading(false);
    }
  };

  const completeTask = async (taskId, actualHours) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/tasks/${taskId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          status: 'completed',
          actual_hours: parseFloat(actualHours)
        }),
      });

      if (response.ok) {
        await fetchTasks();
        await fetchRecommendations();
        await fetchAnalytics();
      }
    } catch (error) {
      console.error('Error completing task:', error);
    }
  };

  const addTeachingSchedule = async () => {
    try {
      const validSchedule = teachingSchedule.filter(item => 
        item.day && item.start_time && item.end_time
      );

      if (validSchedule.length === 0) {
        alert('Please fill in at least one complete schedule item');
        return;
      }

      const response = await fetch(`${BACKEND_URL}/api/schedule/teaching`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(validSchedule),
      });

      if (response.ok) {
        alert('Teaching schedule added successfully!');
        setTeachingSchedule([{ day: 'monday', start_time: '', end_time: '', description: '' }]);
      }
    } catch (error) {
      console.error('Error adding teaching schedule:', error);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const getStatusBadgeColor = (status) => {
    const colors = {
      light: 'bg-green-100 text-green-800',
      moderate: 'bg-yellow-100 text-yellow-800',
      heavy: 'bg-orange-100 text-orange-800',
      overloaded: 'bg-red-100 text-red-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const getPriorityColor = (priority) => {
    const colors = {
      high: 'border-red-400 bg-red-50',
      medium: 'border-yellow-400 bg-yellow-50',
      low: 'border-green-400 bg-green-50'
    };
    return colors[priority] || 'border-gray-400 bg-gray-50';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
              Kenworthy's Master Plan
            </span>
          </h1>
          <p className="text-gray-600">AI-powered personal productivity and scheduling system</p>
        </div>

        {/* Navigation Tabs */}
        <div className="flex justify-center mb-8">
          <div className="bg-white rounded-xl p-2 shadow-lg">
            {[
              { id: 'dashboard', label: 'Dashboard', icon: '📊' },
              { id: 'tasks', label: 'Tasks', icon: '📝' },
              { id: 'schedule', label: 'Schedule', icon: '📅' },
              { id: 'analytics', label: 'Analytics', icon: '📈' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-6 py-3 rounded-lg font-medium transition-all duration-200 mr-2 ${
                  activeTab === tab.id
                    ? 'bg-blue-600 text-white shadow-md'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <span className="mr-2">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div className="space-y-8">
            {/* Daily Recommendations */}
            {recommendations && (
              <div className="space-y-8">
                <div className="bg-white rounded-xl shadow-xl p-8">
                  <div className="flex items-center justify-between mb-6">
                    <h2 className="text-2xl font-bold text-gray-800">Today's Recommendations</h2>
                    <div className={`px-4 py-2 rounded-full font-medium ${getStatusBadgeColor(recommendations.workload_status)}`}>
                      {recommendations.workload_status.charAt(0).toUpperCase() + recommendations.workload_status.slice(1)} Workload
                    </div>
                  </div>

                  <div className="grid md:grid-cols-2 gap-6 mb-6">
                    <div className="bg-gradient-to-r from-blue-500 to-blue-600 rounded-lg p-6 text-white">
                      <h3 className="text-lg font-semibold mb-2">Available Hours</h3>
                      <div className="text-3xl font-bold">{recommendations.available_hours}h</div>
                      <p className="text-blue-100">Daily capacity (8 AM - 4 PM)</p>
                    </div>
                    <div className="bg-gradient-to-r from-indigo-500 to-indigo-600 rounded-lg p-6 text-white">
                      <h3 className="text-lg font-semibold mb-2">Allocated Hours</h3>
                      <div className="text-3xl font-bold">{recommendations.total_hours}h</div>
                      <p className="text-indigo-100">
                        {Math.round((recommendations.total_hours / recommendations.available_hours) * 100)}% utilization
                      </p>
                    </div>
                  </div>
                </div>

                {/* Daily Timetable */}
                {recommendations.timetable && recommendations.timetable.length > 0 && (
                  <div className="bg-white rounded-xl shadow-xl p-8">
                    <h2 className="text-2xl font-bold text-gray-800 mb-6">📅 Your Daily Timetable</h2>
                    <div className="space-y-3">
                      {recommendations.timetable.map((slot, index) => (
                        <div key={index} className={`flex items-center p-4 rounded-lg border-l-4 ${getPriorityColor(slot.priority)}`}>
                          <div className="flex-shrink-0 w-24 text-center">
                            <div className="bg-gray-100 rounded px-2 py-1 text-sm font-mono">
                              {slot.start_time}
                            </div>
                            <div className="text-xs text-gray-500 mt-1">to</div>
                            <div className="bg-gray-100 rounded px-2 py-1 text-sm font-mono">
                              {slot.end_time}
                            </div>
                          </div>
                          
                          <div className="ml-6 flex-1">
                            <h4 className="font-semibold text-gray-800">{slot.task_title}</h4>
                            <div className="flex gap-4 text-sm text-gray-600 mt-1">
                              <span className={`px-2 py-1 rounded text-xs ${
                                slot.priority === 'high' ? 'bg-red-100 text-red-700' :
                                slot.priority === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                                'bg-green-100 text-green-700'
                              }`}>
                                {slot.priority}
                              </span>
                              <span className={`px-2 py-1 rounded text-xs ${
                                slot.complexity === 'large' ? 'bg-red-100 text-red-700' :
                                slot.complexity === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                                'bg-green-100 text-green-700'
                              }`}>
                                {slot.complexity}
                              </span>
                            </div>
                          </div>
                          
                          <div className="text-sm text-gray-500">
                            {Math.round((new Date(`2000-01-01T${slot.end_time}:00`) - new Date(`2000-01-01T${slot.start_time}:00`)) / (1000 * 60 * 60) * 10) / 10}h
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Teaching Break Reminder */}
                    <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                      <div className="flex items-center">
                        <span className="text-blue-600 mr-2">🏫</span>
                        <div>
                          <h4 className="font-medium text-blue-800">Teaching Break Reminder</h4>
                          <p className="text-blue-600 text-sm">Lunch break (12:00-1:00 PM) and teaching commitments are automatically factored into your schedule.</p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Task Overview */}
                <div className="bg-white rounded-xl shadow-xl p-8">
                  <h3 className="text-xl font-semibold text-gray-800 mb-4">Task Overview</h3>
                  {recommendations.tasks.length > 0 ? (
                    <div className="space-y-4">
                      {recommendations.tasks.map(task => (
                        <div key={task.id} className={`border-l-4 rounded-lg p-4 ${getPriorityColor(task.priority)}`}>
                          <div className="flex justify-between items-start">
                            <div className="flex-1">
                              <h4 className="font-semibold text-gray-800 mb-1">{task.title}</h4>
                              <div className="flex flex-wrap gap-4 text-sm text-gray-600">
                                <span>⏰ {task.allocated_hours}h allocated</span>
                                <span>📅 Due: {formatDate(task.deadline)}</span>
                                <span>🎯 {task.priority} priority</span>
                                <span>📊 {task.progress_percentage}% of total estimate</span>
                              </div>
                            </div>
                            <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                              task.complexity === 'large' ? 'bg-red-100 text-red-700' :
                              task.complexity === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                              'bg-green-100 text-green-700'
                            }`}>
                              {task.complexity}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-gray-500">
                      <div className="text-4xl mb-4">✨</div>
                      <p>No tasks scheduled for today. Great job staying on top of things!</p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tasks Tab */}
        {activeTab === 'tasks' && (
          <div className="space-y-8">
            {/* Bulk Import Tasks */}
            <div className="bg-white rounded-xl shadow-xl p-8">
              <h2 className="text-2xl font-bold text-gray-800 mb-6">📋 Bulk Import Tasks</h2>
              <p className="text-gray-600 mb-4">
                Copy and paste your task list in the format: <strong>"Task Name — Date"</strong>
              </p>
              
              <div className="bg-gray-50 p-4 rounded-lg mb-4 border-l-4 border-blue-400">
                <p className="text-sm text-gray-700 mb-2"><strong>Example format:</strong></p>
                <code className="text-sm text-gray-600">
                  Opening Evening — 25 Sep 2025<br/>
                  Open Morning — 24 Sep 2025<br/>
                  INSET Day — 26 Sep 2025
                </code>
              </div>

              <form onSubmit={bulkImportTasks} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Task List</label>
                  <textarea
                    required
                    value={bulkTaskText}
                    onChange={(e) => setBulkTaskText(e.target.value)}
                    rows={6}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Opening Evening — 25 Sep 2025&#10;Open Morning — 24 Sep 2025&#10;INSET Day — 26 Sep 2025"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Default Priority</label>
                  <select
                    value={bulkPriority}
                    onChange={(e) => setBulkPriority(e.target.value)}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="low">Low Priority</option>
                    <option value="medium">Medium Priority</option>
                    <option value="high">High Priority</option>
                  </select>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-gradient-to-r from-green-600 to-green-700 text-white py-3 rounded-lg font-semibold hover:from-green-700 hover:to-green-800 transition-all duration-200 disabled:opacity-50"
                >
                  {loading ? 'Importing Tasks...' : '🚀 Import Tasks with AI Analysis'}
                </button>
              </form>
            </div>

            {/* Add Individual Task Form */}
            <div className="bg-white rounded-xl shadow-xl p-8">
              <h2 className="text-2xl font-bold text-gray-800 mb-6">Add Individual Task</h2>
              <form onSubmit={createTask} className="space-y-4">
                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Task Title</label>
                    <input
                      type="text"
                      required
                      value={newTask.title}
                      onChange={(e) => setNewTask({...newTask, title: e.target.value})}
                      className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="Enter task title..."
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Priority</label>
                    <select
                      value={newTask.priority}
                      onChange={(e) => setNewTask({...newTask, priority: e.target.value})}
                      className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="low">Low Priority</option>
                      <option value="medium">Medium Priority</option>
                      <option value="high">High Priority</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Description</label>
                  <textarea
                    required
                    value={newTask.description}
                    onChange={(e) => setNewTask({...newTask, description: e.target.value})}
                    rows={3}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Describe the task in detail..."
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Deadline</label>
                  <input
                    type="datetime-local"
                    required
                    value={newTask.deadline}
                    onChange={(e) => setNewTask({...newTask, deadline: e.target.value + ':00Z'})}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white py-3 rounded-lg font-semibold hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 disabled:opacity-50"
                >
                  {loading ? 'Creating Task...' : 'Add Task with AI Analysis'}
                </button>
              </form>
            </div>

            {/* Tasks List */}
            <div className="bg-white rounded-xl shadow-xl p-8">
              <h2 className="text-2xl font-bold text-gray-800 mb-6">All Tasks</h2>
              <div className="space-y-4">
                {tasks.map(task => (
                  <TaskCard key={task.id} task={task} onComplete={completeTask} />
                ))}
                
                {tasks.length === 0 && (
                  <div className="text-center py-8 text-gray-500">
                    <div className="text-4xl mb-4">📝</div>
                    <p>No tasks yet. Add your first task above!</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Schedule Tab */}
        {activeTab === 'schedule' && (
          <div className="bg-white rounded-xl shadow-xl p-8">
            <h2 className="text-2xl font-bold text-gray-800 mb-6">Teaching Schedule</h2>
            <p className="text-gray-600 mb-6">
              Set your teaching hours to help the AI plan around your availability. 
              This enables better recommendations during your free time.
            </p>

            <div className="space-y-4">
              {teachingSchedule.map((item, index) => (
                <div key={index} className="grid grid-cols-1 md:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Day</label>
                    <select
                      value={item.day}
                      onChange={(e) => {
                        const updated = [...teachingSchedule];
                        updated[index].day = e.target.value;
                        setTeachingSchedule(updated);
                      }}
                      className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="monday">Monday</option>
                      <option value="tuesday">Tuesday</option>
                      <option value="wednesday">Wednesday</option>
                      <option value="thursday">Thursday</option>
                      <option value="friday">Friday</option>
                      <option value="saturday">Saturday</option>
                      <option value="sunday">Sunday</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Start Time</label>
                    <input
                      type="time"
                      value={item.start_time}
                      onChange={(e) => {
                        const updated = [...teachingSchedule];
                        updated[index].start_time = e.target.value;
                        setTeachingSchedule(updated);
                      }}
                      className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">End Time</label>
                    <input
                      type="time"
                      value={item.end_time}
                      onChange={(e) => {
                        const updated = [...teachingSchedule];
                        updated[index].end_time = e.target.value;
                        setTeachingSchedule(updated);
                      }}
                      className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Description</label>
                    <input
                      type="text"
                      value={item.description}
                      onChange={(e) => {
                        const updated = [...teachingSchedule];
                        updated[index].description = e.target.value;
                        setTeachingSchedule(updated);
                      }}
                      placeholder="Class/Subject"
                      className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
              ))}

              <div className="flex gap-4">
                <button
                  onClick={() => setTeachingSchedule([...teachingSchedule, { day: 'monday', start_time: '', end_time: '', description: '' }])}
                  className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition-colors"
                >
                  Add Another Time Slot
                </button>
                
                <button
                  onClick={addTeachingSchedule}
                  className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                >
                  Save Teaching Schedule
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Analytics Tab */}
        {activeTab === 'analytics' && analytics && (
          <div className="space-y-8">
            <div className="bg-white rounded-xl shadow-xl p-8">
              <h2 className="text-2xl font-bold text-gray-800 mb-6">Learning Analytics</h2>
              
              <div className="grid md:grid-cols-3 gap-6 mb-8">
                <div className="bg-gradient-to-r from-green-500 to-green-600 rounded-lg p-6 text-white">
                  <h3 className="text-lg font-semibold mb-2">Tasks Completed</h3>
                  <div className="text-3xl font-bold">{analytics.total_completed_tasks}</div>
                </div>
                
                <div className="bg-gradient-to-r from-purple-500 to-purple-600 rounded-lg p-6 text-white">
                  <h3 className="text-lg font-semibold mb-2">Pace Factor</h3>
                  <div className="text-3xl font-bold">{analytics.overall_pace_factor}x</div>
                  <p className="text-purple-100 text-sm">
                    {analytics.overall_pace_factor > 1 ? 'Taking longer than estimated' : 'Faster than estimated'}
                  </p>
                </div>
                
                <div className="bg-gradient-to-r from-orange-500 to-orange-600 rounded-lg p-6 text-white">
                  <h3 className="text-lg font-semibold mb-2">Accuracy Improving</h3>
                  <div className="text-3xl font-bold">
                    {analytics.accuracy_trend && analytics.accuracy_trend.length > 0 ? '📈' : '📊'}
                  </div>
                </div>
              </div>

              {/* Complexity Performance */}
              <div className="mb-8">
                <h3 className="text-xl font-semibold text-gray-800 mb-4">Performance by Complexity</h3>
                <div className="grid md:grid-cols-3 gap-4">
                  {Object.entries(analytics.complexity_insights || {}).map(([complexity, factor]) => (
                    <div key={complexity} className="bg-gray-50 rounded-lg p-4">
                      <div className="flex justify-between items-center">
                        <span className="capitalize font-medium">{complexity} Tasks</span>
                        <span className={`px-2 py-1 rounded text-sm ${
                          factor > 1 ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
                        }`}>
                          {factor}x
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Recent Accuracy */}
              {analytics.accuracy_trend && analytics.accuracy_trend.length > 0 && (
                <div>
                  <h3 className="text-xl font-semibold text-gray-800 mb-4">Recent Task Accuracy</h3>
                  <div className="space-y-3">
                    {analytics.accuracy_trend.slice(0, 5).map((item, index) => (
                      <div key={index} className="bg-gray-50 rounded-lg p-4">
                        <div className="flex justify-between items-center">
                          <span className="font-medium">{item.task_title}</span>
                          <div className="text-right text-sm text-gray-600">
                            <div>Estimated: {item.estimated}h | Actual: {item.actual}h</div>
                            <div className={`font-medium ${
                              item.accuracy > 1 ? 'text-red-600' : 'text-green-600'
                            }`}>
                              {item.accuracy > 1 ? '+' : ''}{Math.round((item.accuracy - 1) * 100)}%
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Task Card Component
function TaskCard({ task, onComplete }) {
  const [actualHours, setActualHours] = useState('');
  const [showComplete, setShowComplete] = useState(false);

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getPriorityColor = (priority) => {
    const colors = {
      high: 'border-red-400 bg-red-50',
      medium: 'border-yellow-400 bg-yellow-50',
      low: 'border-green-400 bg-green-50'
    };
    return colors[priority] || 'border-gray-400 bg-gray-50';
  };

  const getStatusColor = (status) => {
    const colors = {
      pending: 'bg-gray-100 text-gray-700',
      in_progress: 'bg-blue-100 text-blue-700',
      completed: 'bg-green-100 text-green-700'
    };
    return colors[status] || 'bg-gray-100 text-gray-700';
  };

  const handleComplete = () => {
    if (actualHours && parseFloat(actualHours) > 0) {
      onComplete(task.id, actualHours);
      setShowComplete(false);
      setActualHours('');
    }
  };

  return (
    <div className={`border-l-4 rounded-lg p-6 transition-all duration-200 hover:shadow-md ${getPriorityColor(task.priority)}`}>
      <div className="flex justify-between items-start mb-4">
        <div className="flex-1">
          <h3 className="text-xl font-semibold text-gray-800 mb-2">{task.title}</h3>
          <p className="text-gray-600 mb-3">{task.description}</p>
          
          <div className="flex flex-wrap gap-4 text-sm text-gray-600 mb-3">
            <span>📅 Due: {formatDate(task.deadline)}</span>
            <span>⏱️ Est: {task.estimated_hours}h</span>
            <span>🎯 {task.priority} priority</span>
            <span className={`px-2 py-1 rounded text-xs ${
              task.complexity === 'large' ? 'bg-red-100 text-red-700' :
              task.complexity === 'medium' ? 'bg-yellow-100 text-yellow-700' :
              'bg-green-100 text-green-700'
            }`}>
              {task.complexity}
            </span>
          </div>

          {task.ai_analysis && (
            <div className="bg-blue-50 border border-blue-200 rounded p-3 mb-3">
              <p className="text-sm text-blue-800">
                <strong>AI Analysis:</strong> {task.ai_analysis}
              </p>
            </div>
          )}

          {task.tags && task.tags.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-3">
              {task.tags.map(tag => (
                <span key={tag} className="px-2 py-1 bg-gray-200 text-gray-700 rounded-full text-xs">
                  #{tag}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="flex flex-col items-end gap-2">
          <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(task.status)}`}>
            {task.status.replace('_', ' ')}
          </span>

          {task.status !== 'completed' && !showComplete && (
            <button
              onClick={() => setShowComplete(true)}
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition-colors"
            >
              Mark Complete
            </button>
          )}
        </div>
      </div>

      {showComplete && (
        <div className="bg-green-50 border border-green-200 rounded p-4 mt-4">
          <h4 className="font-medium text-green-800 mb-2">Complete Task</h4>
          <div className="flex gap-3">
            <input
              type="number"
              step="0.5"
              min="0.1"
              placeholder="Actual hours spent"
              value={actualHours}
              onChange={(e) => setActualHours(e.target.value)}
              className="flex-1 p-2 border border-green-300 rounded focus:ring-2 focus:ring-green-500"
            />
            <button
              onClick={handleComplete}
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition-colors"
            >
              Complete
            </button>
            <button
              onClick={() => setShowComplete(false)}
              className="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;