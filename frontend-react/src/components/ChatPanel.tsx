import { useState, useRef, useEffect } from 'react'
import { Send } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface Props {
  currentPage: string
  domain: string
  onShowAdHocReport: (content: string, title?: string) => void
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  toolsCalled?: string[]
}

export default function ChatPanel({ currentPage, domain, onShowAdHocReport }: Props) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: `Welcome to KetZero Intel. I can help you explore ${domain} computing intelligence. Ask me anything about the data on this page or across the corpus.`,
    },
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [currentStreamingMessage, setCurrentStreamingMessage] = useState<Message | null>(null)
  const endRef = useRef<HTMLDivElement>(null)

  // Track if we're currently streaming to allow auto-scroll
  const [isAutoScrolling, setIsAutoScrolling] = useState(true)

  useEffect(() => {
    if (isAutoScrolling) {
      endRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, currentStreamingMessage, isAutoScrolling])

  // Simple scroll detect to disable auto-scroll if user scrolls up
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget
    const isAtBottom = scrollTop + clientHeight >= scrollHeight - 50
    setIsAutoScrolling(isAtBottom)
  }

  // Listen for "Send to Chat" from Insight Builder
  const pendingMessageRef = useRef<string | null>(null)

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent<{ message: string }>).detail
      if (detail?.message) {
        pendingMessageRef.current = detail.message
        setInput(detail.message)
      }
    }
    window.addEventListener('ketzero-send-to-chat', handler)
    return () => window.removeEventListener('ketzero-send-to-chat', handler)
  }, [])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    setIsAutoScrolling(true)
    const userMsg: Message = { role: 'user', content: input.trim() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setIsLoading(true)

    // Create an empty assistant message to hold streaming content
    setCurrentStreamingMessage({ role: 'assistant', content: '', toolsCalled: [] })

    try {
      // Create search params for the GET stream request
      const params = new URLSearchParams({
        message: userMsg.content,
        domain: domain,
        currentPage: currentPage,
        sessionId: 'default'
      })

      const response = await fetch(`/api/chat/stream?${params.toString()}`, {
        method: 'GET',
      })

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`)
      }

      if (!response.body) {
        throw new Error('ReadableStream not supported')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''

      let finalContent = ''
      let finalTools: string[] = []

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // Process complete SSE events from the buffer
        let eventEnd = buffer.indexOf('\n\n')
        while (eventEnd !== -1) {
          const eventString = buffer.slice(0, eventEnd).trim()
          buffer = buffer.slice(eventEnd + 2)

          if (eventString) {
            let event = 'message'
            let dataStr = ''

            // Parse standard SSE format
            const lines = eventString.split('\n')
            for (const line of lines) {
              if (line.startsWith('event: ')) {
                event = line.substring(7).trim()
              } else if (line.startsWith('data: ')) {
                dataStr = line.substring(6).trim()
              }
            }

            if (dataStr) {
              try {
                const data = JSON.parse(dataStr)

                // Handle specific event types
                if (event === 'text_delta') {
                  finalContent += data.text
                  setCurrentStreamingMessage({
                    role: 'assistant',
                    content: finalContent + ' ▍', // Add cursor
                    toolsCalled: [...finalTools]
                  })
                }
                else if (event === 'tool_call') {
                  finalTools.push(data.tool)
                  setCurrentStreamingMessage({
                    role: 'assistant',
                    content: finalContent + ' ▍',
                    toolsCalled: [...finalTools]
                  })
                }
                else if (event === 'thinking') {
                  // Just a heartbeat
                }
                else if (event === 'error') {
                  finalContent += `\n\n> Error: ${data.error}`
                  setCurrentStreamingMessage({
                    role: 'assistant',
                    content: finalContent,
                    toolsCalled: finalTools
                  })
                }
                else if (event === 'complete') {
                  // Done, process commands
                  if (data.frontend_command) {
                    const cmd = data.frontend_command
                    if (cmd.action === 'navigate' && cmd.target) {
                      window.location.href = cmd.target
                    } else if (cmd.action === 'open_modal') {
                      onShowAdHocReport("Opening requested report...")
                    }
                  }

                  // Check for embedded images/infographics
                  if (finalContent.includes("![")) {
                    onShowAdHocReport(finalContent, "Ad-Hoc Analysis: " + currentPage)
                  }
                }
              } catch (e) {
                console.error("Failed to parse SSE JSON:", dataStr, e)
              }
            }
          }
          eventEnd = buffer.indexOf('\n\n')
        }
      }

      // Stream finished, move from temporary state to permanent messages list
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: finalContent || "I received an empty response.",
          toolsCalled: finalTools
        },
      ])

      setCurrentStreamingMessage(null)

    } catch (error) {
      console.error("Chat error:", error)
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: 'Connection to intelligence agent failed. Please ensure the API is running.' }
      ])
      setCurrentStreamingMessage(null)
    } finally {
      setIsLoading(false)
    }
  }

  // Auto-send when input is populated by the Insight Builder event
  useEffect(() => {
    if (pendingMessageRef.current && input === pendingMessageRef.current && !isLoading) {
      pendingMessageRef.current = null
      handleSend()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [input])

  // Helper to render message content with optional tool usage indicator
  const renderMessageContent = (msg: Message) => {
    return (
      <div className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
        <div className="flex flex-col max-w-[85%]">
          <div
            className={`rounded-lg px-3 py-2 text-sm leading-relaxed ${msg.role === 'user'
              ? 'bg-accent-teal/15 text-accent-teal'
              : 'bg-bg-tertiary text-text-primary'
              }`}
          >
            {msg.role === 'assistant' ? (
              <div className="prose prose-sm prose-invert max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {msg.content}
                </ReactMarkdown>
              </div>
            ) : (
              msg.content
            )}
          </div>

          {/* Tool usage indicator */}
          {msg.role === 'assistant' && msg.toolsCalled && msg.toolsCalled.length > 0 && (
            <div className="mt-1 flex flex-wrap gap-1">
              {msg.toolsCalled.map((tool, idx) => (
                <span key={idx} className="text-[10px] px-1.5 py-0.5 rounded-full bg-bg-secondary text-text-muted border border-border">
                  ⚡ {tool.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    )
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
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4" onScroll={handleScroll}>
        {messages.map((msg, i) => (
          <div key={i}>{renderMessageContent(msg)}</div>
        ))}

        {/* Render currently streaming message */}
        {currentStreamingMessage && (
          <div>{renderMessageContent(currentStreamingMessage)}</div>
        )}

        {isLoading && !currentStreamingMessage && (
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
