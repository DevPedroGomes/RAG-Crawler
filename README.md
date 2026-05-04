# RAG-Crawler

A multi-tenant Retrieval-Augmented Generation application that ingests user-uploaded documents and crawled web pages, then answers questions exclusively from that content using hybrid search and streaming LLM responses. Five Docker services behind Traefik, with full per-user data isolation.

Live deployment: https://ragcrawler.pgdev.com.br

---

## Overview

A signed-in user can:

1. Upload PDF or TXT files, or submit a URL.
2. Watch the ingest pipeline stream progress events (extracting / chunking / embedding / stored).
3. Ask questions in chat. Answers are generated only from the user's own indexed chunks, with sources cited inline. Tokens stream over Server-Sent Events.

Authentication uses Better Auth (httpOnly session cookie, no JWT in JavaScript). Sessions are stored in Postgres and the FastAPI backend resolves the cookie by reading the shared `session` table. Each user gets an isolated pgvector collection (`user_<id>`); cross-tenant access is impossible at the SQL level.

The system is intentionally constrained for showcase: 5 documents per user, 5 MB per file, auto-cleanup after 10 minutes of inactivity.

---

## Architecture

```mermaid
flowchart TB
    User([User browser])

    subgraph Edge[Edge - Traefik]
        Traefik[Traefik v3<br/>TLS + HSTS + global rate limit]
    end

    subgraph FE[Next.js 15 frontend - container ragcrawler-frontend]
        MW[middleware.ts<br/>cookie presence gate]
        BAHandler[/api/auth/...all/<br/>Better Auth handler]
        Proxy[/api/backend/*<br/>Next.js rewrite to FastAPI/]
        UI[React 19 + Radix + Tailwind<br/>lib/api.ts credentials: include]
    end

    subgraph BE[FastAPI backend - container ragcrawler-backend]
        Auth[app/auth.py<br/>Better Auth bridge<br/>reads session row from Postgres]
        Routers[Routers: ingest, chat,<br/>jobs, analysis, admin]
        SSRF{{SSRF GUARD<br/>app/crawler.py is_safe_url<br/>+ Playwright route '**/*' re-validate}}
        RAG[app/rag.py<br/>hybrid retrieval + ChatOpenAI stream]
    end

    subgraph Worker[RQ worker - container ragcrawler-worker]
        WorkerProc[rq.cli worker<br/>process_file_task / process_url_task]
        Crawler[Playwright headless Chromium<br/>render_urls + ssrf_guard]
        Chunker[RecursiveCharacterTextSplitter<br/>1200 chars / 200 overlap]
    end

    subgraph Data[Data plane - internal Docker network only]
        PG[(PostgreSQL 16 + pgvector<br/>HNSW + GIN tsvector<br/>shared with Better Auth)]
        Redis[(Redis 7<br/>requirepass + appendonly<br/>queue + embedding cache)]
    end

    LLM[(OpenAI / OpenRouter<br/>chat completions)]
    Emb[(OpenAI<br/>text-embedding-3-small)]
    Web[(External URL<br/>UNTRUSTED INPUT)]

    User -->|HTTPS| Traefik
    Traefik --> MW
    MW -->|/api/auth/*| BAHandler
    MW -->|/api/backend/*| Proxy
    MW -->|app routes| UI
    UI -->|fetch credentials: include| Proxy
    BAHandler <-->|user/session/account| PG
    Proxy -->|http internal| Auth
    Auth -->|SELECT session JOIN user| PG
    Auth --> Routers
    Routers --> SSRF
    Routers --> RAG
    Routers -->|enqueue| Redis
    Redis -->|dequeue| WorkerProc
    WorkerProc --> SSRF
    SSRF -.->|validated URL| Crawler
    Crawler -->|UNTRUSTED FETCH| Web
    Crawler --> Chunker
    Chunker -->|embed_documents| Emb
    Chunker -->|INSERT vector| PG
    WorkerProc -->|publish progress| Redis
    RAG -->|hybrid search| PG
    RAG -->|embed_query cached| Emb
    RAG -->|stream tokens| LLM
    LLM -.->|SSE: stream-open, sources,<br/>token*, done| UI

    classDef untrusted stroke:#c00,stroke-width:2px,stroke-dasharray:5
    classDef guard fill:#ffd,stroke:#c80,stroke-width:2px
    class Web untrusted
    class SSRF guard
```

The dashed boundary marks untrusted input: the URL submitted by the user, every redirect hop returned by the remote server, and every subresource the headless browser tries to load. The yellow SSRF guard runs at four layers: form validation in the FastAPI router, full revalidation per redirect inside the httpx client (5 hops max), Playwright `context.route('**/*')` interception for browser subresources, and an A+AAAA DNS resolution check that walks every returned address through the deny lists.

