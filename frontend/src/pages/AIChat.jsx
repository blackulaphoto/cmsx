import { useState, useEffect, useRef } from 'react'
import { MessageSquare, Send, Bot, User, Loader2, Sparkles, Zap, Brain, Stars, Save, BookOpen, StickyNote, Bookmark } from 'lucide-react'
import toast from 'react-hot-toast'

const SESSION_KEY = 'ai_assistant_session_id'

const getSessionId = () => {
  const existing = window.localStorage.getItem(SESSION_KEY)
  if (existing) return existing
  const created = `session_${crypto.randomUUID()}`
  window.localStorage.setItem(SESSION_KEY, created)
  return created
}

function AIChat() {
  const [messages, setMessages] = useState([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [context, setContext] = useState({
    client_id: null,
    user_id: null,
    session_id: null
  })
  const [autoSaveResults, setAutoSaveResults] = useState({})
  const messagesContainerRef = useRef(null)
  const [isAtBottom, setIsAtBottom] = useState(true)

  const handleMessagesScroll = () => {
    const container = messagesContainerRef.current
    if (!container) return
    const threshold = 120
    const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight
    setIsAtBottom(distanceFromBottom <= threshold)
  }

  useEffect(() => {
    if (!isAtBottom) return
    const container = messagesContainerRef.current
    if (!container) return
    container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' })
  }, [messages, isAtBottom])

  // EXACT handlers from working debug version
  const handleInputChange = (e) => {
    setInputMessage(e.target.value)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const sendMessage = async () => {
    if (!inputMessage.trim()) {
      toast.error('Please enter a message')
      return
    }

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, userMessage])
    const messageText = inputMessage
    setInputMessage('')
    setIsLoading(true)

    try {
      const response = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: messageText,
          case_manager_id: getSessionId()
        })
      })

      if (!response.ok) {
        throw new Error('Failed to send message')
      }

      const data = await response.json()
      
      const aiMessage = {
        id: Date.now() + 1,
        type: 'ai',
        content: data.response,
        function_calls: data.function_calls,
        auto_save_results: data.auto_save_results,
        timestamp: new Date().toISOString()
      }

      setMessages(prev => [...prev, aiMessage])
      
      // Handle auto-save notifications
      if (data.auto_save_results && data.auto_save_results.analysis?.auto_save_triggered) {
        const results = data.auto_save_results
        let saveMessage = "Content automatically saved to dashboard: "
        const saved = []
        
        if (results.notes_saved?.length > 0) {
          saved.push(`${results.notes_saved.length} note(s)`)
        }
        if (results.docs_saved?.length > 0) {
          saved.push(`${results.docs_saved.length} document(s)`)
        }
        if (results.bookmarks_saved?.length > 0) {
          saved.push(`${results.bookmarks_saved.length} bookmark(s)`)
        }
        
        if (saved.length > 0) {
          toast.success(saveMessage + saved.join(', '))
        }
      }
      
      toast.success('AI response received')
    } catch (error) {
      console.error('Error sending message:', error)
      
      const errorMessage = {
        id: Date.now() + 1,
        type: 'system',
        content: `⚠️ Error: Could not reach AI service\n\nDetails: ${error?.message || 'Unknown error'}\n\nPlease check:\n• Backend server is running\n• API endpoint is accessible at /api/ai/chat\n• Network connection is stable`,
        timestamp: new Date().toISOString()
      }

      setMessages(prev => [...prev, errorMessage])
      toast.error(`Failed to send message: ${error?.message || 'Unknown error'}`)
    } finally {
      setIsLoading(false)
    }
  }

  const quickActions = [
    "Maria has court Tuesday and needs housing in 30 days. What should I prioritize today?",
    "What jobs would work for someone with restaurant experience and a pending expungement?",
    "Analyze this client's progress today and recommend next priorities", 
    "Schedule optimal plan for tomorrow to finish court prep",
    "Search for background-friendly housing options"
  ]

  const handleQuickAction = (action) => {
    setInputMessage(action)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Background Elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-cyan-500/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute top-1/2 -left-40 w-80 h-80 bg-purple-500/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
        <div className="absolute -bottom-40 right-1/3 w-80 h-80 bg-pink-500/10 rounded-full blur-3xl animate-pulse delay-2000"></div>
      </div>

      <div className="relative z-10">
        {/* Header */}
        <div className="bg-black/20 border-b border-white/10 backdrop-blur-sm">
          <div className="max-w-7xl mx-auto px-6 py-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-gradient-to-r from-cyan-500 to-purple-500 rounded-xl shadow-lg">
                <MessageSquare className="h-8 w-8 text-white" />
              </div>
              <div>
                <h1 className="text-4xl font-bold bg-gradient-to-r from-white via-cyan-200 to-purple-200 bg-clip-text text-transparent">
                  AI Chat Assistant
                </h1>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                  <span className="text-gray-300">Powered by GPT-4</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-6">
          {/* Quick Actions */}
          <div className="py-6 border-b border-white/10">
            <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <Zap className="h-5 w-5 text-yellow-400" />
              Quick Actions
            </h3>
            <div className="flex flex-wrap gap-3">
              {quickActions.map((action, index) => (
                <button
                  key={index}
                  onClick={() => handleQuickAction(action)}
                  className="px-4 py-3 bg-white/10 border border-white/20 hover:bg-white/20 text-gray-300 hover:text-white rounded-xl text-sm transition-all duration-300"
                >
                  <div className="flex items-center gap-2">
                    <Sparkles size={14} className="text-cyan-400" />
                    <span>{action}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Messages */}
          <div
            className="overflow-y-auto py-6 space-y-6"
            style={{ height: 'calc(100vh - 400px)', minHeight: '400px' }}
            ref={messagesContainerRef}
            onScroll={handleMessagesScroll}
          >
            {messages.length === 0 ? (
              <div className="text-center py-16 bg-white/5 rounded-2xl border border-white/10">
                <div className="p-6 bg-cyan-500/20 rounded-2xl w-fit mx-auto mb-6">
                  <Bot size={48} className="text-cyan-400" />
                </div>
                <h3 className="text-2xl font-bold text-white mb-3">Welcome to AI Assistant</h3>
                <p className="text-gray-400 mb-6">I can help you with case management, task creation, and intelligent insights.</p>
                <div className="flex items-center justify-center gap-2 text-sm text-cyan-400">
                  <Stars size={16} />
                  <span>Powered by Advanced AI</span>
                  <Stars size={16} />
                </div>
              </div>
            ) : (
              messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex gap-4 ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {message.type === 'ai' && (
                    <div className="w-10 h-10 bg-gradient-to-r from-cyan-500 to-purple-500 rounded-full flex items-center justify-center flex-shrink-0">
                      <Bot size={20} className="text-white" />
                    </div>
                  )}
                  
                  <div className="max-w-[75%]">
                    <div
                      className={`p-6 rounded-2xl ${
                        message.type === 'user'
                          ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white'
                          : 'bg-white/10 border border-white/20 text-gray-100'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        {message.type === 'user' && (
                          <div className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center flex-shrink-0">
                            <User size={16} className="text-white" />
                          </div>
                        )}
                        <div className="flex-1">
                          <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 mt-2 px-2">
                      <p className="text-xs text-gray-500">
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </p>
                      
                      {/* Auto-save indicators */}
                      {message.auto_save_results && message.auto_save_results.analysis?.auto_save_triggered && (
                        <div className="flex items-center gap-1 ml-2">
                          <Save size={12} className="text-green-400" />
                          <span className="text-xs text-green-400">Auto-saved</span>
                          
                          {/* Show what was saved */}
                          <div className="flex items-center gap-1 ml-1">
                            {message.auto_save_results.notes_saved?.length > 0 && (
                              <div className="flex items-center gap-1">
                                <StickyNote size={10} className="text-yellow-400" />
                                <span className="text-xs text-yellow-400">{message.auto_save_results.notes_saved.length}</span>
                              </div>
                            )}
                            {message.auto_save_results.docs_saved?.length > 0 && (
                              <div className="flex items-center gap-1">
                                <BookOpen size={10} className="text-blue-400" />
                                <span className="text-xs text-blue-400">{message.auto_save_results.docs_saved.length}</span>
                              </div>
                            )}
                            {message.auto_save_results.bookmarks_saved?.length > 0 && (
                              <div className="flex items-center gap-1">
                                <Bookmark size={10} className="text-green-400" />
                                <span className="text-xs text-green-400">{message.auto_save_results.bookmarks_saved.length}</span>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {message.type === 'user' && (
                    <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full flex items-center justify-center flex-shrink-0">
                      <User size={20} className="text-white" />
                    </div>
                  )}
                </div>
              ))
            )}
            
            {isLoading && (
              <div className="flex gap-4 justify-start">
                <div className="w-10 h-10 bg-gradient-to-r from-cyan-500 to-purple-500 rounded-full flex items-center justify-center">
                  <Bot size={20} className="text-white" />
                </div>
                <div className="bg-white/10 border border-white/20 p-6 rounded-2xl">
                  <div className="flex items-center gap-3">
                    <Loader2 size={20} className="animate-spin text-cyan-400" />
                    <span className="text-sm text-white">AI is thinking...</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Input Section - EXACT styling from working debug version */}
          <div className="sticky bottom-0 bg-slate-900 py-6 border-t border-white/10">
            <div className="flex gap-4">
              {/* WORKING INPUT - exact same as debug version */}
              <input
                type="text"
                value={inputMessage}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                placeholder="Type your message to the AI assistant..."
                className="flex-1 p-4 bg-white/20 border-2 border-cyan-500 rounded-lg text-white placeholder-gray-300 focus:outline-none focus:border-cyan-300"
                disabled={isLoading}
                data-testid="ai-chat-input"
                autoComplete="off"
                autoFocus
              />
              
              <button
                onClick={sendMessage}
                disabled={!inputMessage.trim() || isLoading}
                className="px-6 py-4 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                data-testid="send-ai-message"
              >
                <Send size={20} />
                <span className="hidden sm:block">Send</span>
              </button>
            </div>
            
            <div className="flex items-center justify-between mt-3 text-xs text-gray-400">
              <div className="flex items-center gap-2">
                <div className="w-1 h-1 bg-green-400 rounded-full animate-pulse"></div>
                <span>AI Assistant is online and ready</span>
              </div>
              <span>Press Enter to send</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default AIChat
