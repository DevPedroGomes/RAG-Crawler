import os
import time
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .config import settings
from .database import Base, engine
from .routers import auth, ingest, chat, admin, jobs, analysis
from .background import start_background_tasks, stop_background_tasks
from .crawler import BrowserPool
from .pgvector_store import init_pgvector

# Configure logging — JSON in production, plaintext in dev
if settings.ENVIRONMENT == "production":
    from pythonjsonlogger import jsonlogger
    handler = logging.StreamHandler()
    handler.setFormatter(jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level"},
    ))
    logging.root.handlers = [handler]
    logging.root.setLevel(getattr(logging, settings.LOG_LEVEL))
else:
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
logger = logging.getLogger(__name__)

# Cria as tabelas do banco de dados
Base.metadata.create_all(bind=engine)

# Configurar rate limiter
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle:
    - Startup: Initialize pgvector, start background tasks
    - Shutdown: Stop background tasks, close browser pool
    """
    # Startup
    logger.info("Starting application...")

    logger.info("Initializing pgvector extension and indexes...")
    init_pgvector()

    logger.info("Starting background tasks...")
    start_background_tasks()

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down application...")

    logger.info("Stopping background tasks...")
    stop_background_tasks()

    logger.info("Closing browser pool...")
    await BrowserPool.close()

    logger.info("Application shutdown complete")

app = FastAPI(
    title="PG Multiuser RAG",
    description="Sistema RAG multiusuário com autenticação via Clerk JWT",
    lifespan=lifespan
)

# Adicionar rate limiter ao app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configurar CORS para Clerk JWT auth
cors_origins = ["https://ragcrawler.pgdev.com.br"]
# Dev/extra origins via env var (comma-separated), e.g. CORS_ORIGINS=http://localhost:3000,http://localhost:5173
extra_origins = os.environ.get("CORS_ORIGINS", "")
if extra_origins:
    cors_origins.extend([o.strip() for o in extra_origins.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],  # Bearer token
    expose_headers=[],
)

# Middleware de segurança - Headers de proteção
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)

    # Content Security Policy — strict for API-only backend
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; "
        "frame-ancestors 'none';"
    )

    # Proteção contra clickjacking
    response.headers["X-Frame-Options"] = "DENY"

    # Proteção contra MIME sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"

    # XSS Protection (legacy mas ainda útil)
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Referrer Policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Permissions Policy
    response.headers["Permissions-Policy"] = (
        "accelerometer=(), camera=(), geolocation=(), "
        "gyroscope=(), magnetometer=(), microphone=(), "
        "payment=(), usb=()"
    )

    return response

# Middleware de logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000

    # Skip logging health checks to reduce noise
    if request.url.path != "/health":
        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round(duration_ms, 1),
                "client_ip": request.client.host if request.client else None,
            },
        )

    return response

# Handler de erros global
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log the error internally
    logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}", exc_info=True)

    # Don't expose error details in production
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Incluir routers
app.include_router(auth.router)
app.include_router(ingest.router)
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(jobs.router)
app.include_router(analysis.router)

@app.get("/health")
def health():
    """
    Health check endpoint.
    Returns status of all dependencies.
    """
    from redis import Redis
    from sqlalchemy import text

    health_status = {
        "status": "healthy",
        "checks": {}
    }

    # Check PostgreSQL
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"

    # Check Redis
    try:
        redis_conn = Redis.from_url(settings.REDIS_URL)
        redis_conn.ping()
        health_status["checks"]["redis"] = "ok"
    except Exception as e:
        health_status["checks"]["redis"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"

    # Check RQ Worker status
    try:
        from rq import Queue
        redis_conn = Redis.from_url(settings.REDIS_URL)
        q = Queue('default', connection=redis_conn)
        workers = q.workers
        health_status["checks"]["worker"] = {
            "active_workers": len(workers),
            "queued_jobs": q.count,
            "failed_jobs": q.failed_job_registry.count,
        }
        if len(workers) == 0:
            health_status["checks"]["worker"]["warning"] = "no active workers"
    except Exception as e:
        health_status["checks"]["worker"] = f"error: {str(e)}"

    # Check OpenAI API key is configured
    health_status["checks"]["openai_configured"] = "ok" if settings.OPENAI_API_KEY else "not configured"

    if health_status["status"] == "unhealthy":
        return JSONResponse(status_code=503, content=health_status)
    return health_status

@app.get("/")
def root():
    """Endpoint raiz"""
    return {
        "message": "PG Multiuser RAG API",
        "version": "3.0.0",
        "auth": "Clerk JWT"
    }
