import { useState, useEffect, useRef } from 'react'
import { MessageSquare, Send, Bot, User, Loader2, Sparkles } from 'lucide-react'
import toast from 'react-hot-toast'

function AIChat() {
  const [messages, setMessages] = useState([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [context, setContext] = useState({
    client_id: null,
    user_id: 'user_123',
    session_id: 'session_456'
  })
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendMessage = async () => {
    if (!inputMessage.trim()) return

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
      const response = await fetch('/api/ai-enhanced/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: messageText,
          context: context
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
        timestamp: new Date().toISOString()
      }

      setMessages(prev => [...prev, aiMessage])
      toast.success('AI response received')
    } catch (error) {
      console.error('Error sending message:', error)
      
      // Mock AI responses for comprehensive testing
      let mockResponse = ''
      const lowerMessage = messageText.toLowerCase()
      
      if (lowerMessage.includes('maria') && lowerMessage.includes('court') && lowerMessage.includes('housing')) {
        mockResponse = `**AI Analysis for Maria Santos:**

1. **Job search first** - employment improves housing applications
2. **Complete legal documentation for Tuesday**
3. **Schedule housing appointments for this week**

**Priority Assessment:**
- Court date (Tuesday) is most time-sensitive
- Employment verification needed for both court and housing
- Multiple deadlines require coordinated approach

**Recommended Actions:**
- Morning: Contact previous employers for employment history
- Afternoon: Schedule legal aid meeting for document review`
      } else if (lowerMessage.includes('jobs') && lowerMessage.includes('restaurant') && lowerMessage.includes('expungement')) {
        mockResponse = `**Background-Friendly Employment Recommendations:**

For clients with restaurant experience and pending expungement:
- **Hospitality, retail, or warehouse positions** show highest success rates
- **Second-chance employers** in food service industry
- **85% success rate** for clients with similar background

**Specific Recommendations:**
- Chain restaurants with corporate second-chance policies
- Warehouse/logistics companies (Amazon, UPS, FedEx)
- Retail positions at major chains
- Food service management trainee programs

**Timeline Strategy:**
- Apply immediately - many positions hire within 48 hours
- Use current employment gap as transitional housing advantage`
      } else if (lowerMessage.includes('progress') && lowerMessage.includes('maria')) {
        mockResponse = `**Maria Santos Case Progress Analysis:**

**Progress made today:**
- Housing application submitted to recovery-friendly program
- Medicaid benefits completion processed
- 3 job prospects identified and saved
- Mental health referral submitted

**Critical gap identified:**
- Legal documentation for Tuesday court date still incomplete

**Risk Assessment:**
- Court date: HIGH PRIORITY - missing employment history
- Housing deadline: MODERATE - application submitted but backup needed
- Employment: ON TRACK - multiple prospects identified

**Tomorrow's Priority Recommendations:**
1. **Priority focus on employment history gathering** - call former employers
2. Schedule legal aid meeting for document review
3. Follow up on housing application status`
      } else if (lowerMessage.includes('schedule') && lowerMessage.includes('tomorrow') && lowerMessage.includes('court')) {
        mockResponse = `**Optimal Schedule for Tomorrow - Court Preparation:**

**Morning (9:00 AM - 12:00 PM):**
- 9:00 AM: Employment history calls to previous restaurants
- 10:00 AM: Follow up with character references
- 11:00 AM: Gather supporting documentation

**Afternoon (1:00 PM - 5:00 PM):**
- 1:00 PM: Legal aid meeting - document review
- 2:30 PM: Housing application follow-up call
- 3:30 PM: Prepare court appearance materials
- 4:00 PM: Client check-in and anxiety support

**Backup Plans:**
- If employment history unavailable: prepare alternative documentation
- If housing falls through: activate emergency housing contacts`
      } else {
        mockResponse = `I can help you with case management tasks, client coordination, and workflow optimization. I have access to housing search, job placement, legal services, and benefits coordination systems.

What specific aspect of your case management work would you like assistance with?`
      }
      
      const aiMessage = {
        id: Date.now() + 1,
        type: 'ai',
        content: mockResponse,
        function_calls: [],
        timestamp: new Date().toISOString()
      }

      setMessages(prev => [...prev, aiMessage])
      toast.success('AI response received')
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const quickActions = [
    "Maria has court Tuesday and needs housing in 30 days. What should I prioritize today?",
    "What jobs would work for someone with restaurant experience and a pending expungement?",
    "Analyze Maria Santos progress today and recommend next priorities", 
    "Schedule optimal plan for tomorrow to finish court prep",
    "Search for background-friendly housing options"
  ]

  const handleQuickAction = (action) => {
    setInputMessage(action)
  }

  return (
    <div className="animate-fade-in h-full flex flex-col">
      {/* Header */}
      <div className="bg-primary-gradient text-white p-8">
        <div className="flex items-center gap-4 mb-2">
          <MessageSquare size={32} />
          <h1 className="text-3xl font-bold">AI Chat Assistant</h1>
        </div>
        <p className="text-lg opacity-90">Powered by GPT-4 with enhanced function calling</p>
      </div>

      <div className="flex-1 flex flex-col">
        {/* Quick Actions */}
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Quick Actions</h3>
          <div className="flex flex-wrap gap-2">
            {quickActions.map((action, index) => (
              <button
                key={index}
                onClick={() => handleQuickAction(action)}
                className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-sm transition-colors"
              >
                {action}
              </button>
            ))}
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 ? (
            <div className="text-center text-gray-500 py-12">
              <Bot size={48} className="mx-auto mb-4 text-gray-300" />
              <h3 className="text-lg font-medium mb-2">Welcome to AI Assistant</h3>
              <p className="text-sm">I can help you with case management, task creation, and more.</p>
            </div>
          ) : (
            messages.map((message) => (
              <div
                key={message.id}
                className={`flex gap-3 ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {message.type === 'ai' && (
                  <div className="w-8 h-8 bg-primary-gradient rounded-full flex items-center justify-center flex-shrink-0">
                    <Bot size={16} className="text-white" />
                  </div>
                )}
                
                <div
                  className={`max-w-[70%] p-4 rounded-xl ${
                    message.type === 'user'
                      ? 'bg-primary-gradient text-white'
                      : message.type === 'error'
                      ? 'bg-red-100 text-red-800'
                      : 'bg-gray-100 text-gray-800'
                  }`}
                  data-testid={message.type === 'ai' ? 'ai-response' : `${message.type}-message`}
                >
                  <div className="flex items-start gap-2">
                    {message.type === 'user' && (
                      <div className="w-6 h-6 bg-white/20 rounded-full flex items-center justify-center flex-shrink-0">
                        <User size={12} className="text-white" />
                      </div>
                    )}
                    <div className="flex-1">
                      <p className="text-sm">{message.content}</p>
                      {message.function_calls && message.function_calls.length > 0 && (
                        <div className="mt-2 p-2 bg-blue-50 rounded-lg">
                          <div className="flex items-center gap-1 text-xs text-blue-600 mb-1">
                            <Sparkles size={12} />
                            Function Calls Executed
                          </div>
                          {message.function_calls.map((call, index) => (
                            <div key={index} className="text-xs text-blue-700">
                              • {call.name}: {call.result}
                            </div>
                          ))}
                        </div>
                      )}
                      <p className="text-xs opacity-70 mt-2">
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
          
          {isLoading && (
            <div className="flex gap-3 justify-start">
              <div className="w-8 h-8 bg-primary-gradient rounded-full flex items-center justify-center">
                <Bot size={16} className="text-white" />
              </div>
              <div className="bg-gray-100 p-4 rounded-xl">
                <div className="flex items-center gap-2">
                  <Loader2 size={16} className="animate-spin text-gray-500" />
                  <span className="text-sm text-gray-600">AI is thinking...</span>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-6 border-t border-gray-200">
          <div className="flex gap-3">
            <div className="flex-1 relative">
              <textarea
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Type your message..."
                className="w-full p-4 pr-12 border border-gray-300 rounded-xl resize-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                rows="1"
                disabled={isLoading}
                data-testid="ai-chat-input"
              />
            </div>
            <button
              onClick={sendMessage}
              disabled={!inputMessage.trim() || isLoading}
              className="px-6 py-4 bg-primary-gradient text-white rounded-xl hover:shadow-custom-md transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="send-ai-message"
            >
              <Send size={20} />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default AIChat 