from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from .config import settings
from .pgvector_store import get_vector_store
from PyPDF2 import PdfReader


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


def embed_and_store(documents: List[Document], user_id: str):
    """Embed documents and store in PGVector."""
    if not documents:
        return
    vs = get_vector_store(user_id)
    vs.add_documents(documents)


def ingest_pdf(file_path: str, source: str, user_id: str):
    """Ingest a PDF file into the vector store."""
    reader = PdfReader(file_path)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    documents = _to_documents(text, source)
    embed_and_store(documents, user_id)


def ingest_txt(text: str, source: str, user_id: str):
    """Ingest plain text into the vector store."""
    documents = _to_documents(text, source)
    embed_and_store(documents, user_id)