Networking: only the frontend joins the Traefik `proxy` network. All five containers share an `internal` bridge. Postgres and Redis are not published to the host. The backend is reachable only as `http://ragcrawler-backend:8000` from inside the network.

---

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Frontend | Next.js 15.5 (standalone output), React 19, TypeScript 5 | `poweredByHeader: false`, lightweight cookie middleware, `/api/backend/*` rewrite to FastAPI |
| UI | Radix UI primitives, Tailwind CSS 4, Lucide icons, react-markdown + remark-gfm | |
| Auth | Better Auth 1.5 (`better-auth/next-js` handler at `/api/auth/[...all]`) | httpOnly cookie `__Secure-better-auth.session_token`; email/password + optional Google OAuth; sessions persisted in Postgres |
| Backend | FastAPI 0.115, Python 3.11, Uvicorn | JSON logging in production, slowapi rate limiting, security headers + strict CSP middleware |
| ORM / DB driver | SQLAlchemy 2.0, psycopg2-binary | dedicated small connection pool for the auth bridge so it cannot starve SQLAlchemy |
| LLM | LangChain 0.3 + `langchain-openai` `ChatOpenAI` | Provider abstraction: `LLM_PROVIDER=openai` (default) or `openrouter`; same OpenAI-compatible client, swapped `base_url` and `api_key` |
| Embeddings | OpenAI `text-embedding-3-small` (1536 dims) | always direct to OpenAI even when chat is on OpenRouter |
| Vector DB | PostgreSQL 16 + `pgvector/pgvector:pg16` | `langchain_pg_embedding` with `vector(1536)` + HNSW (m=16, ef_construction=64) + generated `tsvector` column with GIN index |
| Job queue | Redis 7 + RQ 1.16 | `requirepass` from `REDIS_PASSWORD`, AOF persistence; embedding cache + per-job progress stream stored here too |
| Crawler | Playwright 1.47 (headless Chromium, official `mcr.microsoft.com/playwright/python` image) | `BrowserPool` reuses a single browser; per-request isolated context |
| PDF parsing | `pypdf` (replaces PyPDF2) | |
| Reverse proxy | Traefik v3 (external service) | TLS via Let's Encrypt, HSTS preload, global rate limit middleware, `strip-server-header` |
| Container hardening | `security_opt: no-new-privileges`, `cap_drop: ALL`, `tmpfs: /tmp` on backend and worker | non-root user (uid 10001 backend, 1001 frontend) |

Resource limits per service are declared in `docker-compose.yml`: backend 1 GiB, worker 2 GiB, postgres 1 GiB, redis 256 MiB, frontend 512 MiB.

---

## Ingest Pipeline

```
POST /ingest/upload (PDF/TXT)        POST /ingest/crawl (URL)
            |                                  |
            v                                  v
    backend/app/routers/ingest.py
      - Better Auth cookie check (require_auth)
      - per-user threading.Lock (race-free document limit check)
      - magic-bytes check for PDF (%PDF-)             |
      - is_safe_url(url) ----------------------------+
                                |
                                v
                  enqueue_file_task / enqueue_url_task
                                |
                          Redis Queue 'default'
                                |
                                v
        backend/app/tasks.py (process_*_task) running in worker
                                |
                                v
              -- File path ---------------- URL path -----
              | pypdf PdfReader            Playwright BrowserPool   |
              | extract per page           page.goto, networkidle   |
              |                            ssrf_guard re-validates  |
              |                            every subresource        |
              ----------------|---------------|-------------------
                              v               v
                    RecursiveCharacterTextSplitter (1200/200, paragraphs->lines->spaces)
                              |
                              v
                    OpenAI text-embedding-3-small  (1536 dims)
                              |
                              v
                    INSERT INTO langchain_pg_embedding (collection_id=user_<id>)
                       generated document_tsv tsvector built automatically
                              |
                              v
                    publish progress to Redis list job_progress:<job_id>
```

The frontend polls `GET /jobs/{job_id}` at 2 s intervals, displays the live progress steps (extracting -> extracted -> chunking -> embedding -> stored -> completed) and any error information. On retrieval failure mid-ingest, `_cleanup_partial_source` removes the partially indexed chunks for that source so the user is never left in a half-indexed state.

Limits enforced per request:
- file size 5 MB; PDF magic bytes must match
- max 5 unique sources per user (counted before enqueue, under a per-user lock)
- 10 ingest requests per hour per user (slowapi, keyed on user id)

