from fastapi import APIRouter, HTTPException, Body, Request, Depends
from ..security import require_auth
from ..schemas import ChatIn
from ..rag import answer
from ..pinecone_client import delete_namespace
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/chat", tags=["chat"])
limiter = Limiter(key_func=get_remote_address)

@router.post("/ask")
@limiter.limit("20/minute")
def ask(
    request: Request,
    payload: ChatIn = Body(...),
    user_id: str = Depends(require_auth)
):
    """
    Faz pergunta ao RAG usando documentos indexados do usuário

    Requer autenticação via cookie de sessão e CSRF token
    """
    try:
        result = answer(payload.question, namespace=user_id)
        return result
    except Exception as e:
        raise HTTPException(500, f"Erro ao processar pergunta: {str(e)}")

@router.post("/reset")
def reset(
    request: Request,
    user_id: str = Depends(require_auth)
):
    """
    Limpa todos os documentos indexados do usuário

    Requer autenticação via cookie de sessão e CSRF token
    """
    try:
        delete_namespace(user_id)
        return {"ok": True, "message": "Índice limpo com sucesso"}
    except Exception as e:
        raise HTTPException(500, f"Erro ao limpar índice: {str(e)}")
