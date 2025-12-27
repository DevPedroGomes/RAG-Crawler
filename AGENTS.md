# Repository Guidelines

## Project Structure & Module Organization
- `backend/` holds the FastAPI service. Core logic lives in `app/`, with routers split per domain in `app/routers/`, data models in `app/models.py`, and ingestion utilities (crawler, Pinecone, Playwright) in dedicated modules. Use this layout when adding features so security, ingestion, and chat code stay isolated.
- `frontend/` is the Next.js 15 client. Server components live under `app/`, reusable UI pieces in `components/`, hooks in `hooks/`, and shared helpers in `lib/`. Static assets sit in `public/`.
- Repository-wide docs (`README.md`, `SECURITY.md`, `CHANGELOG.md`) describe architecture and threat model—update them when changes impact deployment or security posture.

## Build, Test, and Development Commands
- Backend setup: `cd backend && ./setup.sh` provisions the virtualenv, installs Python deps, Playwright browsers, and copies `.env.example`. Re-run after dependency updates.
- Run backend: `cd backend && uvicorn app.main:app --reload --port 8000` launches the API with hot reload at `http://localhost:8000`.
- Frontend install: `cd frontend && pnpm install` (or `npm install`) installs packages.
- Frontend dev: `pnpm dev` serves the UI at `http://localhost:3000`; `pnpm build` creates the production bundle; `pnpm lint` runs the Next.js ESLint pipeline.

## Coding Style & Naming Conventions
- Python: follow PEP 8 with 4-space indentation, snake_case functions, and PascalCase models. Keep FastAPI routers thin and delegate to service modules. Prefer docstrings on security-critical flows (auth, session store).
- TypeScript/React: use functional components, PascalCase filenames for components, camelCase hooks/utilities, and colocate styles via Tailwind utility classes. Keep Zod schemas and API clients in `lib/` to avoid circular imports.
- Secrets belong in `.env`/`.env.local`. Never hard-code API keys or session secrets.

## Testing Guidelines
- Automated tests are not yet committed; add backend tests under `backend/tests/` using pytest or FastAPI’s TestClient for new endpoints, especially those touching auth or ingestion.
- Frontend changes should include Storybook-style manual verification plus unit tests with your preferred React testing stack when added; ensure components render with realistic mock session data.
- Always run `pnpm lint` and exercise the end-to-end flow (login → ingest → chat) locally before opening a PR.

## Commit & Pull Request Guidelines
- Use imperative, present-tense commit subjects with a scope prefix when helpful, e.g., `backend: add crawl throttling`. Keep body lines wrapped at 72 chars and reference issues as `(#123)`.
- PRs must describe the change, list manual checks (backend dev server, lint, Playwright install if relevant), and include screenshots or terminal captures for UI or CLI-facing updates.
- Highlight security-sensitive modifications in the PR description so reviewers can assess impacts on authentication, session isolation, and data privacy.
