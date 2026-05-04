"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { signOut } from "@/lib/auth-client"
import { LogOut, User as UserIcon } from "lucide-react"

export function UserMenu({ name, email }: { name: string; email: string }) {
  const [open, setOpen] = useState(false)
  const router = useRouter()

  const handleSignOut = async () => {
    await signOut()
    router.push("/")
    router.refresh()
  }

  const initial = (name || email || "?").trim().charAt(0).toUpperCase()

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex h-8 w-8 items-center justify-center rounded-full bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-800 transition-colors"
        aria-label="User menu"
      >
        {initial}
      </button>

      {open && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setOpen(false)}
            aria-hidden
          />
          <div className="absolute right-0 mt-2 w-64 rounded-xl border border-neutral-200 bg-white shadow-lg z-50">
            <div className="p-3 border-b border-neutral-100">
              <div className="flex items-center gap-2 text-sm">
                <UserIcon className="h-4 w-4 text-neutral-400 shrink-0" />
                <div className="min-w-0">
                  {name && <div className="font-medium text-neutral-900 truncate">{name}</div>}
                  <div className="text-xs text-neutral-500 truncate">{email}</div>
                </div>
              </div>
            </div>
            <button
              onClick={handleSignOut}
              className="flex w-full items-center gap-2 px-3 py-2.5 text-sm text-neutral-700 hover:bg-neutral-50 rounded-b-xl transition-colors"
            >
              <LogOut className="h-4 w-4" />
              Sign out
            </button>
          </div>
        </>
      )}
    </div>
  )
}
