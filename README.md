# PG Multiuser RAG

A multiuser RAG (Retrieval-Augmented Generation) application with secure authentication using HttpOnly cookies and CSRF protection.

## Architecture

```
Frontend (Next.js 15)          Backend (FastAPI)
        |                            |
        | credentials: include       | Redis (sessions)
        | X-CSRF-Token header        | SQLite (users)
        |                            |
        └──────────────────────────> Pinecone (vectors, namespace = user_id)
                                     OpenAI (embeddings + LLM)
```

**Stack:**
- Backend: FastAPI, Redis sessions, SQLAlchemy, LangChain
- Frontend: Next.js 15, React 19, shadcn/ui, Tailwind CSS 4
- Vector DB: Pinecone (serverless)
- LLM: OpenAI gpt-4o-mini + text-embedding-3-small

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
- Redis server
- Pinecone account
- OpenAI API key

## Quick Start

### Backend

```bash
cd backend
./setup.sh
# Or manually:
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env
# Edit .env with your API keys
uvicorn app.main:app --reload --port 8000
```

### Frontend

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
| POST | /ingest/upload | Upload PDF/TXT | 10/hour |
| POST | /ingest/crawl | Index URL | 10/hour |

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
│   │   │   ├── ingest.py       # Document upload/crawl
│   │   │   ├── chat.py         # RAG chat
│   │   │   └── admin.py        # Admin operations
│   │   ├── main.py             # FastAPI app + middleware
│   │   ├── security.py         # Session + CSRF handling
│   │   ├── session_store.py    # Redis session store
│   │   ├── rag.py              # RAG logic
│   │   ├── ingestion.py        # Document processing
│   │   ├── crawler.py          # Web crawler
│   │   └── background.py       # Background tasks
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
    │   └── upload-section.tsx
    ├── lib/
    │   ├── api.ts              # API client with CSRF
    │   ├── auth.ts             # Auth utilities
    │   └── utils.ts            # Helpers
    └── package.json
```

## Known Limitations

1. **SQLite Database**: The user database uses SQLite which does not handle concurrent writes well. For production with 50+ users, migrate to PostgreSQL.

2. **Synchronous Processing**: Document embedding and web crawling block the request thread. Consider adding a background job queue (Celery, RQ) for production.

3. **Browser Not Pooled**: Each crawl request creates/destroys a Chromium instance. Implement browser pooling for high-traffic scenarios.

4. **CORS Configuration**: Only localhost origins are configured. Add production domains in `backend/app/main.py`.

5. **Cookie secure=True**: Requires HTTPS. For local HTTP development, set `secure=False` in `backend/app/security.py`.

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
