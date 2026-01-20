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

export interface JobStatusResponse {
  job_id: string
  status: "queued" | "started" | "finished" | "failed" | "not_found"
  result?: { status: string; message: string }
  error?: string
}

class ApiClient {
  private getToken: (() => Promise<string | null>) | null = null

  /**
   * Set the token getter function (called from React components with Clerk's useAuth)
   */
  setTokenGetter(getter: () => Promise<string | null>) {
    this.getToken = getter
  }

  /**
   * Get headers with Authorization Bearer token
   */
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

  /**
   * Get auth header only (for FormData requests)
   */
  private async getAuthHeader(): Promise<HeadersInit> {
    const headers: HeadersInit = {}

    if (this.getToken) {
      const token = await this.getToken()
      if (token) {
        headers["Authorization"] = `Bearer ${token}`
      }
    }

    return headers
  }

  /**
   * Make authenticated fetch request
   */
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

  /**
   * Upload a file for background indexing
   * Returns immediately with job_id. Use getJobStatus to poll for completion.
   */
  async uploadFile(file: File): Promise<JobResponse> {
    const formData = new FormData()
    formData.append("file", file)

    const headers = await this.getAuthHeader()

    const response = await fetch(`${API_BASE_URL}/ingest/upload`, {
      method: "POST",
      headers,
      body: formData,
    })

    // 202 Accepted is a success for async operations
    if (!response.ok && response.status !== 202) {
      const error = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }))
      throw new Error(error.detail || `Request failed: ${response.status}`)
    }

    return response.json()
  }

  /**
   * Queue URL for background crawling and indexing
   * Returns immediately with job_id. Use getJobStatus to poll for completion.
   */
  async crawlUrl(url: string): Promise<JobResponse> {
    const formData = new FormData()
    formData.append("url", url)

    const headers = await this.getAuthHeader()

    const response = await fetch(`${API_BASE_URL}/ingest/crawl`, {
      method: "POST",
      headers,
      body: formData,
    })

    // 202 Accepted is a success for async operations
    if (!response.ok && response.status !== 202) {
      const error = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }))
      throw new Error(error.detail || `Request failed: ${response.status}`)
    }

    return response.json()
  }

  /**
   * Get the status of a background job
   */
  async getJobStatus(jobId: string): Promise<JobStatusResponse> {
    const response = await this.fetchWithAuth(`${API_BASE_URL}/jobs/${jobId}`, {
      method: "GET",
    })

    return response.json()
  }

  /**
   * Poll job status until completion or failure
   * @param jobId - The job ID to poll
   * @param intervalMs - Polling interval in milliseconds (default: 2000)
   * @param maxAttempts - Maximum polling attempts (default: 60 = 2 minutes)
   */
  async waitForJob(jobId: string, intervalMs = 2000, maxAttempts = 60): Promise<JobStatusResponse> {
    for (let i = 0; i < maxAttempts; i++) {
      const status = await this.getJobStatus(jobId)

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
   * Ask a question to the RAG system with conversation history
   */
  async ask(question: string, chatHistory: ChatHistoryMessage[] = []): Promise<ChatResponse> {
    const response = await this.fetchWithAuth(`${API_BASE_URL}/chat/ask`, {
      method: "POST",
      body: JSON.stringify({ question, chat_history: chatHistory }),
    })

    return response.json()
  }

  /**
   * Check if user has indexed documents
   */
  async getDocumentCount(): Promise<DocumentCountResponse> {
    const response = await this.fetchWithAuth(`${API_BASE_URL}/chat/documents`, {
      method: "GET",
    })

    return response.json()
  }

  /**
   * Reset the knowledge base (delete all indexed documents)
   */
  async reset(): Promise<{ ok: boolean; message: string }> {
    const response = await this.fetchWithAuth(`${API_BASE_URL}/chat/reset`, {
      method: "POST",
      body: JSON.stringify({}),
    })

    return response.json()
  }

  /**
   * Clear all user data from the knowledge base
   * Note: Logout is handled by Clerk on the frontend
   */
  async clearUserData(): Promise<{ ok: boolean; message: string }> {
    const response = await this.fetchWithAuth(`${API_BASE_URL}/admin/clear-data`, {
      method: "POST",
      body: JSON.stringify({}),
    })

    return response.json()
  }
}

export const api = new ApiClient()
