"use client"

import type React from "react"

import { useState, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { api } from "@/lib/api"
import { Upload, Link2, Loader2, CheckCircle2 } from "lucide-react"

export function UploadSection() {
  const [fileLoading, setFileLoading] = useState(false)
  const [urlLoading, setUrlLoading] = useState(false)
  const [url, setUrl] = useState("")
  const [fileSuccess, setFileSuccess] = useState("")
  const [urlSuccess, setUrlSuccess] = useState("")
  const [error, setError] = useState("")
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setError("")
    setFileSuccess("")
    setFileLoading(true)

    try {
      await api.uploadFile(file)
      setFileSuccess(`${file.name} uploaded successfully`)
      if (fileInputRef.current) {
        fileInputRef.current.value = ""
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed")
    } finally {
      setFileLoading(false)
    }
  }

  const handleUrlSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url.trim()) return

    setError("")
    setUrlSuccess("")
    setUrlLoading(true)

    try {
      await api.crawlUrl(url)
      setUrlSuccess("URL indexed successfully")
      setUrl("")
    } catch (err) {
      setError(err instanceof Error ? err.message : "URL indexing failed")
    } finally {
      setUrlLoading(false)
    }
  }

  return (
    <div className="grid gap-6 md:grid-cols-2">
      <Card className="border-border/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5 text-primary" />
            Upload Documents
          </CardTitle>
          <CardDescription>Upload PDF or TXT files to your knowledge base</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="file-upload">Select file</Label>
            <Input
              id="file-upload"
              ref={fileInputRef}
              type="file"
              accept=".pdf,.txt"
              onChange={handleFileUpload}
              disabled={fileLoading}
              className="cursor-pointer bg-background file:mr-4 file:rounded-md file:border-0 file:bg-primary file:px-4 file:py-2 file:text-sm file:font-medium file:text-primary-foreground hover:file:bg-primary/90"
            />
          </div>
          {fileLoading && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Uploading and indexing...
            </div>
          )}
          {fileSuccess && (
            <div className="flex items-center gap-2 text-sm text-accent">
              <CheckCircle2 className="h-4 w-4" />
              {fileSuccess}
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
            <div className="space-y-2">
              <Label htmlFor="url-input">Website URL</Label>
              <Input
                id="url-input"
                type="url"
                placeholder="https://example.com"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                disabled={urlLoading}
                className="bg-background"
              />
            </div>
            <Button type="submit" disabled={urlLoading || !url.trim()} className="w-full">
              {urlLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Indexing...
                </>
              ) : (
                "Index URL"
              )}
            </Button>
            {urlSuccess && (
              <div className="flex items-center gap-2 text-sm text-accent">
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
