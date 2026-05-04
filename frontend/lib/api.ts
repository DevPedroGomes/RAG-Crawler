/**
 * API Client for RAG Backend
 *
 * Uses Better Auth httpOnly session cookies. The browser automatically
 * sends them on every fetch when `credentials: 'include'` is set, so we
 * don't manage tokens in JS. The backend (FastAPI) reads the cookie and
 * resolves the user via SQL on the Better Auth `session` table.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export interface AuthResponse {
  ok: boolean
  message: string
}

export interface ChatSource {
  url: string
  preview: string
}

export interface ChatResponse {
  answer: string
  sources: ChatSource[]
}

export interface ChatHistoryMessage {
  role: "user" | "assistant"
  content: string
}

export interface DocumentCountResponse {
  count: number
  has_documents: boolean
  documents_used: number
  documents_limit: number
  can_upload: boolean
}

export interface ApiError {
  detail: string
}

export interface JobResponse {
  ok: boolean
  job_id: string
  status: "queued" | "started" | "finished" | "failed"
  message: string
}

export interface ProgressStep {
  step: string
  detail: string
}

export interface JobStatusResponse {
  job_id: string
  status: "queued" | "started" | "finished" | "failed" | "not_found"
  result?: { status: string; message: string; words?: number; chunks?: number; pages?: number }
  error?: string
  progress?: ProgressStep[]
}

export interface SearchComparisonResult {
  content: string
  source: string
  score: number
}

export interface SearchComparisonResponse {
  semantic: SearchComparisonResult[]
  keyword: SearchComparisonResult[]
  hybrid: SearchComparisonResult[]
  meta: { semantic_total: number; keyword_total: number; hybrid_total: number }
}

export interface EmbeddingPoint {
  x: number
  y: number
  preview: string
  source: string
}

export interface EmbeddingsResponse {
  points: EmbeddingPoint[]
  message?: string
}

export interface StreamCallbacks {
  onSources: (sources: ChatSource[]) => void
  onToken: (text: string) => void
  onDone: () => void
  onError: (message: string) => void
}

/**
 * If a request comes back 401, the Better Auth session expired or the cookie
 * was cleared. Bounce to /sign-in so the user lands somewhere actionable
 * instead of seeing a generic "Request failed: 401" toast.
 */
function redirectToSignInOn401(status: number): boolean {
  if (status !== 401) return false
  if (typeof window === "undefined") return false
  const callback = window.location.pathname + window.location.search
  window.location.href = `/sign-in?callbackUrl=${encodeURIComponent(callback)}`
  return true
}

class ApiClient {
  private async fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
    const headers: HeadersInit = {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    }

    const response = await fetch(url, {
      credentials: "include",
      ...options,
      headers,
    })

    if (!response.ok) {
      if (redirectToSignInOn401(response.status)) {
        // Throw a sentinel so callers can swallow it (we'll already be navigating away).
        throw new Error("Session expired — redirecting to sign-in")
      }
      const error = await response.json().catch(() => ({
        detail: `HTTP error ${response.status}`,
      }))
      throw new Error(error.detail || `Request failed: ${response.status}`)
    }

