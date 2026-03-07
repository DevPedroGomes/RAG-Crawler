"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { api, type SearchComparisonResult, type EmbeddingPoint } from "@/lib/api"
import { Search, Loader2, BarChart3, Sparkles, Type, Combine, Maximize2 } from "lucide-react"
import { cn } from "@/lib/utils"

// --- Search Comparison ---

function SearchResultList({ results, label, icon: Icon, color }: {
  results: SearchComparisonResult[]
  label: string
  icon: typeof Search
  color: string
}) {
  if (results.length === 0) {
    return (
      <div className="text-xs text-muted-foreground text-center py-4">
        No results
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div className={cn("flex items-center gap-2 text-sm font-medium", color)}>
        <Icon className="h-4 w-4" />
        {label} ({results.length})
      </div>
      <div className="space-y-1.5 max-h-[300px] overflow-y-auto">
        {results.map((r, i) => (
          <div key={i} className="rounded border border-border/50 bg-muted/30 p-2 text-xs space-y-1">
            <div className="flex items-center justify-between">
              <span className="font-mono text-muted-foreground">#{i + 1}</span>
              <span className={cn("font-mono font-bold", color)}>
                {r.score.toFixed(4)}
              </span>
            </div>
            <p className="text-foreground/80 line-clamp-2">{r.content}</p>
            <p className="text-muted-foreground truncate">{r.source}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

function SearchComparison({ hasDocuments }: { hasDocuments: boolean }) {
  const [query, setQuery] = useState("")
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<{
    semantic: SearchComparisonResult[]
    keyword: SearchComparisonResult[]
    hybrid: SearchComparisonResult[]
  } | null>(null)

  const handleSearch = async () => {
    if (!query.trim()) return
    setLoading(true)
    try {
      const data = await api.searchComparison(query.trim())
      setResults(data)
    } catch {
      setResults(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="border-border/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-primary" />
          Search Comparison
        </CardTitle>
        <CardDescription>
          See how semantic, keyword, and hybrid search find different results for the same query
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <Input
            placeholder={hasDocuments ? "Type a query to compare search methods..." : "Index documents first..."}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading || !hasDocuments}
            className="bg-background"
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSearch()
            }}
          />
          <Button onClick={handleSearch} disabled={loading || !query.trim() || !hasDocuments} size="sm">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
          </Button>
        </div>

        {results && (
          <div className="grid gap-4 md:grid-cols-3">
            <SearchResultList
              results={results.semantic}
              label="Semantic"
              icon={Sparkles}
              color="text-purple-500"
            />
            <SearchResultList
              results={results.keyword}
              label="Keyword"
              icon={Type}
              color="text-blue-500"
            />
            <SearchResultList
              results={results.hybrid}
              label="Hybrid (RRF)"
              icon={Combine}
              color="text-green-500"
            />
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// --- Embedding Visualization ---

const SOURCE_COLORS = [
  "hsl(262, 80%, 65%)",  // purple
  "hsl(200, 80%, 55%)",  // blue
  "hsl(150, 70%, 50%)",  // green
  "hsl(35, 90%, 55%)",   // orange
  "hsl(350, 80%, 60%)",  // red
]

function EmbeddingVisualization({ hasDocuments }: { hasDocuments: boolean }) {
  const [points, setPoints] = useState<EmbeddingPoint[]>([])
  const [loading, setLoading] = useState(false)
  const [tooltip, setTooltip] = useState<{ x: number; y: number; point: EmbeddingPoint } | null>(null)
  const canvasRef = useRef<HTMLDivElement>(null)

  const fetchEmbeddings = useCallback(async () => {
    if (!hasDocuments) return
    setLoading(true)
    try {
      const data = await api.getEmbeddings2D()
      setPoints(data.points || [])
    } catch {
      setPoints([])
    } finally {
      setLoading(false)
    }
  }, [hasDocuments])

  useEffect(() => {
    fetchEmbeddings()
  }, [fetchEmbeddings])

  const sourceNames = [...new Set(points.map(p => p.source))]
  const sourceColorMap: Record<string, string> = {}
  sourceNames.forEach((name, i) => {
    sourceColorMap[name] = SOURCE_COLORS[i % SOURCE_COLORS.length]
  })

  const displayName = (source: string) => {
    if (source.length > 30) return "..." + source.slice(-27)
    return source
  }

  return (
    <Card className="border-border/50">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Maximize2 className="h-5 w-5 text-primary" />
              Embedding Space
            </CardTitle>
            <CardDescription>
              2D PCA projection of your document chunks in vector space.
              Each dot is a text chunk. Nearby dots are semantically similar.
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={fetchEmbeddings} disabled={loading || !hasDocuments}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Refresh"}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {!hasDocuments ? (
          <div className="flex items-center justify-center h-[300px] text-muted-foreground text-sm">
            Index documents to visualize embeddings
          </div>
        ) : points.length < 2 ? (
          <div className="flex items-center justify-center h-[300px] text-muted-foreground text-sm">
            {loading ? "Loading..." : "Need at least 2 chunks for visualization"}
          </div>
        ) : (
          <>
            {/* Legend */}
            <div className="flex flex-wrap gap-3 mb-3">
              {sourceNames.map((name) => (
                <div key={name} className="flex items-center gap-1.5 text-xs">
                  <div
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ backgroundColor: sourceColorMap[name] }}
                  />
                  <span className="text-muted-foreground">{displayName(name)}</span>
                </div>
              ))}
            </div>

            {/* Canvas */}
            <div
              ref={canvasRef}
              className="relative h-[350px] rounded-lg border border-border/50 bg-background overflow-hidden"
              onMouseLeave={() => setTooltip(null)}
            >
              {/* Grid lines */}
              <div className="absolute inset-0 opacity-10">
                {[25, 50, 75].map(v => (
                  <div key={`h${v}`}>
                    <div className="absolute left-0 right-0 border-t border-foreground" style={{ top: `${v}%` }} />
                    <div className="absolute top-0 bottom-0 border-l border-foreground" style={{ left: `${v}%` }} />
                  </div>
                ))}
              </div>

              {/* Points */}
              {points.map((point, i) => (
                <div
                  key={i}
                  className="absolute w-2.5 h-2.5 rounded-full cursor-pointer transition-transform hover:scale-[2] hover:z-10"
                  style={{
                    left: `${point.x}%`,
                    top: `${100 - point.y}%`,
                    backgroundColor: sourceColorMap[point.source] || SOURCE_COLORS[0],
                    transform: "translate(-50%, -50%)",
                    opacity: 0.8,
                  }}
                  onMouseEnter={(e) => {
                    const rect = canvasRef.current?.getBoundingClientRect()
                    if (rect) {
                      setTooltip({
                        x: e.clientX - rect.left,
                        y: e.clientY - rect.top,
                        point,
                      })
                    }
                  }}
                />
              ))}

              {/* Tooltip */}
              {tooltip && (
                <div
                  className="absolute z-20 max-w-[250px] rounded-md border border-border bg-popover p-2 text-xs shadow-lg pointer-events-none"
                  style={{
                    left: Math.min(tooltip.x + 12, 250),
                    top: Math.max(tooltip.y - 60, 0),
                  }}
                >
                  <p className="text-foreground line-clamp-3">{tooltip.point.preview}</p>
                  <p className="text-muted-foreground mt-1 truncate">{tooltip.point.source}</p>
                </div>
              )}
            </div>

            <p className="text-xs text-muted-foreground mt-2 text-center">
              {points.length} chunks projected from 1536 dimensions to 2D via PCA
            </p>
          </>
        )}
      </CardContent>
    </Card>
  )
}

// --- Main Panel ---

export function AnalysisPanel({ hasDocuments }: { hasDocuments: boolean }) {
  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h3 className="text-xl font-bold tracking-tight">Under the Hood</h3>
        <p className="text-sm text-muted-foreground">
          Explore how the RAG pipeline processes your queries and visualize your document embeddings
        </p>
      </div>
      <SearchComparison hasDocuments={hasDocuments} />
      <EmbeddingVisualization hasDocuments={hasDocuments} />
    </div>
  )
}
