"use client"

import { useEffect, useState, useCallback } from "react"
import { useAuth } from "@clerk/nextjs"
import { UploadSection } from "@/components/upload-section"
import { ChatSection } from "@/components/chat-section"
import { api, type DocumentCountResponse } from "@/lib/api"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Clock } from "lucide-react"

export function DashboardContent() {
  const { getToken } = useAuth()
  const [documentInfo, setDocumentInfo] = useState<DocumentCountResponse | null>(null)
  const [isCheckingDocuments, setIsCheckingDocuments] = useState(true)
  const [systemMessage, setSystemMessage] = useState<{ id: string; content: string } | null>(null)

  // Set up API client with Clerk token getter
  useEffect(() => {
    api.setTokenGetter(getToken)
  }, [getToken])

  // Check if user has documents
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

  // Initial check for documents
  useEffect(() => {
    // Small delay to ensure token getter is set
    const timer = setTimeout(() => {
      checkDocuments()
    }, 100)
    return () => clearTimeout(timer)
  }, [checkDocuments])

  const hasDocuments = documentInfo?.has_documents ?? false
  const canUpload = documentInfo?.can_upload ?? true
  const documentsUsed = documentInfo?.documents_used ?? 0
  const documentsLimit = documentInfo?.documents_limit ?? 5

  return (
    <>
      {/* Showcase mode warning */}
      <Alert className="mb-6 border-amber-500/50 bg-amber-500/10">
        <Clock className="h-4 w-4 text-amber-500" />
        <AlertTitle className="text-amber-500">Showcase Mode</AlertTitle>
        <AlertDescription className="text-muted-foreground">
          This is a demo application. Your documents will be automatically deleted after 10 minutes of inactivity.
          Maximum {documentsLimit} documents, 5MB each.
        </AlertDescription>
      </Alert>

      <UploadSection
        onUploadComplete={(documentNames?: string[]) => {
          checkDocuments()
          if (documentNames && documentNames.length > 0) {
            const names = documentNames.join(", ")
            setSystemMessage({
              id: crypto.randomUUID(),
              content: `New document${documentNames.length > 1 ? "s" : ""} added: ${names}`
            })
          }
        }}
        canUpload={canUpload}
        documentsUsed={documentsUsed}
        documentsLimit={documentsLimit}
      />
      <ChatSection
        hasDocuments={hasDocuments && !isCheckingDocuments}
        onReset={checkDocuments}
        systemMessage={systemMessage}
      />
    </>
  )
}
