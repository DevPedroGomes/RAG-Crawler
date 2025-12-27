import { getCSRFToken } from "./utils"

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
  /**
   * Get headers for API requests
   * Includes CSRF token for mutating requests
   */
  private getHeaders(includeCSRF: boolean = true): HeadersInit {
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    }

    // Add CSRF token for POST, PUT, PATCH, DELETE requests
    if (includeCSRF) {
      const csrfToken = getCSRFToken()
      if (csrfToken) {
        headers["X-CSRF-Token"] = csrfToken
      }
    }

    return headers
  }

  /**
   * Make a fetch request with credentials and error handling
   */
  private async fetchWithCredentials(
    url: string,
    options: RequestInit = {}
  ): Promise<Response> {
    const response = await fetch(url, {
      ...options,
      credentials: "include", // CRITICAL: Send cookies
    })

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        detail: `HTTP error ${response.status}`,
      }))
      throw new Error(error.detail || `Request failed: ${response.status}`)
    }

    return response
  }

  /**
   * Sign up a new user
   * Backend sets HttpOnly cookies on success
   */
  async signup(email: string, password: string): Promise<AuthResponse> {
    const response = await this.fetchWithCredentials(`${API_BASE_URL}/auth/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    })

    return response.json()
  }

  /**
   * Log in an existing user
   * Backend sets HttpOnly cookies on success
   */
  async login(email: string, password: string): Promise<AuthResponse> {
    const response = await this.fetchWithCredentials(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    })

    return response.json()
  }

  /**
   * Upload a file for background indexing
   * Returns immediately with job_id. Use getJobStatus to poll for completion.
   * Requires authentication (cookies sent automatically)
   */
  async uploadFile(file: File): Promise<JobResponse> {
    const formData = new FormData()
    formData.append("file", file)

    // For FormData, don't set Content-Type (browser sets it with boundary)
    const csrfToken = getCSRFToken()
    const headers: HeadersInit = {}
    if (csrfToken) {
      headers["X-CSRF-Token"] = csrfToken
    }

    const response = await fetch(`${API_BASE_URL}/ingest/upload`, {
      method: "POST",
      headers,
      body: formData,
      credentials: "include",
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
   * Requires authentication (cookies sent automatically)
   */
  async crawlUrl(url: string): Promise<JobResponse> {
    const formData = new FormData()
    formData.append("url", url)

    const csrfToken = getCSRFToken()
    const headers: HeadersInit = {}
    if (csrfToken) {
      headers["X-CSRF-Token"] = csrfToken
    }

    const response = await fetch(`${API_BASE_URL}/ingest/crawl`, {
      method: "POST",
      headers,
      body: formData,
      credentials: "include",
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
   * Requires authentication (cookies sent automatically)
   */
  async getJobStatus(jobId: string): Promise<JobStatusResponse> {
    const response = await this.fetchWithCredentials(`${API_BASE_URL}/jobs/${jobId}`, {
      method: "GET",
      headers: this.getHeaders(false),
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
   * Ask a question to the RAG system
   * Requires authentication (cookies sent automatically)
   */
  async ask(question: string): Promise<ChatResponse> {
    const response = await this.fetchWithCredentials(`${API_BASE_URL}/chat/ask`, {
      method: "POST",
      headers: this.getHeaders(true),
      body: JSON.stringify({ question }),
    })

    return response.json()
  }

  /**
   * Reset the knowledge base (delete all indexed documents)
   * Requires authentication (cookies sent automatically)
   */
  async reset(): Promise<{ ok: boolean; message: string }> {
    const response = await this.fetchWithCredentials(`${API_BASE_URL}/chat/reset`, {
      method: "POST",
      headers: this.getHeaders(true),
      body: JSON.stringify({}),
    })

    return response.json()
  }

  /**
   * Log out the user
   * Backend clears cookies and deletes Pinecone namespace
   */
  async logout(): Promise<{ ok: boolean; message: string }> {
    const response = await this.fetchWithCredentials(`${API_BASE_URL}/admin/logout`, {
      method: "POST",
      headers: this.getHeaders(true),
      body: JSON.stringify({}),
    })

    return response.json()
  }
}

export const api = new ApiClient()
