from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .database import Base, engine
from .routers import auth, ingest, chat, admin
import time
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from .background import start_background_tasks, stop_background_tasks
from contextlib import asynccontextmanager

# Cria as tabelas do banco de dados
Base.metadata.create_all(bind=engine)

# Configurar rate limiter
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia lifecycle da aplicação:
    - Startup: inicia background tasks
    - Shutdown: para background tasks
    """
    # Startup
    print("🚀 [Startup] Iniciando background tasks...")
    start_background_tasks()

    yield

    # Shutdown
    print("🛑 [Shutdown] Parando background tasks...")
    stop_background_tasks()

app = FastAPI(
    title="PG Multiuser RAG",
    description="Sistema RAG multiusuário com autenticação segura via cookies HttpOnly",
    lifespan=lifespan
)

# Adicionar rate limiter ao app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configurar CORS para permitir cookies
# IMPORTANTE: Em produção, especifique os origins exatos
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        # Adicione seus domínios de produção aqui
    ],
    allow_credentials=True,  # CRÍTICO para cookies
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token"],  # CSRF header
    expose_headers=["Set-Cookie"],
)

# Middleware de segurança - Headers de proteção
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)

    # Content Security Policy
    # NOTA: Ajuste conforme necessário para seu frontend
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "  # Ajuste em produção
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' http://localhost:5173 http://localhost:3000; "
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

# Middleware de logging (opcional mas útil)
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    # Log básico (em produção use logging apropriado)
    print(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.2f}s")

    return response

# Handler de erros global
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Em produção, não exponha detalhes do erro
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor"}
    )

# Incluir routers
app.include_router(auth.router)
app.include_router(ingest.router)
app.include_router(chat.router)
app.include_router(admin.router)

@app.get("/health")
def health():
    """Endpoint de health check"""
    return {"ok": True, "status": "healthy"}

@app.get("/")
def root():
    """Endpoint raiz"""
    return {
        "message": "PG Multiuser RAG API",
        "version": "2.0.0",
        "security": "Cookies HttpOnly + CSRF Protection"
    }
