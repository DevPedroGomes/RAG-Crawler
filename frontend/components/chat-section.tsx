"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { api, type ChatSource } from "@/lib/api"
import { MessageSquare, Send, RotateCcw, Loader2, FileText, User, Bot, AlertCircle, Info } from "lucide-react"
import { cn } from "@/lib/utils"

interface Message {
  id: string
  role: "user" | "assistant" | "system"
  content: string
  sources?: ChatSource[]
  timestamp: Date
  isStreaming?: boolean
}

interface ChatSectionProps {
  hasDocuments: boolean
  onReset?: () => void
  systemMessage?: { id: string; content: string } | null
}

export function ChatSection({ hasDocuments, onReset, systemMessage }: ChatSectionProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [question, setQuestion] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    if (systemMessage) {
      const sysMsg: Message = {
        id: systemMessage.id,
        role: "system",
        content: systemMessage.content,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, sysMsg])
    }
  }, [systemMessage?.id])

  const handleAsk = async () => {
    if (!question.trim() || !hasDocuments) return

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: question.trim(),
      timestamp: new Date(),
    }

    const assistantId = crypto.randomUUID()
    const assistantMessage: Message = {
      id: assistantId,
      role: "assistant",
      content: "",
      sources: [],
      timestamp: new Date(),
      isStreaming: true,
    }

    setMessages((prev) => [...prev, userMessage, assistantMessage])
    const currentQuestion = question.trim()
    setQuestion("")
    setError("")
    setLoading(true)

    try {
      const chatHistory = messages
        .filter((m) => m.role === "user" || m.role === "assistant")
        .map((m) => ({
          role: m.role as "user" | "assistant",
          content: m.content,
        }))

      await api.askStream(currentQuestion, chatHistory, {
        onSources: (sources) => {
          setMessages((prev) =>
            prev.map((m) => m.id === assistantId ? { ...m, sources } : m)
          )
        },
        onToken: (text) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, content: m.content + text } : m
            )
          )
        },
        onDone: () => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, isStreaming: false } : m
            )
          )
        },
        onError: (message) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: message, isStreaming: false }
                : m
            )
          )
        },
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to get answer")
      setMessages((prev) => prev.filter((m) => m.id !== userMessage.id && m.id !== assistantId))
    } finally {
      setLoading(false)
    }
  }

  const handleReset = async () => {
    if (
      !confirm(
        "Are you sure you want to reset your knowledge base? This will delete all indexed documents and chat history."
      )
    ) {
      return
    }

    setLoading(true)
    setError("")

    try {
      await api.reset()
      setMessages([])
      setQuestion("")
      onReset?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset failed")
    } finally {
      setLoading(false)
    }
  }

  const handleClearChat = () => {
    if (messages.length === 0) return
    if (confirm("Clear chat history? (Documents will remain indexed)")) {
      setMessages([])
    }
  }

  return (
    <Card className="border-border/50 flex flex-col h-[600px]">
      <CardHeader className="flex-shrink-0">
        <CardTitle className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5 text-primary" />
          Chat with Your Knowledge Base
        </CardTitle>
        <CardDescription>Ask questions about your uploaded documents and indexed URLs</CardDescription>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col min-h-0 space-y-4">
        {!hasDocuments && (
          <div className="flex items-center gap-3 rounded-lg border border-yellow-500/50 bg-yellow-500/10 p-4">
            <AlertCircle className="h-5 w-5 text-yellow-500 flex-shrink-0" />
            <div>
              <p className="font-medium text-yellow-500">No documents indexed</p>
              <p className="text-sm text-muted-foreground">
                Upload a PDF/TXT file or index a URL above to start chatting.
              </p>
            </div>
          </div>
        )}

        <div className="flex-1 overflow-y-auto rounded-lg border border-border/50 bg-muted/20 p-4 space-y-4 min-h-[200px]">
          {messages.length === 0 ? (
            <div className="h-full flex items-center justify-center text-muted-foreground">
              <div className="text-center">
                <MessageSquare className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>{hasDocuments ? "Start a conversation..." : "Index some documents to begin"}</p>
              </div>
            </div>
          ) : (
            <>
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={cn(
                    "flex gap-3",
                    message.role === "user" ? "justify-end" : "justify-start",
                    message.role === "system" && "justify-center"
                  )}
                >
                  {message.role === "system" && (
                    <div className="flex items-center gap-2 rounded-lg border border-blue-500/30 bg-blue-500/10 px-4 py-2 max-w-[90%]">
                      <Info className="h-4 w-4 text-blue-500 flex-shrink-0" />
                      <p className="text-sm text-blue-600 dark:text-blue-400">{message.content}</p>
                    </div>
                  )}

                  {message.role === "assistant" && (
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                      <Bot className="h-4 w-4 text-primary" />
                    </div>
                  )}

                  {message.role !== "system" && (
                  <div
                    className={cn(
                      "max-w-[80%] rounded-lg p-3 space-y-2",
                      message.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-card border border-border/50"
                    )}
                  >
                    <p className="text-sm whitespace-pre-wrap">
                      {message.content}
                      {message.isStreaming && (
                        <span className="inline-block w-2 h-4 bg-primary/60 animate-pulse ml-0.5 align-middle" />
                      )}
                    </p>

                    {message.role === "assistant" && message.sources && message.sources.length > 0 && !message.isStreaming && (
                      <div className="pt-2 border-t border-border/30 space-y-2">
                        <p className="text-xs font-medium flex items-center gap-1 text-muted-foreground">
                          <FileText className="h-3 w-3" />
                          Sources ({message.sources.length})
                        </p>
                        <div className="space-y-1">
                          {message.sources.map((source, idx) => (
                            <div key={idx} className="text-xs bg-muted/50 rounded p-2">
                              <p className="text-muted-foreground line-clamp-2">{source.preview}</p>
                              <a
                                href={source.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-primary hover:underline mt-1 inline-block"
                              >
                                {source.url.length > 50 ? source.url.substring(0, 50) + "..." : source.url}
                              </a>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {!message.isStreaming && (
                    <p className="text-xs opacity-50">
                      {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </p>
                    )}
                  </div>
                  )}

                  {message.role === "user" && (
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary flex items-center justify-center">
                      <User className="h-4 w-4 text-primary-foreground" />
                    </div>
                  )}
                </div>
              ))}

              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {error && <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</div>}

        <div className="flex-shrink-0 space-y-2">
          <Textarea
            placeholder={hasDocuments ? "Ask a question about your documents..." : "Index documents first..."}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={loading || !hasDocuments}
            className="min-h-[80px] resize-none bg-background"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                handleAsk()
              }
            }}
          />

          <div className="flex gap-2">
            <Button
              onClick={handleAsk}
              disabled={loading || !question.trim() || !hasDocuments}
              className="flex-1"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Send className="mr-2 h-4 w-4" />
                  Send
                </>
              )}
            </Button>
            <Button
              onClick={handleClearChat}
              disabled={loading || messages.length === 0}
              variant="outline"
              title="Clear chat history"
            >
              Clear
            </Button>
            <Button onClick={handleReset} disabled={loading} variant="destructive" title="Delete all documents">
              <RotateCcw className="mr-2 h-4 w-4" />
              Reset
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
