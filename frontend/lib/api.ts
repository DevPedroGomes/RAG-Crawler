/**
 * API Client for RAG Backend
 *
 * Uses Clerk JWT for authentication via Authorization header.
 * CSRF tokens no longer needed with stateless JWT auth.
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

class ApiClient {
  private getToken: (() => Promise<string | null>) | null = null

  setTokenGetter(getter: () => Promise<string | null>) {
    this.getToken = getter
  }

  private async getHeaders(): Promise<HeadersInit> {
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    }

    if (this.getToken) {
      const token = await this.getToken()
      if (token) {
        headers["Authorization"] = `Bearer ${token}`
      }
    }

    return headers
  }

  private async getBearerHeader(): Promise<HeadersInit> {
    const headers: HeadersInit = {}
    if (this.getToken) {
      const token = await this.getToken()
      if (token) {
        headers["Authorization"] = `Bearer ${token}`
      }
    }
    return headers
  }

  private async fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
    const headers = await this.getHeaders()

    const response = await fetch(url, {
      ...options,
      headers: { ...headers, ...options.headers },
    })

    if (!response.ok) {
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

    const headers = await this.getBearerHeader()

    const response = await fetch(`${API_BASE_URL}/ingest/upload`, {
      method: "POST",
      headers,
      body: formData,
    })

    if (!response.ok && response.status !== 202) {
      const error = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }))
      throw new Error(error.detail || `Request failed: ${response.status}`)
    }

    return response.json()
  }

  async crawlUrl(url: string): Promise<JobResponse> {
    const formData = new FormData()
    formData.append("url", url)

    const headers = await this.getBearerHeader()

    const response = await fetch(`${API_BASE_URL}/ingest/crawl`, {
      method: "POST",
      headers,
      body: formData,
    })

    if (!response.ok && response.status !== 202) {
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
   * Ask a question via streaming SSE (token-by-token response)
   */
  async askStream(
    question: string,
    chatHistory: ChatHistoryMessage[] = [],
    callbacks: StreamCallbacks,
    signal?: AbortSignal,
  ): Promise<void> {
    const headers = await this.getHeaders()

    const response = await fetch(`${API_BASE_URL}/chat/ask/stream`, {
      method: "POST",
      headers,
      body: JSON.stringify({ question, chat_history: chatHistory }),
      signal,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }))
      callbacks.onError(error.detail || `Request failed: ${response.status}`)
      return
    }

    const reader = response.body?.getReader()
    if (!reader) {
      callbacks.onError("Streaming not supported")
      return
    }

    const decoder = new TextDecoder()
    let buffer = ""
    let eventType = ""

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split("\n")
      buffer = lines.pop() || ""

      for (const line of lines) {
        if (line.startsWith("event: ")) {
          eventType = line.slice(7).trim()
        } else if (line.startsWith("data: ") && eventType) {
          try {
            const data = JSON.parse(line.slice(6))
            switch (eventType) {
              case "sources":
                callbacks.onSources(data)
                break
              case "token":
                callbacks.onToken(data.text)
                break
              case "done":
                callbacks.onDone()
                break
              case "error":
                callbacks.onError(data.message)
                break
            }
          } catch {
            // skip malformed data
          }
          eventType = ""
        }
      }
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