---

## Chat Pipeline

```
User question (UI)
        |
        v
POST /api/backend/chat/ask/stream
        | (Next.js rewrite, internal http)
        v
backend/app/routers/chat.py
  - require_auth (Better Auth cookie)
  - slowapi 20/min/user
        |
        v
StreamingResponse(answer_stream, media_type=text/event-stream)
        |
        v
backend/app/rag.py answer_stream
  1. yield ": stream-open\n\n"      <-- flushes Traefik / Next fetch buffer
  2. _retrieve_docs:
       _get_embedding_with_cache(question)   (Redis SHA256 key, 1h TTL)
       search_hybrid:
         search_semantic   (cosine via HNSW, fetch_k = 3 * top_k)
         search_keyword    (plainto_tsquery + ts_rank_cd via GIN)
         _reciprocal_rank_fusion(k=60)
         falls back to semantic-only if keyword returns 0
  3. yield event: sources  data: [...]
  4. _get_llm() -> ChatOpenAI
       provider=openai      -> OpenAI directly
       provider=openrouter  -> base_url=OPENROUTER_BASE_URL, api_key=OPENROUTER_API_KEY,
                               default_headers HTTP-Referer + X-Title
  5. for chunk in llm.stream(prompt): yield event: token
  6. try / finally guarantees exactly one event: done at the end,
     even when the generator is cancelled or the LLM raises.
        |
        v
SSE response headers:
  Cache-Control: no-cache, no-transform
  X-Accel-Buffering: no
        |
        v
Browser EventSource consumer in lib/api.ts
  spec-compliant parser (separates events on \n\n,
  joins multi-line data:, ignores comment :)
  -> onSources / onToken / onDone / onError
```

The system prompt restricts the model to context-only answers, requires inline source attribution, and preserves the last 10 messages of conversation history (`_convert_chat_history` truncates).

---

## Security Model

### Authentication

- Better Auth runs server-side in Next.js at `/api/auth/[...all]/route.ts` using `betterAuth({ database: new Pool(...) })`, sharing the same Postgres cluster as the backend.
- Sessions are stored in the `session` table (schema in `backend/migrations/0001_better_auth.sql`). The cookie value is `<token>.<signature>`; only `<token>` is the row key.
- Cookies are httpOnly, `__Secure-` prefixed in production. JS code never reads or sends a Bearer token; `lib/api.ts` uses `credentials: 'include'` and the browser attaches the cookie automatically.
- The Next.js middleware (`frontend/middleware.ts`) is intentionally lightweight: it only checks for cookie presence and redirects to `/sign-in?callbackUrl=...` on miss. Cryptographic validation happens twice afterwards: once inside the Better Auth handler, once inside FastAPI for every protected route.
- FastAPI auth bridge lives in `backend/app/auth.py`. `get_current_user` parses the cookie, splits on the first `.`, and runs a parameterized SQL `SELECT ... FROM "session" s JOIN "user" u WHERE s.token = %s AND s."expiresAt" > NOW()` against a small dedicated psycopg2 pool. There is no JWT signing or verification on the Python side.
- Rate-limit keys are derived from the resolved user id (`get_user_id_for_rate_limit`); unauthenticated traffic is rejected at auth, never bucketed under the upstream proxy IP.

### SSRF defense (file `backend/app/crawler.py`)

`is_safe_url` is the canonical gate. It runs at four layers:

1. **Form-time validation** in `routers/ingest.crawl` before the job is enqueued.
2. **Per-redirect re-validation** in the httpx helper `_get`: redirects are not auto-followed; each `Location` is resolved and re-checked against `is_safe_url` (5 hops max).
3. **Playwright network interception**: `context.route('**/*', _ssrf_guard)` re-validates every request the browser makes, including subresources, XHR, and any 30x sent by the page itself.
4. **DNS A+AAAA enumeration**: every address returned by `getaddrinfo` is validated through `_check_ip`. If any address fails the check the URL is rejected.

`_check_ip` rejects:

- Anything `is_private | is_loopback | is_link_local | is_reserved | is_multicast | is_unspecified`.
- Extra IPv4 networks: `0.0.0.0/8`, `100.64.0.0/10` (CGNAT), `169.254.0.0/16` (link-local + AWS metadata), `192.0.0.0/24`, `192.0.2.0/24` (TEST-NET-1), `198.18.0.0/15` (benchmark), `198.51.100.0/24` (TEST-NET-2), `203.0.113.0/24` (TEST-NET-3), `240.0.0.0/4` (reserved), `255.255.255.255/32`.
- Extra IPv6 networks: `fd00:ec2::/32` (AWS IPv6 metadata range).
- IPv6 transitions: `ipv4_mapped`, `sixtofour`, and `teredo` are unwrapped and the embedded IPv4 is recursively checked, so `::ffff:169.254.169.254` and friends do not bypass the v4 deny list.

