import { auth } from "@/lib/auth-server"
import { headers } from "next/headers"
import { redirect } from "next/navigation"
import { DashboardContent } from "@/components/dashboard-content"
import { UserMenu } from "@/components/user-menu"

export default async function DashboardPage() {
  const session = await auth.api.getSession({ headers: await headers() })

  if (!session?.user) {
    redirect("/sign-in")
  }

  return (
    <div className="min-h-screen bg-white">
      <header className="sticky top-0 z-50 border-b border-neutral-200 bg-white/80 backdrop-blur-xl">
        <div className="max-w-5xl mx-auto flex h-14 items-center justify-between px-6 sm:px-8">
          <div className="flex items-center gap-2.5">
            <img src="/logo.png" alt="Logo" className="h-8 w-8 rounded-lg object-cover" />
            <span className="font-semibold tracking-tight text-neutral-900">RAG Assistant</span>
          </div>
          <UserMenu name={session.user.name} email={session.user.email} />
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 sm:px-8 py-8">
        <DashboardContent />
      </main>
    </div>
  )
}
