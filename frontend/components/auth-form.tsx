"use client"

import { useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import Link from "next/link"
import { signIn, signUp } from "@/lib/auth-client"
import { Loader2 } from "lucide-react"

type Mode = "sign-in" | "sign-up"

export function AuthForm({
  mode,
  googleEnabled,
}: {
  mode: Mode
  googleEnabled: boolean
}) {
  const router = useRouter()
  const search = useSearchParams()
  const callbackUrl = search.get("callbackUrl") || "/dashboard"

  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      if (mode === "sign-up") {
        const { error: err } = await signUp.email({
          name: name.trim() || email.split("@")[0],
          email: email.trim(),
          password,
          callbackURL: callbackUrl,
        })
        if (err) throw new Error(err.message || "Sign-up failed")
      } else {
        const { error: err } = await signIn.email({
          email: email.trim(),
          password,
          callbackURL: callbackUrl,
        })
        if (err) throw new Error(err.message || "Sign-in failed")
      }
      router.push(callbackUrl)
      router.refresh()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Authentication failed")
    } finally {
      setLoading(false)
    }
  }

  async function handleGoogle() {
    setError(null)
    setLoading(true)
    try {
      await signIn.social({
        provider: "google",
        callbackURL: callbackUrl,
      })
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Google sign-in failed")
      setLoading(false)
    }
  }

  return (
    <div className="w-full max-w-sm space-y-4">
      {googleEnabled && (
        <>
          <button
            type="button"
            onClick={handleGoogle}
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 rounded-lg border border-neutral-200 bg-white py-2.5 text-sm font-medium text-neutral-900 hover:bg-neutral-50 disabled:opacity-60 transition-colors"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" aria-hidden>
              <path fill="#4285F4" d="M22.5 12.25c0-.79-.07-1.55-.2-2.28H12v4.32h5.9c-.26 1.37-1.04 2.53-2.21 3.31v2.75h3.58c2.09-1.92 3.23-4.74 3.23-8.1z" />
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.65l-3.58-2.75c-.99.66-2.26 1.06-3.7 1.06-2.85 0-5.27-1.92-6.13-4.5H2.18v2.83C3.99 20.62 7.7 23 12 23z" />
              <path fill="#FBBC05" d="M5.87 14.16c-.22-.66-.35-1.36-.35-2.16s.13-1.5.35-2.16V7.01H2.18C1.43 8.51 1 10.22 1 12s.43 3.49 1.18 4.99l3.69-2.83z" />
              <path fill="#EA4335" d="M12 5.34c1.62 0 3.06.56 4.21 1.65l3.15-3.15C17.45 2.16 14.97 1 12 1 7.7 1 3.99 3.38 2.18 7.01l3.69 2.83C6.73 7.26 9.15 5.34 12 5.34z" />
            </svg>
            Continue with Google
          </button>
          <div className="flex items-center gap-3 text-xs text-neutral-400">
            <div className="h-px flex-1 bg-neutral-200" />
            or
            <div className="h-px flex-1 bg-neutral-200" />
          </div>
        </>
      )}

      <form onSubmit={handleSubmit} className="space-y-3">
        {mode === "sign-up" && (
          <div>
            <label htmlFor="name" className="block text-xs font-medium text-neutral-600 mb-1">
              Name
            </label>
            <input
              id="name"
              type="text"
              autoComplete="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
              placeholder="Jane Doe"
            />
          </div>
        )}
        <div>
          <label htmlFor="email" className="block text-xs font-medium text-neutral-600 mb-1">
            Email
          </label>
          <input
            id="email"
            type="email"
            required
            autoComplete={mode === "sign-up" ? "email" : "username"}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
            placeholder="you@example.com"
          />
        </div>
        <div>
          <label htmlFor="password" className="block text-xs font-medium text-neutral-600 mb-1">
            Password
          </label>
          <input
            id="password"
            type="password"
            required
            minLength={8}
            autoComplete={mode === "sign-up" ? "new-password" : "current-password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
            placeholder="At least 8 characters"
          />
        </div>

        {error && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-60 transition-colors"
        >
          {loading && <Loader2 className="h-4 w-4 animate-spin" />}
          {mode === "sign-up" ? "Create account" : "Sign in"}
        </button>
      </form>

      <p className="text-center text-xs text-neutral-500">
        {mode === "sign-up" ? (
          <>
            Already have an account?{" "}
            <Link href="/sign-in" className="font-medium text-neutral-900 hover:underline">
              Sign in
            </Link>
          </>
        ) : (
          <>
            Don&apos;t have an account?{" "}
            <Link href="/sign-up" className="font-medium text-neutral-900 hover:underline">
              Sign up
            </Link>
          </>
        )}
      </p>
    </div>
  )
}
