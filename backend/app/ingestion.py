import logging
from typing import List, Callable, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from sqlalchemy import text as sql_text
from .config import settings
from .pgvector_store import get_vector_store
from .database import engine
from PyPDF2 import PdfReader

ProgressCallback = Optional[Callable[[str, str], None]]

logger = logging.getLogger(__name__)


def _chunks(text: str) -> List[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        add_start_index=True
    )
    return splitter.split_text(text)


def _to_documents(text: str, source: str) -> List[Document]:
    """Convert text to LangChain Documents with metadata."""
    docs = []
    for chunk in _chunks(text):
        docs.append(Document(
            page_content=chunk,
            metadata={"source": source}
        ))
    return docs


def _cleanup_partial_source(user_id: str, source: str):
    """Remove partially indexed chunks for a source if ingestion fails mid-way."""
    collection_name = f"user_{user_id}"
    try:
        with engine.connect() as conn:
            conn.execute(
                sql_text("""
                    DELETE FROM langchain_pg_embedding
                    WHERE collection_id IN (
                        SELECT uuid FROM langchain_pg_collection WHERE name = :coll
                    )
                    AND cmetadata->>'source' = :source
                """),
                {"coll": collection_name, "source": source}
            )
            conn.commit()
            logger.info(f"Cleaned up partial chunks for source '{source}' user {user_id}")
    except Exception as cleanup_err:
        logger.error(f"Failed to cleanup partial chunks: {cleanup_err}")


def embed_and_store(documents: List[Document], user_id: str, source: str = ""):
    """Embed documents and store in PGVector. Cleans up on failure."""
    if not documents:
        return
    vs = get_vector_store(user_id)
    try:
        vs.add_documents(documents)
    except Exception:
        logger.error(f"Embedding failed for source '{source}', cleaning up partial data")
        _cleanup_partial_source(user_id, source)
        raise


def ingest_pdf(file_path: str, source: str, user_id: str):
    """Ingest a PDF file into the vector store."""
    reader = PdfReader(file_path)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    documents = _to_documents(text, source)
    embed_and_store(documents, user_id, source=source)


def ingest_txt(text: str, source: str, user_id: str):
    """Ingest plain text into the vector store."""
    documents = _to_documents(text, source)
    embed_and_store(documents, user_id, source=source)


def ingest_pdf_with_progress(
    file_path: str, source: str, user_id: str, on_progress: ProgressCallback = None,
) -> dict:
    """Ingest a PDF with progress callbacks for pipeline visibility."""
    reader = PdfReader(file_path)
    page_count = len(reader.pages)
    if on_progress:
        on_progress("extracting", f"Extracting text from {page_count} pages")

    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    word_count = len(text.split())
    if on_progress:
        on_progress("extracted", f"{word_count} words from {page_count} pages")

    documents = _to_documents(text, source)
    chunk_count = len(documents)
    if on_progress:
        on_progress("chunking", f"Split into {chunk_count} chunks ({settings.CHUNK_SIZE} chars, {settings.CHUNK_OVERLAP} overlap)")

    if on_progress:
        on_progress("embedding", f"Generating embeddings for {chunk_count} chunks")
    embed_and_store(documents, user_id, source=source)
    if on_progress:
        on_progress("stored", f"Stored {chunk_count} vectors in HNSW index")

    return {"words": word_count, "chunks": chunk_count, "pages": page_count}


def ingest_txt_with_progress(
    text: str, source: str, user_id: str, on_progress: ProgressCallback = None,
) -> dict:
    """Ingest plain text with progress callbacks for pipeline visibility."""
    word_count = len(text.split())
    if on_progress:
        on_progress("extracted", f"{word_count} words extracted")

    documents = _to_documents(text, source)
    chunk_count = len(documents)
    if on_progress:
        on_progress("chunking", f"Split into {chunk_count} chunks ({settings.CHUNK_SIZE} chars, {settings.CHUNK_OVERLAP} overlap)")

    if on_progress:
        on_progress("embedding", f"Generating embeddings for {chunk_count} chunks")
    embed_and_store(documents, user_id, source=source)
    if on_progress:
        on_progress("stored", f"Stored {chunk_count} vectors in HNSW index")

    return {"words": word_count, "chunks": chunk_count}
