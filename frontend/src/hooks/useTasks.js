import { useState, useEffect } from 'react'

const useTasks = (clientId) => {
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(false)
  const [syncing, setSyncing] = useState(false)

  // Load tasks from localStorage and backend on mount
  useEffect(() => {
    if (clientId) {
      loadTasksFromStorage()
      loadTasksFromBackend()
    }
  }, [clientId])

  const loadTasksFromStorage = () => {
    try {
      const storedTasks = localStorage.getItem(`tasks_${clientId}`)
      if (storedTasks) {
        const parsedTasks = JSON.parse(storedTasks)
        setTasks(parsedTasks)
        console.log(`Loaded ${parsedTasks.length} tasks from storage`)
      }
    } catch (error) {
      console.error('Error loading tasks from storage:', error)
    }
  }

  const saveTasksToStorage = (updatedTasks) => {
    try {
      localStorage.setItem(`tasks_${clientId}`, JSON.stringify(updatedTasks))
    } catch (error) {
      console.error('Error saving tasks to storage:', error)
    }
  }

  const loadTasksFromBackend = async () => {
    try {
      const response = await fetch(`/api/case-management/tasks/list/${clientId}`)
      if (response.ok) {
        const data = await response.json()
        if (data.success && data.tasks) {
          // Merge backend tasks with local tasks, avoiding duplicates
          const backendTasks = data.tasks.map(task => ({ ...task, synced: true }))
          const localTasks = JSON.parse(localStorage.getItem(`tasks_${clientId}`) || '[]')
          
          // Create a map of existing task IDs to avoid duplicates
          const existingIds = new Set(backendTasks.map(task => task.task_id))
          const uniqueLocalTasks = localTasks.filter(task => !existingIds.has(task.task_id))
          
          // Combine and sort tasks by due date
          const allTasks = [...backendTasks, ...uniqueLocalTasks]
            .sort((a, b) => new Date(a.due_date) - new Date(b.due_date))
          
          setTasks(allTasks)
          saveTasksToStorage(allTasks)
          console.log(`Loaded ${backendTasks.length} tasks from backend`)
        }
      }
    } catch (error) {
      console.log('Backend not available for tasks loading:', error.message)
    }
  }

  const generateTaskId = () => {
    return `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  const addTask = async (taskData) => {
    try {
      setLoading(true)
      
      const newTask = {
        task_id: generateTaskId(),
        client_id: clientId,
        title: taskData.title,
        description: taskData.description || '',
        priority: taskData.priority || 'medium',
        status: 'pending',
        task_type: taskData.task_type || 'general',
        due_date: taskData.due_date,
        assigned_to: taskData.assigned_to || 'Current User',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        synced: false
      }

      // Add to local state immediately
      const updatedTasks = [newTask, ...tasks]
      setTasks(updatedTasks)
      saveTasksToStorage(updatedTasks)

      // Try to sync to backend
      await syncTaskToBackend(newTask)
      
      console.log('Task added successfully:', newTask.task_id)
      return newTask
    } catch (error) {
      console.error('Error adding task:', error)
      throw error
    } finally {
      setLoading(false)
    }
  }

  const updateTask = async (taskId, updates) => {
    try {
      setLoading(true)
      
      const updatedTasks = tasks.map(task => 
        task.task_id === taskId 
          ? { 
              ...task, 
              ...updates, 
              updated_at: new Date().toISOString(),
              synced: false 
            }
          : task
      )
      
      setTasks(updatedTasks)
      saveTasksToStorage(updatedTasks)

      // Try to sync to backend
      const updatedTask = updatedTasks.find(task => task.task_id === taskId)
      if (updatedTask) {
        await syncTaskToBackend(updatedTask, true)
      }
      
      console.log('Task updated successfully:', taskId)
    } catch (error) {
      console.error('Error updating task:', error)
      throw error
    } finally {
      setLoading(false)
    }
  }

  const deleteTask = async (taskId) => {
    try {
      setLoading(true)
      
      const updatedTasks = tasks.filter(task => task.task_id !== taskId)
      setTasks(updatedTasks)
      saveTasksToStorage(updatedTasks)

      // Try to delete from backend
      try {
        await fetch(`/api/case-management/tasks/${taskId}`, {
          method: 'DELETE'
        })
      } catch (error) {
        console.log('Backend not available for task deletion')
      }
      
      console.log('Task deleted successfully:', taskId)
    } catch (error) {
      console.error('Error deleting task:', error)
      throw error
    } finally {
      setLoading(false)
    }
  }

  const completeTask = async (taskId) => {
    await updateTask(taskId, { 
      status: 'completed',
      completed_at: new Date().toISOString()
    })
  }

  const syncTaskToBackend = async (task, isUpdate = false) => {
    try {
      setSyncing(true)
      
      const endpoint = isUpdate 
        ? `/api/case-management/tasks/update/${task.task_id}`
        : `/api/case-management/tasks/add/${clientId}`
      
      const method = isUpdate ? 'PUT' : 'POST'
      
      const response = await fetch(endpoint, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: task.title,
          description: task.description,
          priority: task.priority,
          status: task.status,
          task_type: task.task_type,
          due_date: task.due_date,
          assigned_to: task.assigned_to
        })
      })

      if (response.ok) {
        // Mark as synced
        const updatedTasks = tasks.map(t => 
          t.task_id === task.task_id ? { ...t, synced: true } : t
        )
        setTasks(updatedTasks)
        saveTasksToStorage(updatedTasks)
        console.log(`Task ${isUpdate ? 'updated' : 'synced'} to backend:`, task.task_id)
      }
    } catch (error) {
      console.log('Backend not available for task sync:', error.message)
    } finally {
      setSyncing(false)
    }
  }

  const syncAllTasks = async () => {
    const unsyncedTasks = tasks.filter(task => !task.synced)
    
    if (unsyncedTasks.length === 0) {
      console.log('All tasks are already synced')
      return
    }

    console.log(`Syncing ${unsyncedTasks.length} unsynced tasks...`)
    
    for (const task of unsyncedTasks) {
      await syncTaskToBackend(task)
      // Small delay to prevent overwhelming the server
      await new Promise(resolve => setTimeout(resolve, 100))
    }
  }

  const getFilteredTasks = (filter) => {
    if (filter === 'All') return tasks
    
    switch (filter) {
      case 'Pending':
        return tasks.filter(task => task.status === 'pending')
      case 'In Progress':
        return tasks.filter(task => task.status === 'in_progress')
      case 'Completed':
        return tasks.filter(task => task.status === 'completed')
      case 'Overdue':
        return tasks.filter(task => 
          task.status !== 'completed' && 
          new Date(task.due_date) < new Date()
        )
      case 'High Priority':
        return tasks.filter(task => task.priority === 'high' || task.priority === 'urgent')
      default:
        return tasks.filter(task => task.priority === filter.toLowerCase())
    }
  }

  const getTasksStats = () => {
    const total = tasks.length
    const pending = tasks.filter(task => task.status === 'pending').length
    const inProgress = tasks.filter(task => task.status === 'in_progress').length
    const completed = tasks.filter(task => task.status === 'completed').length
    const overdue = tasks.filter(task => 
      task.status !== 'completed' && 
      new Date(task.due_date) < new Date()
    ).length
    const urgent = tasks.filter(task => task.priority === 'urgent').length
    const high = tasks.filter(task => task.priority === 'high').length
    const unsynced = tasks.filter(task => !task.synced).length

    const byStatus = {
      'pending': pending,
      'in_progress': inProgress,
      'completed': completed,
      'overdue': overdue
    }

    const byPriority = {
      'urgent': urgent,
      'high': high,
      'medium': tasks.filter(task => task.priority === 'medium').length,
      'low': tasks.filter(task => task.priority === 'low').length
    }

    return {
      total,
      pending,
      inProgress,
      completed,
      overdue,
      urgent,
      high,
      unsynced,
      byStatus,
      byPriority
    }
  }

  const getTaskById = (taskId) => {
    return tasks.find(task => task.task_id === taskId)
  }

  return {
    tasks,
    loading,
    syncing,
    addTask,
    updateTask,
    deleteTask,
    completeTask,
    syncAllTasks,
    getFilteredTasks,
    getTasksStats,
    getTaskById,
    loadTasksFromStorage,
    loadTasksFromBackend
  }
}

export default useTasks