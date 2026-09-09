import { useEffect, useState, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '@/lib/api'
import type { Conversation, ChatMessage } from '@/lib/types'
import { MessageSquare, Send, Trash2, ClipboardList } from 'lucide-react'

interface ScreeningRecommendation {
  id: string
  name: string
  description: string
}

const INSTRUMENT_MAP: Record<string, ScreeningRecommendation> = {
  PHQ9: { id: 'PHQ9', name: 'PHQ-9 (Depression)', description: 'Patient Health Questionnaire-9 — screens for depressive symptoms' },
  GAD7: { id: 'GAD7', name: 'GAD-7 (Anxiety)', description: 'Generalized Anxiety Disorder-7 — screens for anxiety symptoms' },
  PHQ4: { id: 'PHQ4', name: 'PHQ-4 (Brief)', description: 'Patient Health Questionnaire-4 — brief depression & anxiety screen' },
  'SAFE-T': { id: 'SAFE-T', name: 'SAFE-T / C-SSRS (Suicide Risk)', description: 'Suicide Assessment Five-Step Evaluation — screens for suicide risk' },
}

function detectScreeningRecommendation(text: string): ScreeningRecommendation | null {
  const lower = text.toLowerCase()
  for (const [key, rec] of Object.entries(INSTRUMENT_MAP)) {
    if (lower.includes(key.toLowerCase())) {
      if (
        lower.includes('would you like to take') ||
        lower.includes('would you like to go through') ||
        lower.includes('would you like to continue') ||
        lower.includes('may be useful') ||
        lower.includes('could be useful') ||
        lower.includes('screening questionnaire') ||
        lower.includes('screener') ||
        lower.includes('screening') ||
        lower.includes('recommended')
      ) {
        return rec
      }
    }
  }
  return null
}

export default function ChatPage() {
  const navigate = useNavigate()
  const [conversation, setConversation] = useState<Conversation | null>(null)
  const [input, setInput] = useState(() => sessionStorage.getItem('chat_input') || '')
  const [sending, setSending] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [streamingText, setStreamingText] = useState('')
  const [activeRecommendation, setActiveRecommendation] = useState<ScreeningRecommendation | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const isMounted = useRef(true)

  useEffect(() => {
    isMounted.current = true
    api.get('/chat')
      .then(res => {
        if (isMounted.current) {
          setConversation(res.data)
          requestAnimationFrame(() => {
            inputRef.current?.focus()
          })
        }
      })
      .catch(() => {})

    return () => {
      isMounted.current = false
    }
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [conversation?.messages.length, streamingText, activeRecommendation])

  useEffect(() => {
    const visibilityChange = async () => {
      if (isMounted.current) {
        try {
          const res = await api.get('/chat')
          if (isMounted.current) {
            setConversation(res.data)
          }
        } catch {
          // best effort
        }
      }
    }

    document.addEventListener('visibilitychange', visibilityChange)

    return () => {
      document.removeEventListener('visibilitychange', visibilityChange)
    }
  }, [])

  useEffect(() => {
    if (!sending && conversation?.is_generating) {
      const poll = setInterval(async () => {
        try {
          const res = await api.get('/chat')
          if (isMounted.current) {
            setConversation(res.data)
          }
        } catch {
          // keep polling
        }
      }, 2000)

      return () => clearInterval(poll)
    }
  }, [sending, conversation?.is_generating])

  const notifyScreeningSuggested = useCallback(async (instrumentId: string) => {
    try {
      await api.post('/chat/screening-suggested', { instrument_id: instrumentId })
    } catch {
      // Best-effort
    }
  }, [])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || sending) return
    setInput('')
    sessionStorage.removeItem('chat_input')
    setSending(true)
    setStreamingText('')
    setActiveRecommendation(null)

    const userMsg: ChatMessage = {
      message_id: `temp-${Date.now()}`,
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    }

    if (conversation) {
      setConversation({ ...conversation, messages: [...conversation.messages, userMsg] })
    }

    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch(`${api.defaults.baseURL}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ content: text }),
      })

      if (!res.ok) {
        throw new Error(`Chat request failed: ${res.status}`)
      }

      const reader = res.body?.getReader()
      if (!reader) {
        throw new Error('No response stream')
      }

      const decoder = new TextDecoder()
      let accumulated = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') break
            accumulated += data
            setStreamingText(accumulated)
          }
        }
      }

      setStreamingText('')
      const freshRes = await api.get('/chat')
      setConversation(freshRes.data)

      // Detect screening recommendation
      const recommendation = detectScreeningRecommendation(accumulated)
      if (recommendation) {
        setActiveRecommendation(recommendation)
        notifyScreeningSuggested(recommendation.id)
      }
    } catch {
      setStreamingText('')
      api.get('/chat').then(res => setConversation(res.data)).catch(() => {})
    } finally {
      setSending(false)
    }
  }

  const handleDelete = async () => {
    if (!confirm('Delete entire chat history?')) return
    setDeleting(true)
    setActiveRecommendation(null)
    try {
      await api.delete('/chat')
      const res = await api.get('/chat')
      setConversation(res.data)
      requestAnimationFrame(() => {
        inputRef.current?.focus()
      })
    } catch {
      setConversation(null)
    } finally {
      setDeleting(false)
      requestAnimationFrame(() => {
        inputRef.current?.focus()
      })
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleTakeScreening = (instrumentId: string) => {
    navigate(`/screener?instrument=${instrumentId}`)
  }

  const messages: ChatMessage[] = conversation?.messages || []
  const lastAssistantIdx = messages.length > 0
    ? messages.map((m, i) => m.role === 'assistant' ? i : -1).filter(i => i >= 0).pop()
    : undefined

  return (
    <div className="flex h-full flex-col max-w-3xl mx-auto">
      <div className="flex items-center justify-between border-b pb-4 mb-4">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <MessageSquare className="h-6 w-6" /> Chat
        </h1>
        {messages.length > 0 && (
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="flex items-center gap-1 rounded-md px-3 py-1.5 text-sm font-medium text-destructive hover:bg-destructive/10 disabled:opacity-50"
          >
            <Trash2 className="h-4 w-4" />
            Delete Chat
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {(messages.length === 0 && !conversation) && (
          <div className="flex justify-center py-12 text-muted-foreground">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          </div>
        )}
        {messages.map((msg, idx) => (
          <div key={msg.message_id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[75%] rounded-lg px-4 py-2.5 ${
              msg.role === 'user'
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-foreground'
            }`}>
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>

              {/* Show screening recommendation card on the last assistant message */}
              {msg.role === 'assistant' && idx === lastAssistantIdx && activeRecommendation && (
                <div className="mt-3 p-3 bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded-lg">
                  <div className="flex items-start gap-2">
                    <ClipboardList className="h-4 w-4 text-blue-600 dark:text-blue-400 mt-0.5 shrink-0" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-blue-800 dark:text-blue-300">
                        Recommended: {activeRecommendation.name}
                      </p>
                      <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">
                        {activeRecommendation.description}
                      </p>
                      <button
                        onClick={() => handleTakeScreening(activeRecommendation.id)}
                        className="mt-2 px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded-md hover:bg-blue-700 transition-colors"
                      >
                        Take Screening
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
        {streamingText && (
          <div className="flex justify-start">
            <div className="max-w-[75%] rounded-lg px-4 py-2.5 bg-muted text-foreground">
              <p className="text-sm whitespace-pre-wrap">{streamingText}</p>
              <span className="inline-block w-1.5 h-4 ml-0.5 bg-foreground/60 animate-pulse" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t pt-4">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={e => {
              setInput(e.target.value)
              sessionStorage.setItem('chat_input', e.target.value)
            }}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            disabled={sending || !conversation}
            className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={sending || !input.trim() || !conversation}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  )
}