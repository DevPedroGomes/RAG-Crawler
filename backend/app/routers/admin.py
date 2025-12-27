from fastapi import APIRouter, HTTPException, Request, Response, Depends
from ..security import require_auth, clear_auth_cookies
from ..pinecone_client import delete_namespace
from ..session_store import delete_session

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    user_id: str = Depends(require_auth)
):
    """
    Faz logout completo: limpa sessão, cookies e namespace do Pinecone

    Requer autenticação via cookie de sessão e CSRF token
    """
    try:
        # Deletar namespace do Pinecone
        delete_namespace(user_id)

        # Deletar sessão
        sid = request.cookies.get("sid")
        if sid:
            delete_session(sid)

        # Limpar cookies
        clear_auth_cookies(response)

        return {"ok": True, "message": "Logout realizado e dados removidos"}
    except Exception as e:
        # Mesmo com erro, limpar cookies
        clear_auth_cookies(response)
        raise HTTPException(500, f"Erro ao fazer logout: {str(e)}")
