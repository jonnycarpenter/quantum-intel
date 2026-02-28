import { useState, useRef, useEffect } from 'react'
import { Send } from 'lucide-react'

interface Props {
  currentPage: string
  domain: string
}

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export default function ChatPanel({ currentPage, domain }: Props) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: `Welcome to KetZero Intel. I can help you explore ${domain} computing intelligence. Ask me anything about the data on this page or across the corpus.`,
    },
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return
    const userMsg: Message = { role: 'user', content: input.trim() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setIsLoading(true)

    // TODO: Wire to /api/chat SSE endpoint when agent integration is built
    setTimeout(() => {
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: `I'm currently in preview mode. The full agent integration (with corpus search, stock data, and web search tools) will be connected in the next phase. You asked about: "${userMsg.content}" on the ${currentPage} page.`,
        },
      ])
      setIsLoading(false)
    }, 800)
  }

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Context indicator */}
      <div className="px-4 py-2 border-b border-border">
        <div className="flex items-center gap-2 text-xs text-text-muted">
          <span className="w-1.5 h-1.5 rounded-full bg-accent-green" />
          Context: {currentPage} • {domain === 'quantum' ? 'Quantum' : 'AI'}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[85%] rounded-lg px-3 py-2 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-accent-teal/15 text-accent-teal'
                  : 'bg-bg-tertiary text-text-primary'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-bg-tertiary rounded-lg px-3 py-2 text-sm text-text-muted">
              <span className="animate-pulse">Thinking...</span>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Input */}
      <div className="p-3 border-t border-border">
        <div className="flex items-center gap-2 bg-bg-tertiary rounded-lg px-3 py-2">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
            placeholder="Ask about the data..."
            className="flex-1 bg-transparent text-sm text-text-primary placeholder-text-muted outline-none"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="text-accent-blue hover:text-accent-cyan disabled:text-text-muted transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