Hostname normalization runs IDNA encoding, strips trailing dot, rejects `@` (userinfo), and **strict dotted-quad regex** for IPv4 literals, blocking obfuscated encodings such as `0177.0.0.1`, hex (`0xC0A80001`), and integer (`3232235521`).

Schemes are restricted to `http` / `https`. Ports `22, 23, 25, 3306, 5432, 6379, 27017` are rejected. Hostname deny list covers `localhost`, IPv6 loopback aliases, `metadata.google.internal`, `metadata`, `metadata.azure.{com,internal}`, `instance-data`.

### Tenant isolation

- Each user gets a dedicated pgvector collection named `user_<better_auth_user_id>`. All ingest, retrieval, count, and delete queries filter on this collection.
- The vector store factory `get_vector_store(user_id)` is `lru_cache`d with size 32 to amortize PGVector startup cost.
- Job ownership: every RQ job stores `meta={'user_id': user_id}`. `GET /jobs/{job_id}` returns `not_found` (not 403) when the requester does not own the job, so existence is never leaked.
- Rate limits are keyed on user id, not IP, so the shared upstream IP from Traefik does not collapse all tenants into one bucket.

### Production hardening

- `/docs`, `/redoc`, `/openapi.json` are disabled when `ENVIRONMENT=production`.
- `/health` is a public minimal liveness probe returning only `{"status": "ok"}`. `/health/detailed` is auth-gated and is the only endpoint that exposes Postgres / Redis / worker state.
- Backend and worker containers run with `security_opt: no-new-privileges:true`, `cap_drop: ALL`, and `tmpfs: /tmp`. Both run as a non-root user.
- Redis requires `REDIS_PASSWORD`; AOF persistence is enabled.
- Strict CSP (`default-src 'none'; frame-ancestors 'none'`), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, restrictive `Permissions-Policy` for the API surface.
- On startup the backend logs CRITICAL if `ENVIRONMENT=production` but `DATABASE_URL` still points at `localhost`/`127.0.0.1`, since Better Auth requires the shared cluster.

---

## Local Development

Prerequisites: Docker Engine 27+ and Docker Compose v2, an OpenAI API key, optional Google OAuth credentials, optional OpenRouter key.

```bash
git clone <repository-url> /opt/showcase/RAG-Crawler
cd /opt/showcase/RAG-Crawler

# Fill in the env file (see Environment Variables below)
cp backend/.env.example .env   # base, then add the Better Auth + frontend keys

# Build and start
docker compose up -d --build
# First build: ~5-10 min (Playwright base image, Next.js compile)

docker compose ps

# Apply Better Auth schema (idempotent; do this once per fresh Postgres volume)
docker exec -i ragcrawler-db psql -U ragcrawler -d ragdb \
  < backend/migrations/0001_better_auth.sql

# Liveness check
docker exec ragcrawler-backend curl -s http://127.0.0.1:8000/health
```

The backend's pgvector init and required tables are created automatically on the first FastAPI startup (`init_pgvector()` in `pgvector_store.py`). The Better Auth tables (`user`, `session`, `account`, `verification`) must be created manually from the SQL migration above; Better Auth's Pool driver does not run schema migrations on boot.

