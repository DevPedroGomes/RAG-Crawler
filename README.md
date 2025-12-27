# PG Multiuser RAG

A multiuser RAG (Retrieval-Augmented Generation) application with secure authentication using HttpOnly cookies and CSRF protection.

## Architecture

```
Frontend (Next.js 15)          Backend (FastAPI)
        |                            |
        | credentials: include       | PostgreSQL (users)
        | X-CSRF-Token header        | Redis (sessions + job queue)
        |                            |
        └──────────────────────────> Pinecone (vectors, namespace = user_id)
                                     OpenAI (embeddings + LLM)

                                     RQ Worker (background processing)
                                          |
                                          └──> Document embedding, URL crawling
```

**Stack:**
- Backend: FastAPI, PostgreSQL, Redis (sessions + RQ), SQLAlchemy, LangChain
- Frontend: Next.js 15, React 19, shadcn/ui, Tailwind CSS 4
- Vector DB: Pinecone (serverless)
- LLM: OpenAI gpt-4o-mini + text-embedding-3-small
- Background Jobs: Redis Queue (RQ)

## Security Features

- HttpOnly cookies for session tokens (XSS protection)
- CSRF double-submit cookie pattern
- Security headers: CSP, X-Frame-Options, X-Content-Type-Options
- SSRF protection in web crawler
- bcrypt password hashing
- Rate limiting on all endpoints
- Namespace isolation in Pinecone per user

## Prerequisites

- Python 3.9+
- Node.js 18+ or 20+
- PostgreSQL 14+
- Redis server
- Pinecone account
- OpenAI API key

## Quick Start

### 1. Database Setup

```bash
# Create PostgreSQL database
createdb ragdb
# Or using psql:
# psql -U postgres -c "CREATE DATABASE ragdb;"
```

### 2. Backend

```bash
cd backend
./setup.sh
# Or manually:
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env
# Edit .env with your API keys and DATABASE_URL
uvicorn app.main:app --reload --port 8000
```

### 3. Background Worker

In a separate terminal, start the RQ worker for background processing:

```bash
cd backend
source venv/bin/activate
rq worker --url redis://localhost:6379/0
```

### 4. Frontend

```bash
cd frontend
pnpm install
cp .env.example .env.local
# Edit .env.local if needed
pnpm dev
```

Access at http://localhost:3000

## Configuration

### Backend (.env)

| Variable | Description |
|----------|-------------|
| OPENAI_API_KEY | OpenAI API key |
| PINECONE_API_KEY | Pinecone API key |
| PINECONE_INDEX_NAME | Pinecone index name |
| PINECONE_INDEX_HOST | Pinecone index host (optional) |
| JWT_SECRET | Secret for session tokens |
| REDIS_URL | Redis connection URL |
| EMBEDDING_MODEL | OpenAI embedding model (default: text-embedding-3-small) |
| CHUNK_SIZE | Text chunk size (default: 1200) |
| CHUNK_OVERLAP | Chunk overlap (default: 200) |
| TOP_K | Number of retrieval results (default: 5) |

### Frontend (.env.local)

| Variable | Description |
|----------|-------------|
| NEXT_PUBLIC_API_URL | Backend URL (default: http://localhost:8000) |

## API Endpoints

### Authentication

| Method | Endpoint | Description | Rate Limit |
|--------|----------|-------------|------------|
| POST | /auth/signup | Create account | 5/hour |
| POST | /auth/login | Login | 10/hour |
| POST | /auth/logout | Logout (clears cookies) | - |

### Document Ingestion (requires auth + CSRF)

| Method | Endpoint | Description | Rate Limit |
|--------|----------|-------------|------------|
| POST | /ingest/upload | Queue PDF/TXT for processing (returns job_id) | 10/hour |
| POST | /ingest/crawl | Queue URL for indexing (returns job_id) | 10/hour |

### Jobs (requires auth)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /jobs/{job_id} | Get job status (queued/started/finished/failed) |

### Chat (requires auth + CSRF)

| Method | Endpoint | Description | Rate Limit |
|--------|----------|-------------|------------|
| POST | /chat/ask | Ask question | 20/minute |
| POST | /chat/reset | Clear user index | - |

### Admin (requires auth + CSRF)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /admin/logout | Full logout + Pinecone cleanup |

## Project Structure

```
rag-crawler-indexer/
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   │   ├── auth.py         # Authentication endpoints
│   │   │   ├── ingest.py       # Document upload/crawl (async)
│   │   │   ├── chat.py         # RAG chat
│   │   │   ├── jobs.py         # Job status endpoint
│   │   │   └── admin.py        # Admin operations
│   │   ├── main.py             # FastAPI app + middleware
│   │   ├── security.py         # Session + CSRF handling
│   │   ├── session_store.py    # Redis session store
│   │   ├── tasks.py            # RQ background tasks
│   │   ├── rag.py              # RAG logic
│   │   ├── ingestion.py        # Document processing
│   │   ├── crawler.py          # Web crawler + browser pool
│   │   └── background.py       # Scheduled tasks
│   ├── requirements.txt
│   └── setup.sh
└── frontend/
    ├── app/
    │   ├── page.tsx            # Login page
    │   ├── layout.tsx          # Root layout
    │   └── dashboard/page.tsx  # Dashboard
    ├── components/
    │   ├── auth-form.tsx
    │   ├── chat-section.tsx
    │   └── upload-section.tsx  # With job polling
    ├── lib/
    │   ├── api.ts              # API client with CSRF + job status
    │   ├── auth.ts             # Auth utilities
    │   └── utils.ts            # Helpers
    └── package.json
```

## Known Limitations

1. **CORS Configuration**: Only localhost origins are configured. Add production domains in `backend/app/main.py`.

2. **Cookie secure=True**: Requires HTTPS. For local HTTP development, set `secure=False` in `backend/app/security.py`.

3. **Single Worker**: For high traffic, run multiple RQ workers: `rq worker -c 4` or use a process manager.

4. **No Job Persistence**: Job results are stored in Redis with default TTL. Configure RQ result TTL for longer retention if needed.

## Troubleshooting

### CSRF token invalid
- Clear browser cookies and login again
- Verify X-CSRF-Token header is being sent

### Session not found
- Session expired (2 hours TTL)
- Redis connection issue
- Backend restarted

### Pinecone errors
- Check API key and index name
- Verify region matches your account

### Playwright errors
```bash
python -m playwright install chromium
```

### CORS errors
- Verify `credentials: "include"` in frontend
- Check backend CORS origins match frontend URL

### Jobs stuck in "queued" status
- Ensure RQ worker is running: `rq worker --url redis://localhost:6379/0`
- Check Redis connection: `redis-cli ping`
- View queue: `rq info --url redis://localhost:6379/0`

### Database connection errors
- Verify PostgreSQL is running
- Check DATABASE_URL format: `postgresql://user:password@host:port/database`
- Ensure database exists: `createdb ragdb`
