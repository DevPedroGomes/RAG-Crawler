"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { AuthForm } from "@/components/auth-form"
import { isAuthenticated } from "@/lib/auth"
import { Brain } from "lucide-react"

export default function HomePage() {
  const router = useRouter()

  useEffect(() => {
    if (isAuthenticated()) {
      router.push("/dashboard")
    }
  }, [router])

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-4">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-primary/20 via-background to-background" />

      <div className="mb-8 text-center">
        <div className="mb-4 flex justify-center">
          <div className="rounded-2xl bg-primary/10 p-4">
            <Brain className="h-12 w-12 text-primary" />
          </div>
        </div>
        <h1 className="mb-2 text-4xl font-bold tracking-tight text-balance">RAG Knowledge Assistant</h1>
        <p className="text-lg text-muted-foreground text-balance">
          Upload documents, index URLs, and chat with your AI-powered knowledge base
        </p>
      </div>

      <AuthForm />
    </main>
  )
}