For local non-Docker frontend dev (point at the running backend):

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 \
BACKEND_INTERNAL_URL=http://localhost:8000 \
BETTER_AUTH_SECRET=$(openssl rand -hex 32) \
BETTER_AUTH_URL=http://localhost:3000 \
DATABASE_URL=postgresql://ragcrawler:...@localhost:5432/ragdb \
npm run dev
```

---

## Deployment

Production runs on `pgdev.com.br` behind a shared Traefik reverse proxy on the external `proxy` Docker network. The frontend container declares all the Traefik labels in `docker-compose.yml`:

- Router rule: `Host(`ragcrawler.pgdev.com.br`)`
- TLS via Let's Encrypt resolver `letsencrypt`
- Middleware chain: `ragcrawler-security@docker` (HSTS preload, frame-deny, content-type-nosniff, referrer-policy strict-origin-when-cross-origin, browser-xss-filter), `global-ratelimit@file`, `strip-server-header@file`
- Service port `3000` (Next.js standalone)

Postgres, Redis, the backend, and the worker stay on the `internal` network only. The backend is reached exclusively via the Next.js rewrite `/api/backend/*` -> `http://ragcrawler-backend:8000`. There is no direct ingress to FastAPI.

Updates:

```bash
cd /opt/showcase/RAG-Crawler
git pull
docker compose build
docker compose up -d
docker compose logs -f backend worker
```

---

## Environment Variables

Two `.env` consumers (the same file at the project root works because variables are namespaced):

### Required

| Variable | Where | Description |
|---|---|---|
| `OPENAI_API_KEY` | backend, worker | Used for both chat completions (when `LLM_PROVIDER=openai`) and **always** for embeddings |
| `POSTGRES_PASSWORD` | postgres, backend, worker, frontend | Strong random; reused inside the composed `DATABASE_URL` |
| `REDIS_PASSWORD` | redis, backend, worker | Strong random; reused inside `REDIS_URL` |
| `BETTER_AUTH_SECRET` | frontend | 64-char hex (`openssl rand -hex 32`); used by Better Auth to sign cookies |
| `BETTER_AUTH_URL` | frontend | Public origin, e.g. `https://ragcrawler.pgdev.com.br` |
| `NEXT_PUBLIC_APP_URL` | frontend | Same as above; baked at build time as Better Auth trusted origin |

### Optional

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `openai` | Set to `openrouter` to route chat completions through OpenRouter; embeddings still go to OpenAI |
| `LLM_MODEL` | `gpt-4o-mini` | Model id; with OpenRouter this is the OpenRouter id (e.g. `deepseek/deepseek-chat`) |
| `OPENROUTER_API_KEY` | empty | Required only when `LLM_PROVIDER=openrouter` |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | 1536-dim; changing requires migrating the `vector(1536)` column |
| `CHUNK_SIZE`, `CHUNK_OVERLAP`, `TOP_K` | 1200 / 200 / 5 | RAG tuning |
| `ENABLE_HYBRID_SEARCH` | `true` | Set `false` to fall back to MMR-only semantic retrieval |
| `EMBEDDING_CACHE_TTL` | `3600` | Redis TTL (seconds) for query embedding cache |
| `MAX_DOCUMENTS_PER_USER` | `5` | Showcase cap |
| `HEADLESS`, `BATCH_SIZE`, `CRAWL_DELAY_MS`, `USER_AGENT` | crawler tuning | |
| `POSTGRES_USER`, `POSTGRES_DB` | `ragcrawler` / `ragdb` | |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | empty | Google OAuth button only renders when both are set |
| `CORS_ORIGINS` | empty | Comma-separated extra dev origins (the production origin is hard-coded) |
| `LOG_LEVEL` | `INFO` | |
| `ENVIRONMENT` | `development` | `production` triggers JSON logging, hides `/docs`, gates `/health/detailed`, refuses to accept localhost `DATABASE_URL` |

`DATABASE_URL`, `REDIS_URL`, `NEXT_PUBLIC_API_URL` (=`/api/backend`), and `BACKEND_INTERNAL_URL` (=`http://ragcrawler-backend:8000`) are computed by `docker-compose.yml` and should not be overridden in the `.env`.

Note: `backend/.env.example` still references Clerk variables and predates the Better Auth migration; the canonical reference is now `frontend/.env.example` plus this section.

---

## Project Layout

```
backend/
  app/
    auth.py             Better Auth bridge (cookie -> SQL session lookup)
    security.py         Re-export of require_auth for legacy routes
    crawler.py          is_safe_url + Playwright BrowserPool + ssrf_guard
    rag.py              _get_llm provider abstraction, answer_stream SSE
    pgvector_store.py   init_pgvector, search_semantic/keyword/hybrid + RRF
    ingestion.py        pypdf reader, RecursiveCharacterTextSplitter, embed_and_store
    tasks.py            RQ queue + process_file_task / process_url_task
    main.py             FastAPI app, security headers, lifespan (BrowserPool/init_pgvector)
    routers/            ingest, chat, jobs, analysis, admin, auth
  migrations/
    0001_better_auth.sql   user / session / account / verification tables
  Dockerfile          Playwright official image + libpq + non-root user
frontend/
  app/
    api/auth/[...all]/route.ts   Better Auth handler
    sign-in, sign-up, dashboard
  lib/
    auth-server.ts      Better Auth config (Pool, providers, session)
    auth-client.ts      createAuthClient with credentials: include
    api.ts              fetch wrapper, SSE parser, 401 -> /sign-in redirect
  middleware.ts         Cookie presence gate
  next.config.mjs       standalone, poweredByHeader: false, /api/backend rewrite
docker-compose.yml      5 services + internal/proxy networks + volumes
```
