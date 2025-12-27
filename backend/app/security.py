"""
Security module - Autenticação com sessões seguras

Implementa:
- Hash de senhas com bcrypt
- Sessões opacas em cookies HttpOnly
- Proteção CSRF
- Validação de sessão
"""

from typing import Optional
from passlib.context import CryptContext
from fastapi import Request, HTTPException, Response
from .session_store import create_session, get_session, delete_session, refresh_session

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configurações de segurança
COOKIE_MAX_AGE = 7200  # 2 horas
SESSION_TTL = 7200  # 2 horas

def hash_password(password: str) -> str:
    """Hash de senha com bcrypt"""
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    """Verifica senha contra hash"""
    return pwd_context.verify(password, hashed)

def create_auth_response(response: Response, user_id: str):
    """
    Cria cookies de autenticação seguros

    Args:
        response: FastAPI Response object
        user_id: ID do usuário autenticado
    """
    sid, csrf_token = create_session(user_id, ttl=SESSION_TTL)

    # Cookie de sessão - HttpOnly (JavaScript não acessa)
    response.set_cookie(
        key="sid",
        value=sid,
        httponly=True,  # Proteção XSS
        secure=True,     # HTTPS only (desabilite em dev se necessário)
        samesite="lax",  # Proteção CSRF
        path="/",
        max_age=COOKIE_MAX_AGE
    )

    # Cookie CSRF - NÃO HttpOnly (JavaScript precisa ler)
    response.set_cookie(
        key="XSRF-TOKEN",
        value=csrf_token,
        httponly=False,  # JavaScript precisa ler
        secure=True,
        samesite="lax",
        path="/",
        max_age=COOKIE_MAX_AGE
    )

def clear_auth_cookies(response: Response):
    """
    Remove cookies de autenticação

    Args:
        response: FastAPI Response object
    """
    response.set_cookie(
        key="sid",
        value="",
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
        max_age=0
    )
    response.set_cookie(
        key="XSRF-TOKEN",
        value="",
        httponly=False,
        secure=True,
        samesite="lax",
        path="/",
        max_age=0
    )

def validate_session(request: Request) -> str:
    """
    Valida sessão do usuário

    Args:
        request: FastAPI Request object

    Returns:
        user_id se válido

    Raises:
        HTTPException 401 se sessão inválida
    """
    sid = request.cookies.get("sid")

    if not sid:
        raise HTTPException(401, "Sessão não encontrada")

    session = get_session(sid)

    if not session:
        raise HTTPException(401, "Sessão inválida ou expirada")

    # Renovar sessão (sliding window)
    refresh_session(sid, ttl=SESSION_TTL)

    return session["user_id"]

def validate_csrf(request: Request):
    """
    Valida token CSRF para métodos mutáveis

    Args:
        request: FastAPI Request object

    Raises:
        HTTPException 403 se CSRF inválido
    """
    # CSRF só é necessário para métodos que modificam dados
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return

    # Token do cookie
    csrf_cookie = request.cookies.get("XSRF-TOKEN")

    # Token do header
    csrf_header = request.headers.get("X-CSRF-Token")

    if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
        raise HTTPException(403, "CSRF token inválido")

def require_auth(request: Request) -> str:
    """
    Dependency para rotas protegidas
    Valida sessão E CSRF

    Args:
        request: FastAPI Request object

    Returns:
        user_id se autenticado

    Raises:
        HTTPException se não autenticado ou CSRF inválido
    """
    # Validar CSRF primeiro
    validate_csrf(request)

    # Validar sessão
    user_id = validate_session(request)

    return user_id

def logout_user(request: Request, response: Response):
    """
    Faz logout do usuário

    Args:
        request: FastAPI Request object
        response: FastAPI Response object
    """
    sid = request.cookies.get("sid")

    if sid:
        # Remover sessão do store
        delete_session(sid)

    # Limpar cookies
    clear_auth_cookies(response)
