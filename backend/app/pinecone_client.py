from pinecone import Pinecone, ServerlessSpec
from .config import settings

_pc = None
_index = None

def get_pc() -> Pinecone:
    global _pc
    if _pc is None:
        _pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    return _pc

def ensure_index(dimension: int = 1536, metric: str = "cosine"):
    """
    Cria (se necessário) e retorna host do index serverless.
    """
    pc = get_pc()
    name = settings.PINECONE_INDEX_NAME
    if settings.PINECONE_INDEX_HOST:
        return settings.PINECONE_INDEX_HOST

    # cria se não existe
    existing = [i["name"] for i in pc.list_indexes()]
    if name not in existing:
        # ajuste cloud/region conforme sua conta
        pc.create_index(
            name=name,
            dimension=dimension,
            metric=metric,
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
    # busca host
    desc = pc.describe_index(name)
    return desc["host"]

def get_index():
    global _index
    if _index is None:
        pc = get_pc()
        host = settings.PINECONE_INDEX_HOST or ensure_index(1536, "cosine")
        _index = pc.Index(host=host)
    return _index

def delete_namespace(namespace: str):
    idx = get_index()
    # API moderna: apagar NAMESPACE inteiro
    idx.delete(delete_all=True, namespace=namespace)
