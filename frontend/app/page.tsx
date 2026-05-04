import { auth } from "@/lib/auth-server"
import { headers } from "next/headers"
import { redirect } from "next/navigation"
import {
  Brain, FileText, Search, Cpu, Database, MessageSquare,
  Scissors, ArrowRight, Sparkles, Type, Combine, Shield,
  Zap, Globe, BarChart3
} from "lucide-react"
import Link from "next/link"

function PipelineStep({
  icon: Icon,
  title,
  description,
  detail,
  color,
}: {
  icon: typeof Brain
  title: string
  description: string
  detail: string
  color: string
}) {
  return (
    <div className="flex gap-4 items-start">
      <div className={`rounded-xl p-2.5 ${color} flex-shrink-0`}>
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <h4 className="font-semibold text-neutral-900">{title}</h4>
        <p className="text-sm text-neutral-500 leading-relaxed mt-0.5">{description}</p>
        <p className="text-xs text-neutral-400 mt-1 font-mono">{detail}</p>
      </div>
    </div>
  )
}

function FeatureCard({
  icon: Icon,
  title,
  description,
}: {
  icon: typeof Brain
  title: string
  description: string
}) {
  return (
    <div className="bg-white border border-neutral-200 rounded-2xl p-6 hover-lift">
      <div className="space-y-2">
        <Icon className="h-8 w-8 text-neutral-900" />
        <h3 className="font-semibold text-neutral-900">{title}</h3>
        <p className="text-sm text-neutral-500">{description}</p>
      </div>
    </div>
  )
}

