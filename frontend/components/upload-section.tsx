"use client"

import type React from "react"

import { useState, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { api, type ProgressStep } from "@/lib/api"
import { Upload, Link2, Loader2, CheckCircle2, Clock, XCircle, FileText, Cpu, Scissors, Database, Search } from "lucide-react"
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
  progress?: ProgressStep[]
}

const STEP_ICONS: Record<string, typeof Cpu> = {
  extracting: FileText,
  extracted: FileText,
  crawling: Search,
  chunking: Scissors,
  embedding: Cpu,
  stored: Database,
  completed: CheckCircle2,
}

function PipelineSteps({ steps }: { steps: ProgressStep[] }) {
  if (!steps || steps.length === 0) return null

  return (
    <div className="mt-2 space-y-1 border-l-2 border-primary/30 pl-3">
      {steps.map((step, i) => {
        const Icon = STEP_ICONS[step.step] || Loader2
        const isLast = i === steps.length - 1
        return (
          <div key={i} className="flex items-center gap-2 text-xs">
            <Icon className={cn(
              "h-3 w-3 flex-shrink-0",
              isLast ? "text-primary animate-pulse" : "text-green-500"
            )} />
            <span className={cn(
              "font-mono",
              isLast ? "text-foreground" : "text-muted-foreground"
            )}>
              {step.detail}
            </span>
          </div>
        )
      })}
    </div>
  )
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
  const [urlProgress, setUrlProgress] = useState<ProgressStep[]>([])
  const [error, setError] = useState("")
  const fileInputRef = useRef<HTMLInputElement>(null)

  const updateFileStatus = (id: string, updates: Partial<FileUploadStatus>) => {
    setFileStatuses(prev => prev.map(f => f.id === id ? { ...f, ...updates } : f))
  }

  const MAX_FILE_SIZE = 5 * 1024 * 1024 // 5MB

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    const oversized = Array.from(files).filter(f => f.size > MAX_FILE_SIZE)
    if (oversized.length > 0) {
      setError(`File${oversized.length > 1 ? "s" : ""} too large (max 5MB): ${oversized.map(f => f.name).join(", ")}`)
      if (fileInputRef.current) fileInputRef.current.value = ""
      return
    }

    setError("")
    setIsUploading(true)

    const initialStatuses: FileUploadStatus[] = Array.from(files).map(file => ({
      id: crypto.randomUUID(),
      name: file.name,
      status: "uploading",
      progress: [],
    }))
    setFileStatuses(initialStatuses)

    const uploadPromises = Array.from(files).map(async (file, index) => {
      const fileId = initialStatuses[index].id

      try {
        const jobResponse = await api.uploadFile(file)
        updateFileStatus(fileId, { status: "processing" })

        const result = await api.waitForJob(jobResponse.job_id, 2000, 150, (steps) => {
          updateFileStatus(fileId, { progress: steps })
        })

        if (result.status === "finished" && result.result?.status === "completed") {
          updateFileStatus(fileId, {
            status: "completed",
            message: result.result.message || "Indexed successfully",
            progress: result.progress,
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
    setUrlProgress([])
    setUrlLoading(true)

    try {
      const jobResponse = await api.crawlUrl(url)
      setUrlLoading(false)
      setUrlProcessing(true)

      const result = await api.waitForJob(jobResponse.job_id, 2000, 150, (steps) => {
        setUrlProgress(steps)
      })

      if (result.status === "finished" && result.result?.status === "completed") {
        setUrlSuccess(result.result.message || "URL indexed successfully")
        setUrlProgress(result.progress || [])
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

          {fileStatuses.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Pipeline Progress</span>
                {hasCompletedUploads && (
                  <Button variant="ghost" size="sm" onClick={clearFileStatuses} className="h-6 text-xs">
                    Clear
                  </Button>
                )}
              </div>
              <div className="space-y-1 max-h-[300px] overflow-y-auto">
                {fileStatuses.map(file => (
                  <div
                    key={file.id}
                    className={cn(
                      "text-sm p-2 rounded-md",
                      file.status === "completed" && "bg-green-500/10",
                      file.status === "failed" && "bg-destructive/10",
                      (file.status === "uploading" || file.status === "processing") && "bg-muted"
                    )}
                  >
                    <div className="flex items-center gap-2">
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
                    {file.progress && file.progress.length > 0 && (
                      <PipelineSteps steps={file.progress} />
                    )}
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
            {(urlProcessing || urlProgress.length > 0) && (
              <PipelineSteps steps={urlProgress} />
            )}
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
