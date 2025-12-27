from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, Depends
from ..security import require_auth
from ..ingestion import ingest_pdf, ingest_txt, embed_and_upsert, _to_vectors
from ..crawler import render_urls
import tempfile
import os
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/ingest", tags=["ingest"])
limiter = Limiter(key_func=get_remote_address)

@router.post("/upload")
@limiter.limit("10/hour")
async def upload(
    request: Request,
    file: UploadFile = File(...),
    user_id: str = Depends(require_auth)
):
    """
    Upload e indexação de documento

    Requer autenticação via cookie de sessão e CSRF token
    """
    ext = (file.filename or "").lower()

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        path = tmp.name

    try:
        if ext.endswith(".pdf"):
            ingest_pdf(path, source=file.filename or "document.pdf", namespace=user_id)
        else:
            text = content.decode("utf-8", errors="ignore")
            ingest_txt(text, source=file.filename or "document.txt", namespace=user_id)

        return {"ok": True, "message": f"Documento '{file.filename}' indexado com sucesso"}
    except Exception as e:
        raise HTTPException(500, f"Erro ao processar documento: {str(e)}")
    finally:
        os.unlink(path)

@router.post("/crawl")
@limiter.limit("10/hour")
async def crawl(
    request: Request,
    url: str = Form(...),
    user_id: str = Depends(require_auth)
):
    """
    Indexação de URL via crawler

    Requer autenticação via cookie de sessão e CSRF token
    """
    try:
        docs = await render_urls([url])
        text = "\n".join(d["page_content"] for d in docs)

        if not text.strip():
            raise HTTPException(400, "Não foi possível extrair conteúdo da URL")

        vectors = _to_vectors(text, source=url)
        embed_and_upsert(vectors, namespace=user_id)

        return {"ok": True, "message": f"URL '{url}' indexada com sucesso", "url": url}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Erro ao indexar URL: {str(e)}")
