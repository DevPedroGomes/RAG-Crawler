import { auth } from "@clerk/nextjs/server"
import { redirect } from "next/navigation"
import {
  Brain, FileText, Search, Cpu, Database, MessageSquare,
  Scissors, ArrowRight, Sparkles, Type, Combine, Shield,
  Zap, Globe, BarChart3
} from "lucide-react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"

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
      <div className={`rounded-lg p-2.5 ${color} flex-shrink-0`}>
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <h4 className="font-semibold text-foreground">{title}</h4>
        <p className="text-sm text-muted-foreground mt-0.5">{description}</p>
        <p className="text-xs text-muted-foreground/70 mt-1 font-mono">{detail}</p>
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
    <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
      <CardContent className="pt-6 space-y-2">
        <Icon className="h-8 w-8 text-primary" />
        <h3 className="font-semibold">{title}</h3>
        <p className="text-sm text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  )
}

export default async function HomePage() {
  const { userId } = await auth()

  if (userId) {
    redirect("/dashboard")
  }

  return (
    <main className="min-h-screen">
      {/* Hero */}
      <section className="relative flex flex-col items-center justify-center px-4 pt-24 pb-16">
        <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-primary/20 via-background to-background" />

        <div className="mb-6 flex justify-center">
          <div className="rounded-2xl bg-primary/10 p-5">
            <Brain className="h-14 w-14 text-primary" />
          </div>
        </div>
        <h1 className="mb-3 text-5xl font-bold tracking-tight text-center text-balance">
          RAG Knowledge Assistant
        </h1>
        <p className="text-xl text-muted-foreground text-center text-balance max-w-2xl mb-2">
          Upload documents or crawl web pages, then ask questions answered exclusively
          from your indexed content using hybrid AI search.
        </p>
        <p className="text-sm text-muted-foreground/70 text-center max-w-xl mb-8">
          Built with FastAPI, Next.js, PostgreSQL + pgvector, LangChain, and OpenAI.
          Full-stack RAG with streaming responses, real-time pipeline visibility,
          and interactive search analysis.
        </p>

        <div className="flex gap-4">
          <Button asChild size="lg">
            <Link href="/sign-up">
              Get Started
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
          <Button asChild variant="outline" size="lg">
            <Link href="/sign-in">Sign In</Link>
          </Button>
        </div>
      </section>

      {/* Features Grid */}
      <section className="max-w-5xl mx-auto px-4 py-16">
        <h2 className="text-2xl font-bold text-center mb-2">How It Works</h2>
        <p className="text-muted-foreground text-center mb-10 max-w-2xl mx-auto">
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
            description="Clerk JWT authentication, per-user data isolation, SSRF protection on URLs, rate limiting, and automatic cleanup of inactive sessions."
          />
        </div>
      </section>

      {/* AI Pipeline Deep Dive */}
      <section className="max-w-4xl mx-auto px-4 py-16">
        <h2 className="text-2xl font-bold text-center mb-2">The AI Pipeline</h2>
        <p className="text-muted-foreground text-center mb-12 max-w-2xl mx-auto">
          Every document goes through a multi-stage pipeline before it can answer your questions.
          Here is exactly what happens at each step.
        </p>

        <div className="grid gap-8 md:grid-cols-2">
          {/* Ingestion Pipeline */}
          <div className="space-y-6">
            <h3 className="text-lg font-semibold border-b border-border/50 pb-2">Document Ingestion</h3>

            <PipelineStep
              icon={FileText}
              title="1. Text Extraction"
              description="PDF files are parsed page-by-page with PyPDF2. URLs are rendered in a headless Chromium browser via Playwright, executing JavaScript and expanding collapsed sections."
              detail="Handles SPAs, dynamic content, and lazy-loaded pages"
              color="bg-blue-500/10 text-blue-500"
            />
            <PipelineStep
              icon={Scissors}
              title="2. Recursive Chunking"
              description="Text is split using LangChain's RecursiveCharacterTextSplitter, which tries paragraph breaks first, then sentences, then words -- preserving semantic boundaries."
              detail="1200 chars per chunk, 200 char overlap"
              color="bg-orange-500/10 text-orange-500"
            />
            <PipelineStep
              icon={Cpu}
              title="3. Embedding Generation"
              description="Each chunk is sent to OpenAI's text-embedding-3-small model, which converts it into a 1536-dimensional vector capturing its semantic meaning."
              detail="Cached in Redis to avoid redundant API calls"
              color="bg-purple-500/10 text-purple-500"
            />
            <PipelineStep
              icon={Database}
              title="4. Vector Storage"
              description="Vectors are stored in PostgreSQL with the pgvector extension. An HNSW index (m=16, ef_construction=64) enables sub-millisecond approximate nearest-neighbor search."
              detail="Plus a GIN index on tsvector for full-text search"
              color="bg-green-500/10 text-green-500"
            />
          </div>

          {/* Query Pipeline */}
          <div className="space-y-6">
            <h3 className="text-lg font-semibold border-b border-border/50 pb-2">Query and Retrieval</h3>

            <PipelineStep
              icon={Sparkles}
              title="5. Semantic Search"
              description="Your question is embedded into the same vector space and compared against all stored chunks using cosine similarity. Finds conceptually related content even with different wording."
              detail="Returns top 15 candidates ranked by vector distance"
              color="bg-purple-500/10 text-purple-500"
            />
            <PipelineStep
              icon={Type}
              title="6. Keyword Search"
              description="In parallel, PostgreSQL's full-text search engine matches exact terms, acronyms, and technical identifiers that vector similarity might miss."
              detail="plainto_tsquery with ts_rank_cd scoring"
              color="bg-blue-500/10 text-blue-500"
            />
            <PipelineStep
              icon={Combine}
              title="7. Reciprocal Rank Fusion"
              description="Results from both searches are merged using RRF: each document gets score 1/(k+rank) from each method, then scores are summed. This consistently outperforms either method alone."
              detail="k=60, top 5 results selected"
              color="bg-green-500/10 text-green-500"
            />
            <PipelineStep
              icon={MessageSquare}
              title="8. Grounded Generation"
              description="The top chunks are sent to GPT-4o-mini along with conversation history. The system prompt strictly constrains answers to the provided context -- no hallucinations."
              detail="temperature=0.1, last 10 messages of history"
              color="bg-orange-500/10 text-orange-500"
            />
          </div>
        </div>
      </section>

      {/* Tech Stack */}
      <section className="max-w-4xl mx-auto px-4 py-16">
        <h2 className="text-2xl font-bold text-center mb-10">Tech Stack</h2>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center text-sm">
          {[
            { label: "Frontend", tech: "Next.js 15, React 19, Tailwind" },
            { label: "Backend", tech: "FastAPI, Python 3.11, LangChain" },
            { label: "Database", tech: "PostgreSQL 16, pgvector, Redis" },
            { label: "AI Models", tech: "GPT-4o-mini, text-embedding-3-small" },
            { label: "Auth", tech: "Clerk (JWT RS256)" },
            { label: "Crawler", tech: "Playwright (headless Chromium)" },
            { label: "Queue", tech: "Redis Queue (RQ) + workers" },
            { label: "Deploy", tech: "Docker Compose, Traefik" },
          ].map((item) => (
            <div key={item.label} className="rounded-lg border border-border/50 bg-card/50 p-4 space-y-1">
              <p className="font-semibold text-foreground">{item.label}</p>
              <p className="text-xs text-muted-foreground">{item.tech}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer CTA */}
      <section className="flex flex-col items-center px-4 py-16 border-t border-border/50">
        <h2 className="text-2xl font-bold mb-2">Try It Out</h2>
        <p className="text-muted-foreground mb-6 text-center max-w-md">
          Upload a document, ask a question, and explore the pipeline in action.
        </p>
        <Button asChild size="lg">
          <Link href="/sign-up">
            Get Started
            <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </Button>
        <p className="text-xs text-muted-foreground mt-4">
          Showcase mode -- data auto-deleted after 10 minutes of inactivity
        </p>
      </section>
    </main>
  )
}
