"use client"

import type React from "react"

import { useState, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { api } from "@/lib/api"
import { Upload, Link2, Loader2, CheckCircle2, Clock, XCircle, FileText } from "lucide-react"
import { cn } from "@/lib/utils"

interface UploadSectionProps {
  onUploadComplete?: (documentNames?: string[]) => void
  canUpload?: boolean
  documentsUsed?: number
  documentsLimit?: number
}

interface FileUploadStatus {
  id: string
  name: string
  status: "uploading" | "processing" | "completed" | "failed"
  message?: string
}

export function UploadSection({
  onUploadComplete,
  canUpload = true,
  documentsUsed = 0,
  documentsLimit = 5
}: UploadSectionProps) {
  const [fileStatuses, setFileStatuses] = useState<FileUploadStatus[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [urlLoading, setUrlLoading] = useState(false)
  const [urlProcessing, setUrlProcessing] = useState(false)
  const [url, setUrl] = useState("")
  const [urlSuccess, setUrlSuccess] = useState("")
  const [error, setError] = useState("")
  const fileInputRef = useRef<HTMLInputElement>(null)

  const updateFileStatus = (id: string, updates: Partial<FileUploadStatus>) => {
    setFileStatuses(prev => prev.map(f => f.id === id ? { ...f, ...updates } : f))
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    setError("")
    setIsUploading(true)

    // Initialize status for all files
    const initialStatuses: FileUploadStatus[] = Array.from(files).map(file => ({
      id: crypto.randomUUID(),
      name: file.name,
      status: "uploading"
    }))
    setFileStatuses(initialStatuses)

    // Process files in parallel
    const uploadPromises = Array.from(files).map(async (file, index) => {
      const fileId = initialStatuses[index].id

      try {
        // Upload file
        const jobResponse = await api.uploadFile(file)
        updateFileStatus(fileId, { status: "processing" })

        // Wait for processing
        const result = await api.waitForJob(jobResponse.job_id)

        if (result.status === "finished" && result.result?.status === "completed") {
          updateFileStatus(fileId, {
            status: "completed",
            message: result.result.message || "Indexed successfully"
          })
          return true
        } else {
          updateFileStatus(fileId, {
            status: "failed",
            message: result.error || result.result?.message || "Processing failed"
          })
          return false
        }
      } catch (err) {
        updateFileStatus(fileId, {
          status: "failed",
          message: err instanceof Error ? err.message : "Upload failed"
        })
        return false
      }
    })

    try {
      const results = await Promise.all(uploadPromises)
      const successfulFileNames = initialStatuses
        .filter((_, index) => results[index])
        .map(f => f.name)

      if (successfulFileNames.length > 0) {
        onUploadComplete?.(successfulFileNames)
      }
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ""
      }
    }
  }

  const handleUrlSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url.trim()) return

    setError("")
    setUrlSuccess("")
    setUrlLoading(true)

    try {
      // Queue URL for processing
      const jobResponse = await api.crawlUrl(url)
      setUrlLoading(false)
      setUrlProcessing(true)

      // Poll for job completion
      const result = await api.waitForJob(jobResponse.job_id)

      if (result.status === "finished" && result.result?.status === "completed") {
        setUrlSuccess(result.result.message || "URL indexed successfully")
        const indexedUrl = url
        setUrl("")
        onUploadComplete?.([indexedUrl])
      } else {
        setError(result.error || result.result?.message || "Indexing failed")
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "URL indexing failed")
    } finally {
      setUrlLoading(false)
      setUrlProcessing(false)
    }
  }

  const clearFileStatuses = () => {
    setFileStatuses([])
  }

  const hasActiveUploads = fileStatuses.some(f => f.status === "uploading" || f.status === "processing")
  const hasCompletedUploads = fileStatuses.length > 0 && !hasActiveUploads

  return (
    <div className="grid gap-6 md:grid-cols-2">
      <Card className="border-border/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5 text-primary" />
            Upload Documents
          </CardTitle>
          <CardDescription>Upload multiple PDF or TXT files to your knowledge base</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Document limit indicator */}
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Documents used:</span>
            <span className={cn(
              "font-medium",
              !canUpload ? "text-amber-500" : "text-foreground"
            )}>
              {documentsUsed} / {documentsLimit}
            </span>
          </div>

          {!canUpload && (
            <div className="rounded-md bg-amber-500/10 border border-amber-500/50 p-3 text-sm text-amber-500">
              Document limit reached. Reset your knowledge base to upload new documents.
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="file-upload">Select files</Label>
            <Input
              id="file-upload"
              ref={fileInputRef}
              type="file"
              accept=".pdf,.txt"
              multiple
              onChange={handleFileUpload}
              disabled={isUploading || !canUpload}
              className="cursor-pointer bg-background file:mr-4 file:rounded-md file:border-0 file:bg-primary file:px-4 file:py-2 file:text-sm file:font-medium file:text-primary-foreground hover:file:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <p className="text-xs text-muted-foreground">Max 5MB per file. You can select multiple files.</p>
          </div>

          {/* File upload statuses */}
          {fileStatuses.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Upload Progress</span>
                {hasCompletedUploads && (
                  <Button variant="ghost" size="sm" onClick={clearFileStatuses} className="h-6 text-xs">
                    Clear
                  </Button>
                )}
              </div>
              <div className="space-y-1 max-h-[200px] overflow-y-auto">
                {fileStatuses.map(file => (
                  <div
                    key={file.id}
                    className={cn(
                      "flex items-center gap-2 text-sm p-2 rounded-md",
                      file.status === "completed" && "bg-green-500/10",
                      file.status === "failed" && "bg-destructive/10",
                      (file.status === "uploading" || file.status === "processing") && "bg-muted"
                    )}
                  >
                    {file.status === "uploading" && <Loader2 className="h-4 w-4 animate-spin text-primary" />}
                    {file.status === "processing" && <Clock className="h-4 w-4 animate-pulse text-primary" />}
                    {file.status === "completed" && <CheckCircle2 className="h-4 w-4 text-green-500" />}
                    {file.status === "failed" && <XCircle className="h-4 w-4 text-destructive" />}
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    <span className="flex-1 truncate">{file.name}</span>
                    <span className="text-xs text-muted-foreground">
                      {file.status === "uploading" && "Uploading..."}
                      {file.status === "processing" && "Processing..."}
                      {file.status === "completed" && "Done"}
                      {file.status === "failed" && "Failed"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="border-border/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Link2 className="h-5 w-5 text-primary" />
            Index URL
          </CardTitle>
          <CardDescription>Crawl and index content from any webpage</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleUrlSubmit} className="space-y-4">
            {!canUpload && (
              <div className="rounded-md bg-amber-500/10 border border-amber-500/50 p-3 text-sm text-amber-500">
                Document limit reached. Reset your knowledge base to index new URLs.
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="url-input">Website URL</Label>
              <Input
                id="url-input"
                type="url"
                placeholder="https://example.com"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                disabled={urlLoading || urlProcessing || !canUpload}
                className="bg-background"
              />
            </div>
            <Button type="submit" disabled={urlLoading || urlProcessing || !url.trim() || !canUpload} className="w-full">
              {urlLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Queueing...
                </>
              ) : urlProcessing ? (
                <>
                  <Clock className="mr-2 h-4 w-4 animate-pulse" />
                  Processing...
                </>
              ) : (
                "Index URL"
              )}
            </Button>
            {urlSuccess && (
              <div className="flex items-center gap-2 text-sm text-green-500">
                <CheckCircle2 className="h-4 w-4" />
                {urlSuccess}
              </div>
            )}
          </form>
        </CardContent>
      </Card>

      {error && (
        <Card className="border-destructive/50 bg-destructive/10 md:col-span-2">
          <CardContent className="pt-6">
            <p className="text-sm text-destructive">{error}</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
