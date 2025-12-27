from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import User
from ..schemas import SignUpIn
from ..security import hash_password, verify_password, create_auth_response, clear_auth_cookies, logout_user
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/signup")
@limiter.limit("5/hour")
def signup(request: Request, body: SignUpIn, response: Response, db: Session = Depends(get_db)):
    """
    Cria nova conta de usuário

    Retorna cookies HttpOnly:
    - sid: Session ID (HttpOnly, Secure, SameSite=Lax)
    - XSRF-TOKEN: Token CSRF (Secure, SameSite=Lax)
    """
    # Verificar se email já existe
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(400, "E-mail já cadastrado")

    # Criar usuário
    u = User(email=body.email, password_hash=hash_password(body.password))
    db.add(u)
    db.commit()
    db.refresh(u)

    # Criar cookies de autenticação
    create_auth_response(response, str(u.id))

    return {"ok": True, "message": "Conta criada com sucesso"}

@router.post("/login")
@limiter.limit("10/hour")
def login(request: Request, body: SignUpIn, response: Response, db: Session = Depends(get_db)):
    """
    Faz login do usuário

    Retorna cookies HttpOnly:
    - sid: Session ID (HttpOnly, Secure, SameSite=Lax)
    - XSRF-TOKEN: Token CSRF (Secure, SameSite=Lax)
    """
    # Buscar usuário
    u = db.query(User).filter(User.email == body.email).first()

    if not u or not verify_password(body.password, u.password_hash):
        raise HTTPException(401, "Credenciais inválidas")

    # Criar cookies de autenticação
    create_auth_response(response, str(u.id))

    return {"ok": True, "message": "Login realizado com sucesso"}

@router.post("/logout")
def logout(response: Response):
    """
    Faz logout do usuário

    Remove cookies de autenticação
    """
    clear_auth_cookies(response)
    return {"ok": True, "message": "Logout realizado com sucesso"}
