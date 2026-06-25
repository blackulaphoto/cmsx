import { useEffect, useRef, useState } from 'react'
import { MessageCircle, Minimize2, PenSquare, Send, X } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import AIAssistantButton from './AIAssistantButton'
import { apiFetch } from '../../api/config'

const assistantMessageClasses = 'bg-gray-100 text-gray-900 break-words leading-relaxed'

// Initial conversation state. An empty history renders the assistant greeting
// (see the empty-state block below). Reused by the "New Chat" reset so the
// reset behaviour stays clean and testable.
const INITIAL_MESSAGES = []

const markdownComponents = {
  h1: ({ children }) => <p className="font-semibold text-gray-900 mb-1">{children}</p>,
  h2: ({ children }) => <p className="font-semibold text-gray-900 mb-1">{children}</p>,
  h3: ({ children }) => <p className="font-semibold text-gray-900 mb-1">{children}</p>,
  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
  ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-0.5">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-0.5">{children}</ol>,
  li: ({ children }) => <li>{children}</li>,
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  code: ({ children }) => (
    <code className="bg-gray-200 rounded px-1 py-0.5 text-xs font-mono">{children}</code>
  ),
}

export default function AIAssistantPopup() {
  const [isOpen, setIsOpen] = useState(false)
  const [isMinimized, setIsMinimized] = useState(false)
  const [messages, setMessages] = useState(INITIAL_MESSAGES)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const containerRef = useRef(null)

  // Clears the in-popup conversation back to the initial greeting. Frontend-only:
  // no backend call, no logout, no app/client/page state touched. Disabled while
  // a request is in flight to avoid resetting mid-response.
  const startNewChat = () => {
    if (loading) return
    setMessages(INITIAL_MESSAGES)
    setInput('')
  }

  useEffect(() => {
    if (!isOpen || isMinimized) return
    const container = containerRef.current
    if (!container) return
    container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' })
  }, [messages, isOpen, isMinimized])

  const sendMessage = async () => {
    if (!input.trim() || loading) return

    const messageText = input.trim()
    setMessages((prev) => [...prev, { role: 'user', content: messageText }])
    setInput('')
    setLoading(true)

    try {
      const response = await apiFetch('/api/ai/assistant', {
        timeoutMs: 30000,
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: messageText,
          current_route: window.location.pathname,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to send message')
      }

      const data = await response.json()
      setMessages((prev) => [...prev, { role: 'assistant', content: data.response }])
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Error: ${error?.message || 'Unable to reach AI assistant.'}`,
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) {
    return <AIAssistantButton onClick={() => setIsOpen(true)} />
  }

  if (isMinimized) {
    return (
      <div
        className="fixed bottom-6 right-6 bg-white rounded-lg shadow-xl px-4 py-3 cursor-pointer z-50"
        onClick={() => setIsMinimized(false)}
      >
        <div className="flex items-center gap-2">
          <MessageCircle className="w-5 h-5 text-blue-600" />
          <span className="font-medium text-gray-900">AI Assistant</span>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed bottom-6 right-6 w-96 h-[600px] bg-white rounded-2xl shadow-2xl flex flex-col z-50">
      <div className="flex items-center justify-between p-4 border-b bg-gradient-to-r from-blue-500 to-purple-600 rounded-t-2xl">
        <div className="flex items-center gap-2">
          <MessageCircle className="w-5 h-5 text-white" />
          <h3 className="font-semibold text-white">AI Assistant</h3>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={startNewChat}
            disabled={loading}
            className="flex items-center gap-1 text-white hover:bg-white/20 px-2 py-1 rounded text-xs font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Start new chat"
            title="New Chat"
          >
            <PenSquare className="w-4 h-4" />
            <span className="hidden sm:inline">New Chat</span>
          </button>
          <button
            onClick={() => setIsMinimized(true)}
            className="text-white hover:bg-white/20 p-1 rounded"
            aria-label="Minimize assistant"
          >
            <Minimize2 className="w-4 h-4" />
          </button>
          <button
            onClick={() => setIsOpen(false)}
            className="text-white hover:bg-white/20 p-1 rounded"
            aria-label="Close assistant"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div ref={containerRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-8">
            <MessageCircle className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <p className="font-medium">AI Research Assistant</p>
            <p className="text-sm mt-2">
              Ask me to research resources or draft documents.
            </p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[80%] p-3 rounded-lg ${
                msg.role === 'user'
                  ? 'bg-blue-500 text-white'
                  : assistantMessageClasses
              }`}
              data-testid={msg.role === 'assistant' ? 'assistant-message' : undefined}
            >
              {msg.role === 'assistant' ? (
                <ReactMarkdown components={markdownComponents}>
                  {msg.content}
                </ReactMarkdown>
              ) : (
                msg.content
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 p-3 rounded-lg">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                <div
                  className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                  style={{ animationDelay: '0.1s' }}
                />
                <div
                  className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                  style={{ animationDelay: '0.2s' }}
                />
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="p-4 border-t">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                sendMessage()
              }
            }}
            placeholder="Ask me anything..."
            className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            aria-label="Send message"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
