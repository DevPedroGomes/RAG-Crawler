"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { UploadSection } from "@/components/upload-section"
import { ChatSection } from "@/components/chat-section"
import { isAuthenticated, clearToken } from "@/lib/auth"
import { api } from "@/lib/api"
import { Brain, LogOut } from "lucide-react"

export default function DashboardPage() {
  const router = useRouter()

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/")
    }
  }, [router])

  const handleLogout = async () => {
    try {
      await api.logout()
    } catch (err) {
      console.error("Logout error:", err)
    } finally {
      clearToken()
      router.push("/")
    }
  }

  if (!isAuthenticated()) {
    return null
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-10 border-b border-border/50 bg-card/80 backdrop-blur-sm">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-primary/10 p-2">
              <Brain className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">RAG Assistant</h1>
              <p className="text-xs text-muted-foreground">AI Knowledge Base</p>
            </div>
          </div>
          <Button onClick={handleLogout} variant="outline" size="sm">
            <LogOut className="mr-2 h-4 w-4" />
            Sign out
          </Button>
        </div>
      </header>

      <main className="container mx-auto space-y-8 p-4 py-8">
        <div className="space-y-2">
          <h2 className="text-3xl font-bold tracking-tight text-balance">Your Knowledge Base</h2>
          <p className="text-muted-foreground text-balance">
            Upload documents or index URLs to build your AI-powered knowledge assistant
          </p>
        </div>

        <UploadSection />
        <ChatSection />
      </main>
    </div>
  )
}
