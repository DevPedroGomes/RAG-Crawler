from typing import List, Dict
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from .config import settings
from .pinecone_client import get_index
import hashlib
from PyPDF2 import PdfReader

def _chunks(text: str):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP, add_start_index=True
    )
    return splitter.split_text(text)

def _hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def _to_vectors(text: str, source: str) -> List[Dict]:
    out = []
    for ch in _chunks(text):
        id_ = _hash(source + ch)
        out.append({"id": id_, "values": None, "metadata": {"source": source, "text": ch}})
    return out

def embed_and_upsert(vectors: List[Dict], namespace: str):
    if not vectors:
        return
    texts = [v["metadata"]["text"] for v in vectors]
    emb = OpenAIEmbeddings(model=settings.EMBEDDING_MODEL, api_key=settings.OPENAI_API_KEY)
    embs = emb.embed_documents(texts)
    for v, e in zip(vectors, embs):
        v["values"] = e
    index = get_index()
    index.upsert(vectors=vectors, namespace=namespace)

def ingest_pdf(file_path: str, source: str, namespace: str):
    reader = PdfReader(file_path)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    vectors = _to_vectors(text, source)
    embed_and_upsert(vectors, namespace)

def ingest_txt(text: str, source: str, namespace: str):
    vectors = _to_vectors(text, source)
    embed_and_upsert(vectors, namespace)
