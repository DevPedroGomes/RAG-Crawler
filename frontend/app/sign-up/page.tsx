import { Brain } from "lucide-react"
import { Suspense } from "react"
import { AuthForm } from "@/components/auth-form"

export default function SignUpPage() {
  // Botão Google sempre visível.
  const googleEnabled = true

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-4 bg-neutral-50">
      <div className="mb-8 text-center">
        <div className="mb-4 flex justify-center">
          <div className="rounded-2xl bg-neutral-900/5 p-4">
            <Brain className="h-12 w-12 text-neutral-900" />
          </div>
        </div>
        <h1 className="mb-2 text-3xl font-semibold tracking-tight text-neutral-900">
          Create your account
        </h1>
        <p className="text-sm text-neutral-500">
          Start chatting with your documents in seconds
        </p>
      </div>

      <div className="w-full max-w-sm rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm">
        <Suspense fallback={<div className="text-center text-sm text-neutral-400">Loading…</div>}>
          <AuthForm mode="sign-up" googleEnabled={googleEnabled} />
        </Suspense>
      </div>
    </main>
  )
}