    return response
  }

  async uploadFile(file: File): Promise<JobResponse> {
    const formData = new FormData()
    formData.append("file", file)

    const response = await fetch(`${API_BASE_URL}/ingest/upload`, {
      method: "POST",
      credentials: "include",
      body: formData,
    })

    if (!response.ok && response.status !== 202) {
      if (redirectToSignInOn401(response.status)) {
        throw new Error("Session expired — redirecting to sign-in")
      }
      const error = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }))
      throw new Error(error.detail || `Request failed: ${response.status}`)
    }

    return response.json()
  }

  async crawlUrl(url: string): Promise<JobResponse> {
    const formData = new FormData()
    formData.append("url", url)

    const response = await fetch(`${API_BASE_URL}/ingest/crawl`, {
      method: "POST",
      credentials: "include",
      body: formData,
    })

    if (!response.ok && response.status !== 202) {
      if (redirectToSignInOn401(response.status)) {
        throw new Error("Session expired — redirecting to sign-in")
      }
      const error = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }))
      throw new Error(error.detail || `Request failed: ${response.status}`)
    }

    return response.json()
  }

  async getJobStatus(jobId: string): Promise<JobStatusResponse> {
    const response = await this.fetchWithAuth(`${API_BASE_URL}/jobs/${jobId}`, {
      method: "GET",
    })

    return response.json()
  }

  async waitForJob(
    jobId: string,
    intervalMs = 2000,
    maxAttempts = 150,
    onProgress?: (steps: ProgressStep[]) => void,
  ): Promise<JobStatusResponse> {
    for (let i = 0; i < maxAttempts; i++) {
      const status = await this.getJobStatus(jobId)

      if (onProgress && status.progress) {
        onProgress(status.progress)
      }

      if (status.status === "finished" || status.status === "failed" || status.status === "not_found") {
        return status
      }

      await new Promise(resolve => setTimeout(resolve, intervalMs))
    }

    return {
      job_id: jobId,
      status: "failed",
      error: "Timeout waiting for job completion"
    }
  }

  /**
   * Ask a question via streaming SSE (token-by-token response).
   *
   * Spec-compliant SSE parser: events are separated by `\n\n`, each event
   * may have multiple `data:` lines that get concatenated, and `:`-prefixed
   * comment lines are ignored (they're keep-alives).
   */
  async askStream(
    question: string,
    chatHistory: ChatHistoryMessage[] = [],
    callbacks: StreamCallbacks,
    signal?: AbortSignal,
  ): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/chat/ask/stream`, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
        "Cache-Control": "no-cache",
      },
      body: JSON.stringify({ question, chat_history: chatHistory }),
      signal,
    })

    if (!response.ok) {
      if (redirectToSignInOn401(response.status)) return
      const text = await response.text().catch(() => "")
      let detail = `HTTP error ${response.status}`
      try {
        const parsed = JSON.parse(text)
        detail = parsed.detail || detail
      } catch {
        if (text) detail = text.slice(0, 200)
      }
      callbacks.onError(detail)
      return
    }

    const reader = response.body?.getReader()
    if (!reader) {
      callbacks.onError("Streaming not supported")
      return
    }

    const decoder = new TextDecoder()
    let buffer = ""

    const dispatchEvent = (rawEvent: string) => {
      let eventType = "message"
      const dataLines: string[] = []
      for (const line of rawEvent.split("\n")) {
        if (!line || line.startsWith(":")) continue // keep-alive / comment
        if (line.startsWith("event:")) eventType = line.slice(6).trim()
        else if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart())
      }
      if (dataLines.length === 0) return
      const data = dataLines.join("\n")
      let parsed: unknown = data
      try { parsed = JSON.parse(data) } catch { /* string passthrough */ }
      switch (eventType) {
        case "sources":
          callbacks.onSources(parsed as ChatSource[])
          break
        case "token":
          callbacks.onToken((parsed as { text: string }).text || "")
          break
        case "done":
          callbacks.onDone()
          break
        case "error":
          callbacks.onError((parsed as { message: string }).message || String(parsed))
          break
      }
    }

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        let sep
        // Standard SSE event separator is a blank line ("\n\n").
        while ((sep = buffer.indexOf("\n\n")) !== -1) {
          const rawEvent = buffer.slice(0, sep)
          buffer = buffer.slice(sep + 2)
          if (rawEvent.length > 0) dispatchEvent(rawEvent)
        }
      }
      // Flush any trailing event without separator (shouldn't happen with backend, but safe).
      if (buffer.length > 0) dispatchEvent(buffer)
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        reader.cancel()
        throw err
      }
      callbacks.onError(err instanceof Error ? err.message : "Stream error")
    } finally {
      reader.releaseLock()
    }
  }

  /**
   * Non-streaming ask (legacy fallback)
   */
  async ask(question: string, chatHistory: ChatHistoryMessage[] = []): Promise<ChatResponse> {
    const response = await this.fetchWithAuth(`${API_BASE_URL}/chat/ask`, {
      method: "POST",
      body: JSON.stringify({ question, chat_history: chatHistory }),
    })

    return response.json()
  }

  async getDocumentCount(): Promise<DocumentCountResponse> {
    const response = await this.fetchWithAuth(`${API_BASE_URL}/chat/documents`, {
      method: "GET",
    })

    return response.json()
  }

  async reset(): Promise<{ ok: boolean; message: string }> {
    const response = await this.fetchWithAuth(`${API_BASE_URL}/chat/reset`, {
      method: "POST",
      body: JSON.stringify({}),
    })

    return response.json()
  }

  async clearUserData(): Promise<{ ok: boolean; message: string }> {
    const response = await this.fetchWithAuth(`${API_BASE_URL}/admin/clear-data`, {
      method: "POST",
      body: JSON.stringify({}),
    })

    return response.json()
  }

  /**
   * Get search comparison: semantic vs keyword vs hybrid side-by-side
   */
  async searchComparison(question: string): Promise<SearchComparisonResponse> {
    const response = await this.fetchWithAuth(`${API_BASE_URL}/analysis/search-comparison`, {
      method: "POST",
      body: JSON.stringify({ question }),
    })

    return response.json()
  }

  /**
   * Get 2D PCA projection of user's document embeddings
   */
  async getEmbeddings2D(): Promise<EmbeddingsResponse> {
    const response = await this.fetchWithAuth(`${API_BASE_URL}/analysis/embeddings-2d`, {
      method: "GET",
    })

    return response.json()
  }
}

export const api = new ApiClient()
