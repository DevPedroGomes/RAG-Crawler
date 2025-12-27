# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**PG Multiuser RAG** is a security-first multiuser RAG (Retrieval-Augmented Generation) application with:
- **Backend:** FastAPI (Python) with HttpOnly cookie-based authentication
- **Frontend:** Next.js 15 with React 19, shadcn/ui, and Tailwind CSS 4
- **Vector DB:** Pinecone with namespace isolation per user
- **LLM Stack:** OpenAI embeddings (text-embedding-3-small) + GPT-4o-mini via LangChain

**Security is the #1 priority**: This project implements modern web authentication best practices using HttpOnly cookies, CSRF protection, and session-based auth instead of localStorage tokens.

## Development Commands

### Backend

**Setup (first time or after dependency changes):**
```bash
cd backend
./setup.sh
# Or manually:
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env
```

**Run development server:**
```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

**Environment variables** (backend/.env):
- `OPENAI_API_KEY` - OpenAI API key for embeddings and chat
- `PINECONE_API_KEY` - Pinecone API key
- `PINECONE_INDEX_NAME` - Pinecone index name
- `JWT_SECRET` - Secret for session tokens (change in production)

### Frontend

**Setup:**
```bash
cd frontend
pnpm install  # or npm install
cp .env.example .env.local
```

**Development server:**
```bash
pnpm dev  # http://localhost:3000
```

**Build for production:**
```bash
pnpm build
```

**Lint:**
```bash
pnpm lint
```

**Environment variables** (frontend/.env.local):
- `NEXT_PUBLIC_API_URL` - Backend API URL (default: http://localhost:8000)

## Architecture & Code Organization

### Backend (`backend/app/`)

**Core modules:**
- `main.py` - FastAPI app with CORS, security headers, and global middlewares
- `security.py` - Authentication core: password hashing (bcrypt), session validation, CSRF validation, cookie management
- `session_store.py` - Session storage (in-memory dict for dev, migrate to Redis for production)
- `database.py` - SQLAlchemy setup and engine
- `models.py` - SQLAlchemy User model
- `schemas.py` - Pydantic request/response schemas
- `config.py` - Settings loaded from environment variables

**Domain modules:**
- `pinecone_client.py` - Pinecone index initialization and client
- `rag.py` - RAG logic: retriever setup (MMR search), prompt template, answer generation
- `ingestion.py` - Document processing: chunking (RecursiveCharacterTextSplitter), embedding, Pinecone upsert
- `crawler.py` - Web crawler using Playwright to render JavaScript pages, extract text with BeautifulSoup

**Routers** (`app/routers/`):
- `auth.py` - `/auth/signup`, `/auth/login`, `/auth/logout` (no CSRF on login/signup)
- `ingest.py` - `/ingest/upload` (PDF/TXT), `/ingest/crawl` (URL) - requires session + CSRF
- `chat.py` - `/chat/ask`, `/chat/reset` - requires session + CSRF
- `admin.py` - `/admin/logout` - full logout with Pinecone namespace cleanup - requires session + CSRF

### Frontend (`frontend/`)

**App structure** (Next.js 15 App Router):
- `app/page.tsx` - Home/login page
- `app/dashboard/page.tsx` - Protected dashboard with upload and chat
- `app/layout.tsx` - Root layout with ThemeProvider

**Components:**
- `components/ui/*` - shadcn/ui components (auto-generated, do not manually edit)
- `components/auth-form.tsx` - Login/signup form
- `components/upload-section.tsx` - File upload + URL indexing UI
- `components/chat-section.tsx` - RAG chat interface

**Library code** (`lib/`):
- `lib/api.ts` - **CRITICAL:** API client with `credentials: "include"` and CSRF header injection
- `lib/auth.ts` - Auth utilities using cookie-based session detection
- `lib/utils.ts` - Helper functions including `getCookie()` and `getCSRFToken()`

## Security Architecture (CRITICAL)

### Authentication Flow

**This project does NOT use localStorage or Authorization headers**. All authentication uses HttpOnly cookies:

1. **Login/Signup:**
   - Backend validates credentials → creates session → sets cookies
   - `sid` cookie (HttpOnly, Secure, SameSite=Lax) - session ID
   - `XSRF-TOKEN` cookie (Secure, SameSite=Lax) - CSRF token (not HttpOnly so JS can read)

2. **Authenticated Requests:**
   - Browser automatically sends cookies
   - Frontend reads `XSRF-TOKEN` cookie and sends in `X-CSRF-Token` header
   - Backend validates session (from `sid` cookie) AND CSRF (cookie == header)

3. **Logout:**
   - Backend deletes session, clears Pinecone namespace, clears cookies

### Key Security Rules

- **Never use localStorage** for tokens - it's vulnerable to XSS
- **Always use `credentials: "include"`** in frontend fetch calls (see `lib/api.ts`)
- **Always send CSRF header** on POST/PUT/PATCH/DELETE (see `lib/api.ts` `getHeaders()`)
- **Session cookies are HttpOnly** - JavaScript cannot access them (XSS protection)
- **CSRF validation** uses double-submit cookie pattern (see `security.py` `validate_csrf()`)
- **Pinecone namespace = user_id** - ensures data isolation between users

### Important Files for Security

- `backend/app/security.py` - Core auth logic (read this first)
- `backend/app/session_store.py` - Session management (migrate to Redis in prod)
- `backend/app/main.py` - Security headers middleware
- `frontend/lib/api.ts` - Client-side auth integration
- `SECURITY.md` - Complete security documentation
- `frontend/INTEGRATION.md` - Details on cookie-based auth integration

## Testing & Validation

**Backend:**
- No automated tests yet - add tests in `backend/tests/` using pytest
- Test security flows manually: login → upload → chat → logout
- Use `curl` to verify CSRF protection (requests without CSRF header should fail with 403)

**Frontend:**
- Run `pnpm lint` before committing
- Manual testing: verify cookies in DevTools (Application > Cookies)
- Check Network tab for `credentials: "include"` and `X-CSRF-Token` header

**End-to-end flow to validate:**
1. Start backend + frontend
2. Create account → verify `sid` (HttpOnly) and `XSRF-TOKEN` cookies are set
3. Upload document → verify CSRF header is sent
4. Ask question → verify answer with sources
5. Logout → verify cookies are cleared and namespace is deleted from Pinecone

## Common Development Tasks

### Adding a new protected endpoint

1. Add route in appropriate router (e.g., `routers/chat.py`)
2. Use `require_auth(request)` dependency to validate session + CSRF
3. Extract `user_id` from dependency return value
4. Use `user_id` as namespace for Pinecone operations

Example:
```python
from fastapi import APIRouter, Request, Depends
from ..security import require_auth

@router.post("/my-endpoint")
def my_endpoint(request: Request, user_id: str = Depends(require_auth)):
    # user_id is validated, CSRF is validated
    # Use user_id as namespace for data isolation
    ...
```

### Adding a new frontend API call

1. Add method to `ApiClient` in `lib/api.ts`
2. Use `fetchWithCredentials()` helper (includes `credentials: "include"`)
3. For POST/PUT/PATCH/DELETE, use `getHeaders(includeCSRF: true)`

Example:
```typescript
async myApiCall(data: any) {
  const response = await this.fetchWithCredentials(
    `${this.baseUrl}/my-endpoint`,
    {
      method: "POST",
      headers: this.getHeaders(true), // true = include CSRF
      body: JSON.stringify(data),
    }
  )
  return response.json()
}
```

### Modifying RAG behavior

- **Chunking:** Edit `ingestion.py` `_chunks()` - uses RecursiveCharacterTextSplitter
- **Retrieval:** Edit `rag.py` `get_retriever()` - currently uses MMR with k=5
- **Prompt:** Edit `rag.py` `_PROMPT` - system message for LLM
- **LLM model:** Edit `rag.py` `answer()` - currently uses gpt-4o-mini

### Adding shadcn/ui components

Use the shadcn CLI:
```bash
cd frontend
npx shadcn@latest add [component-name]
```

Components are added to `components/ui/` and should not be manually edited.

## Production Deployment Checklist

### Critical

- [ ] Migrate session store from in-memory dict to Redis (see `session_store.py`)
- [ ] Set `secure=True` on all cookies (already done, but verify for HTTP dev)
- [ ] Update CORS origins in `main.py` to production domains (remove localhost)
- [ ] Use strong `JWT_SECRET` in production .env
- [ ] Enable HTTPS only (cookies require Secure flag)
- [ ] Add rate limiting (e.g., slowapi)
- [ ] Set up proper logging (replace print statements)
- [ ] Configure production Pinecone index and verify region

### Recommended

- [ ] Add health checks beyond `/health` endpoint
- [ ] Implement session cleanup worker (delete expired sessions)
- [ ] Add monitoring (Sentry, Datadog)
- [ ] Implement "logout all sessions" functionality
- [ ] Add password reset flow
- [ ] Consider 2FA (TOTP)

## Known Limitations

- **Session store is in-memory** - sessions lost on server restart, doesn't scale horizontally. Migrate to Redis for production.
- **No automated tests** - add pytest tests for backend, React Testing Library for frontend.
- **Crawler is synchronous** - for large-scale crawling, consider async crawler or queue-based processing.
- **No session cleanup worker** - expired sessions remain in memory until accessed. Add cleanup task for Redis in prod.

## Documentation References

- `README.md` - Project overview, setup, and features
- `SECURITY.md` - Detailed security documentation and threat model
- `AGENTS.md` - Repository guidelines (overlaps with this file)
- `CHANGELOG.md` - Version history
- `frontend/INTEGRATION.md` - Cookie-based auth integration details
- `frontend/README.md` - Frontend-specific documentation

## Tips for Working in This Codebase

- **Security first:** Any auth/session changes require reviewing `SECURITY.md` and testing the full flow
- **Namespace isolation:** Always use `user_id` as Pinecone namespace to prevent data leakage
- **Cookie mechanics:** Remember that `sid` is HttpOnly (backend only) and `XSRF-TOKEN` is readable by JS
- **LangChain patterns:** Uses retriever → prompt → LLM flow with MMR search for diversity
- **Next.js 15:** Uses App Router with Server Components - keep client interactivity in Client Components
- **Type safety:** Backend uses Pydantic schemas, frontend uses TypeScript - leverage type checking
