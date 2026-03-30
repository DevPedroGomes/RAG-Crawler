"use client"

import { useEffect, useState, useCallback } from "react"
import { useAuth } from "@clerk/nextjs"
import { UploadSection } from "@/components/upload-section"
import { ChatSection } from "@/components/chat-section"
import { AnalysisPanel } from "@/components/analysis-panel"
import { api, type DocumentCountResponse } from "@/lib/api"
import { Upload, MessageSquare, BarChart3, Plus, X, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

export function DashboardContent() {
  const { getToken } = useAuth()
  const [documentInfo, setDocumentInfo] = useState<DocumentCountResponse | null>(null)
  const [isCheckingDocuments, setIsCheckingDocuments] = useState(true)
  const [systemMessage, setSystemMessage] = useState<{ id: string; content: string } | null>(null)
  const [activeTab, setActiveTab] = useState<"chat" | "analyze">("chat")
  const [showUpload, setShowUpload] = useState(false)

  useEffect(() => {
    api.setTokenGetter(getToken)
  }, [getToken])

  const checkDocuments = useCallback(async () => {
    try {
      setIsCheckingDocuments(true)
      const response = await api.getDocumentCount()
      setDocumentInfo(response)
    } catch (error) {
      console.error("Failed to check document count:", error)
      setDocumentInfo(null)
    } finally {
      setIsCheckingDocuments(false)
    }
  }, [])

  useEffect(() => {
    const timer = setTimeout(() => {
      checkDocuments()
    }, 100)
    return () => clearTimeout(timer)
  }, [checkDocuments])

  const hasDocuments = documentInfo?.has_documents ?? false
  const canUpload = documentInfo?.can_upload ?? true
  const documentsUsed = documentInfo?.documents_used ?? 0
  const documentsLimit = documentInfo?.documents_limit ?? 5

  const handleUploadComplete = useCallback((documentNames?: string[]) => {
    checkDocuments()
    if (documentNames && documentNames.length > 0) {
      const names = documentNames.join(", ")
      setSystemMessage({
        id: crypto.randomUUID(),
        content: `New document${documentNames.length > 1 ? "s" : ""} added: ${names}`
      })
    }
  }, [checkDocuments])

  // Loading state
  if (isCheckingDocuments && !documentInfo) {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-neutral-300 mb-4" />
        <p className="text-sm text-neutral-400">Loading your knowledge base...</p>
      </div>
    )
  }

  // ─── Phase 1: Upload (no documents yet) ───
  if (!hasDocuments) {
    return (
      <div className="py-8">
        <div className="text-center mb-12 animate-fade-in-up">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-neutral-100 mb-5">
            <Upload className="h-8 w-8 text-neutral-900" />
          </div>
          <h2 className="text-3xl font-semibold tracking-tight text-neutral-900">
            Add Your First Document
          </h2>
          <p className="text-neutral-500 mt-3 max-w-lg mx-auto leading-relaxed">
            Upload PDF or TXT files, or paste a URL to start building your AI knowledge base.
            Once indexed, you can ask questions answered exclusively from your content.
          </p>
          <p className="text-xs text-neutral-400 mt-3 font-mono">
            Showcase mode — auto-deleted after 10 min inactivity · max {documentsLimit} docs · 5MB each
          </p>
        </div>

        <div className="animate-fade-in-up-delay-1">
          <UploadSection
            onUploadComplete={(documentNames) => {
              handleUploadComplete(documentNames)
              setShowUpload(false)
            }}
            canUpload={canUpload}
            documentsUsed={documentsUsed}
            documentsLimit={documentsLimit}
          />
        </div>
      </div>
    )
  }

  // ─── Phase 2: Active (has documents) ───
  return (
    <div className="animate-fade-in-up">
      {/* Navigation bar */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-1 bg-neutral-100 rounded-lg p-1">
          <button
            onClick={() => setActiveTab("chat")}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all duration-200",
              activeTab === "chat"
                ? "bg-white text-neutral-900 shadow-sm"
                : "text-neutral-500 hover:text-neutral-700"
            )}
          >
            <MessageSquare className="h-4 w-4" />
            Chat
          </button>
          <button
            onClick={() => setActiveTab("analyze")}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all duration-200",
              activeTab === "analyze"
                ? "bg-white text-neutral-900 shadow-sm"
                : "text-neutral-500 hover:text-neutral-700"
            )}
          >
            <BarChart3 className="h-4 w-4" />
            Analyze
          </button>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs text-neutral-400 font-mono hidden sm:inline">
            {documentsUsed}/{documentsLimit} docs · showcase mode
          </span>
          <button
            onClick={() => setShowUpload(!showUpload)}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium border transition-all duration-200",
              showUpload
                ? "bg-neutral-900 text-white border-neutral-900"
                : "text-neutral-600 border-neutral-200 hover:bg-neutral-50"
            )}
          >
            {showUpload ? <X className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
            <span className="hidden sm:inline">{showUpload ? "Close" : "Add Documents"}</span>
          </button>
        </div>
      </div>

      {/* Collapsible upload panel */}
      {showUpload && (
        <div className="animate-fade-in-up mb-6 rounded-2xl border border-neutral-200 bg-neutral-50 p-6">
          <UploadSection
            onUploadComplete={(documentNames) => {
              handleUploadComplete(documentNames)
              setShowUpload(false)
            }}
            canUpload={canUpload}
            documentsUsed={documentsUsed}
            documentsLimit={documentsLimit}
          />
        </div>
      )}

      {/* Tab content: both mounted, shown/hidden to preserve state */}
      <div className={activeTab === "chat" ? "" : "hidden"}>
        <ChatSection
          hasDocuments={hasDocuments && !isCheckingDocuments}
          onReset={() => {
            checkDocuments()
            setShowUpload(false)
          }}
          systemMessage={systemMessage}
        />
      </div>
      <div className={activeTab === "analyze" ? "" : "hidden"}>
        <AnalysisPanel hasDocuments={hasDocuments && !isCheckingDocuments} />
      </div>
    </div>
  )
}
