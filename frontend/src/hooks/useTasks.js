import { useState, useEffect } from 'react'
import { apiFetch } from '../api/config'

const useTasks = (clientId) => {
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(false)
  const [syncing, setSyncing] = useState(false)

  useEffect(() => {
    if (clientId) {
      loadTasksFromBackend()
    } else {
      setTasks([])
    }
  }, [clientId])

  const loadTasksFromBackend = async () => {
    try {
      const response = await apiFetch(`/api/case-management/tasks/list/${clientId}`)
      if (response.ok) {
        const data = await response.json()
        if (data.success && data.tasks) {
          const backendTasks = data.tasks
            .map(task => ({ ...task, synced: true }))
            .sort((a, b) => new Date(a.due_date || '9999-12-31') - new Date(b.due_date || '9999-12-31'))
          setTasks(backendTasks)
        }
      }
    } catch (error) {
      console.error('Backend not available for tasks loading:', error.message)
      setTasks([])
    }
  }

  const addTask = async (taskData) => {
    try {
      setLoading(true)
      
      const newTask = {
        title: taskData.title,
        description: taskData.description || '',
        priority: taskData.priority || 'medium',
        status: 'pending',
        task_type: taskData.task_type || 'general',
        due_date: taskData.due_date,
        assigned_to: taskData.assigned_to || 'Case Manager'
      }
      const createdTask = await syncTaskToBackend(newTask)
      await loadTasksFromBackend()
      return createdTask
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
      
      const currentTask = tasks.find(task => task.task_id === taskId)
      if (!currentTask) {
        throw new Error('Task not found')
      }
      const response = await apiFetch(`/api/case-management/tasks/update/${taskId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...currentTask,
          ...updates
        })
      })
      if (!response.ok) {
        throw new Error('Failed to update task')
      }
      const data = await response.json()
      setTasks(current => current.map(task => task.task_id === taskId ? { ...data.task, synced: true } : task))
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
      
      const response = await apiFetch(`/api/case-management/tasks/${taskId}`, {
        method: 'DELETE'
      })
      if (!response.ok) {
        throw new Error('Failed to delete task')
      }
      setTasks(current => current.filter(task => task.task_id !== taskId))
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
      
      const response = await apiFetch(endpoint, {
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
        const data = await response.json()
        return { ...(data.task || task), synced: true }
      }
      throw new Error('Task sync failed')
    } catch (error) {
      console.error('Backend not available for task sync:', error.message)
      throw error
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
    loadTasksFromBackend
  }
}

export default useTasks