export default async function HomePage() {
  const session = await auth.api.getSession({ headers: await headers() })

  if (session?.user) {
    redirect("/dashboard")
  }

  return (
    <main className="min-h-screen bg-white">
      {/* Navbar */}
      <header className="sticky top-0 z-50 border-b border-neutral-200 bg-white/80 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto flex h-14 items-center justify-between px-6 sm:px-8">
          <div className="flex items-center gap-2.5">
            <img src="/logo.png" alt="Logo" className="h-8 w-8 rounded-lg object-cover" />
            <span className="font-semibold tracking-tight text-neutral-900">RAG Assistant</span>
          </div>
          <Link href="/sign-in">
            <button className="bg-neutral-900 text-white hover:bg-neutral-800 rounded-lg px-6 py-2 font-medium text-sm transition-colors">
              Sign In
            </button>
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="relative flex flex-col items-center justify-center px-6 sm:px-8 pt-24 pb-20">
        <p className="text-sm text-neutral-400 font-mono mb-6">retrieval-augmented generation</p>
        <h1 className="text-5xl md:text-7xl font-semibold tracking-tighter leading-[0.9] text-neutral-900 text-center text-balance mb-6">
          RAG Knowledge Assistant
        </h1>
        <p className="text-lg text-neutral-500 text-center text-balance max-w-2xl mb-3">
          Upload documents or crawl web pages, then ask questions answered exclusively
          from your indexed content using hybrid AI search.
        </p>
        <p className="text-sm text-neutral-400 font-mono text-center max-w-xl mb-10">
          Built with FastAPI, Next.js, PostgreSQL + pgvector, LangChain, and OpenAI.
          Full-stack RAG with streaming responses, real-time pipeline visibility,
          and interactive search analysis.
        </p>

        <div className="flex gap-4">
          <Link href="/sign-up" className="inline-flex items-center bg-neutral-900 text-white hover:bg-neutral-800 rounded-lg px-6 py-3 font-medium text-sm transition-colors">
            Get Started
            <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
          <Link href="/sign-in" className="inline-flex items-center border border-neutral-200 text-neutral-900 hover:bg-neutral-50 rounded-lg px-6 py-3 font-medium text-sm transition-colors">
            Sign In
          </Link>
        </div>
      </section>

      <div className="section-divider max-w-6xl mx-auto" />

      {/* Features Grid */}
      <section className="max-w-6xl mx-auto px-6 sm:px-8 py-20">
        <div className="flex items-center gap-4 mb-3">
          <span className="text-xs font-bold text-neutral-400 uppercase tracking-widest font-mono">Features</span>
          <div className="h-px flex-1 bg-neutral-200" />
        </div>
        <h2 className="text-3xl md:text-4xl font-semibold tracking-tight text-neutral-900 mb-3">How It Works</h2>
        <p className="text-neutral-500 mb-12 max-w-2xl">
          A production-grade Retrieval-Augmented Generation system
          that grounds every answer in your documents -- no hallucinations.
        </p>

        <div className="grid gap-6 md:grid-cols-3">
          <FeatureCard
            icon={Globe}
            title="Multi-Source Ingestion"
            description="Upload PDF and TXT files, or paste any URL. A headless Chromium browser renders JavaScript-heavy pages to extract their full content."
          />
          <FeatureCard
            icon={Search}
            title="Hybrid Search"
            description="Combines vector similarity search (cosine distance) with PostgreSQL full-text search, merged via Reciprocal Rank Fusion for the best of both worlds."
          />
          <FeatureCard
            icon={Zap}
            title="Streaming Answers"
            description="Responses are streamed token-by-token via Server-Sent Events. You see the answer forming in real time, not waiting for the full generation."
          />
          <FeatureCard
            icon={BarChart3}
            title="Pipeline Transparency"
            description="Watch every step of the ingestion pipeline live: text extraction, chunking, embedding generation, and vector storage. See the AI thinking."
          />
          <FeatureCard
            icon={Sparkles}
            title="Search Analysis"
            description="Compare semantic, keyword, and hybrid search results side-by-side with relevance scores. Understand why certain chunks are retrieved."
          />
          <FeatureCard
            icon={Shield}
            title="Multi-Tenant Security"
            description="Better Auth (httpOnly cookies + Google OAuth), per-user data isolation, SSRF protection on URLs, rate limiting, and automatic cleanup of inactive sessions."
          />
        </div>
      </section>

      <div className="section-divider max-w-6xl mx-auto" />

      {/* AI Pipeline Deep Dive */}
      <section className="max-w-6xl mx-auto px-6 sm:px-8 py-20">
        <div className="flex items-center gap-4 mb-3">
          <span className="text-xs font-bold text-neutral-400 uppercase tracking-widest font-mono">Pipeline</span>
          <div className="h-px flex-1 bg-neutral-200" />
        </div>
        <h2 className="text-3xl md:text-4xl font-semibold tracking-tight text-neutral-900 mb-3">The AI Pipeline</h2>
        <p className="text-neutral-500 mb-14 max-w-2xl">
          Every document goes through a multi-stage pipeline before it can answer your questions.
          Here is exactly what happens at each step.
        </p>

        <div className="grid gap-12 md:grid-cols-2">
          {/* Ingestion Pipeline */}
          <div className="space-y-6">
            <h3 className="text-lg font-semibold text-neutral-900 border-b border-neutral-200 pb-2">Document Ingestion</h3>

            <PipelineStep
              icon={FileText}
              title="1. Text Extraction"
              description="PDF files are parsed page-by-page with PyPDF2. URLs are rendered in a headless Chromium browser via Playwright, executing JavaScript and expanding collapsed sections."
              detail="Handles SPAs, dynamic content, and lazy-loaded pages"
              color="bg-blue-50 text-blue-600"
            />
            <PipelineStep
              icon={Scissors}
              title="2. Recursive Chunking"
              description="Text is split using LangChain's RecursiveCharacterTextSplitter, which tries paragraph breaks first, then sentences, then words -- preserving semantic boundaries."
              detail="1200 chars per chunk, 200 char overlap"
              color="bg-orange-50 text-orange-600"
            />
            <PipelineStep
              icon={Cpu}
              title="3. Embedding Generation"
              description="Each chunk is sent to OpenAI's text-embedding-3-small model, which converts it into a 1536-dimensional vector capturing its semantic meaning."
              detail="Cached in Redis to avoid redundant API calls"
              color="bg-purple-50 text-purple-600"
            />
            <PipelineStep
              icon={Database}
              title="4. Vector Storage"
              description="Vectors are stored in PostgreSQL with the pgvector extension. An HNSW index (m=16, ef_construction=64) enables sub-millisecond approximate nearest-neighbor search."
              detail="Plus a GIN index on tsvector for full-text search"
              color="bg-emerald-50 text-emerald-600"
            />
          </div>

          {/* Query Pipeline */}
          <div className="space-y-6">
            <h3 className="text-lg font-semibold text-neutral-900 border-b border-neutral-200 pb-2">Query and Retrieval</h3>

            <PipelineStep
              icon={Sparkles}
              title="5. Semantic Search"
              description="Your question is embedded into the same vector space and compared against all stored chunks using cosine similarity. Finds conceptually related content even with different wording."
              detail="Returns top 15 candidates ranked by vector distance"
              color="bg-purple-50 text-purple-600"
            />
            <PipelineStep
              icon={Type}
              title="6. Keyword Search"
              description="In parallel, PostgreSQL's full-text search engine matches exact terms, acronyms, and technical identifiers that vector similarity might miss."
              detail="plainto_tsquery with ts_rank_cd scoring"
              color="bg-blue-50 text-blue-600"
            />
            <PipelineStep
              icon={Combine}
              title="7. Reciprocal Rank Fusion"
              description="Results from both searches are merged using RRF: each document gets score 1/(k+rank) from each method, then scores are summed. This consistently outperforms either method alone."
              detail="k=60, top 5 results selected"
              color="bg-emerald-50 text-emerald-600"
            />
            <PipelineStep
              icon={MessageSquare}
              title="8. Grounded Generation"
              description="The top chunks are sent to GPT-4o-mini along with conversation history. The system prompt strictly constrains answers to the provided context -- no hallucinations."
              detail="temperature=0.1, last 10 messages of history"
              color="bg-orange-50 text-orange-600"
            />
          </div>
        </div>
      </section>

      <div className="section-divider max-w-6xl mx-auto" />

      {/* Tech Stack */}
      <section className="max-w-6xl mx-auto px-6 sm:px-8 py-20">
        <div className="flex items-center gap-4 mb-3">
          <span className="text-xs font-bold text-neutral-400 uppercase tracking-widest font-mono">Stack</span>
          <div className="h-px flex-1 bg-neutral-200" />
        </div>
        <h2 className="text-3xl md:text-4xl font-semibold tracking-tight text-neutral-900 mb-12">Tech Stack</h2>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: "Frontend", tech: "Next.js 15, React 19, Tailwind" },
            { label: "Backend", tech: "FastAPI, Python 3.11, LangChain" },
            { label: "Database", tech: "PostgreSQL 16, pgvector, Redis" },
            { label: "AI Models", tech: "GPT-4o-mini, text-embedding-3-small" },
            { label: "Auth", tech: "Better Auth (cookies + Google OAuth)" },
            { label: "Crawler", tech: "Playwright (headless Chromium)" },
            { label: "Queue", tech: "Redis Queue (RQ) + workers" },
            { label: "Deploy", tech: "Docker Compose, Traefik" },
          ].map((item) => (
            <div key={item.label} className="rounded-xl border border-neutral-200 bg-neutral-50 p-4 space-y-1">
              <p className="font-semibold text-neutral-900">{item.label}</p>
              <p className="text-xs text-neutral-500">{item.tech}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer CTA */}
      <section className="border-t border-neutral-200">
        <div className="max-w-6xl mx-auto px-6 sm:px-8 py-20 flex flex-col items-center">
          <h2 className="text-3xl md:text-4xl font-semibold tracking-tight text-neutral-900 mb-3">Try It Out</h2>
          <p className="text-neutral-500 mb-8 text-center max-w-md">
            Upload a document, ask a question, and explore the pipeline in action.
          </p>
          <Link href="/sign-up" className="inline-flex items-center bg-neutral-900 text-white hover:bg-neutral-800 rounded-lg px-6 py-3 font-medium text-sm transition-colors">
            Get Started
            <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
          <p className="text-xs text-neutral-400 mt-6 font-mono">
            Showcase mode -- data auto-deleted after 10 minutes of inactivity
          </p>
        </div>
      </section>
    </main>
  )
}
