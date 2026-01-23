import { MessageCircle } from 'lucide-react'

export default function AIAssistantButton({ onClick, hasUnread }) {
  return (
    <button
      onClick={onClick}
      className="fixed bottom-6 right-6 w-14 h-14 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full shadow-lg hover:shadow-xl transition-all duration-300 flex items-center justify-center hover:scale-110 z-50"
      aria-label="Open AI Assistant"
    >
      <MessageCircle className="w-6 h-6 text-white" />
      {hasUnread && (
        <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full border-2 border-white" />
      )}
    </button>
  )
}
