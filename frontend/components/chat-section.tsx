"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { api, type ChatResponse } from "@/lib/api"
import { MessageSquare, Send, RotateCcw, Loader2, FileText } from "lucide-react"

export function ChatSection() {
  const [question, setQuestion] = useState("")
  const [response, setResponse] = useState<ChatResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  const handleAsk = async () => {
    if (!question.trim()) return

    setError("")
    setLoading(true)

    try {
      const result = await api.ask(question)
      setResponse(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to get answer")
    } finally {
      setLoading(false)
    }
  }

  const handleReset = async () => {
    if (!confirm("Are you sure you want to reset your knowledge base? This will delete all indexed documents.")) {
      return
    }

    setLoading(true)
    setError("")

    try {
      await api.reset()
      setResponse(null)
      setQuestion("")
      alert("Knowledge base reset successfully")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset failed")
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="border-border/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5 text-primary" />
          Chat with Your Knowledge Base
        </CardTitle>
        <CardDescription>Ask questions about your uploaded documents and indexed URLs</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Textarea
            placeholder="Ask a question about your documents..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={loading}
            className="min-h-[100px] resize-none bg-background"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                handleAsk()
              }
            }}
          />
        </div>

        <div className="flex gap-2">
          <Button onClick={handleAsk} disabled={loading || !question.trim()} className="flex-1">
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Thinking...
              </>
            ) : (
              <>
                <Send className="mr-2 h-4 w-4" />
                Ask
              </>
            )}
          </Button>
          <Button onClick={handleReset} disabled={loading} variant="outline">
            <RotateCcw className="mr-2 h-4 w-4" />
            Reset
          </Button>
        </div>

        {error && <div className="rounded-md bg-destructive/10 p-4 text-sm text-destructive">{error}</div>}

        {response && (
          <div className="space-y-4 rounded-lg border border-border/50 bg-muted/30 p-4">
            <div className="space-y-2">
              <h3 className="font-semibold text-foreground">Answer</h3>
              <p className="text-pretty leading-relaxed text-foreground">{response.answer}</p>
            </div>

            {response.sources && response.sources.length > 0 && (
              <div className="space-y-2 border-t border-border/50 pt-4">
                <h3 className="flex items-center gap-2 font-semibold text-foreground">
                  <FileText className="h-4 w-4" />
                  Sources ({response.sources.length})
                </h3>
                <div className="space-y-2">
                  {response.sources.map((source, idx) => (
                    <div key={idx} className="rounded-md border border-border/30 bg-card/50 p-3 text-sm space-y-2">
                      <p className="text-pretty leading-relaxed text-card-foreground">{source.preview}</p>
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center text-xs text-primary hover:underline"
                      >
                        {source.url}
                      </a>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
