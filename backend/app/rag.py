from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_pinecone import PineconeVectorStore
from .pinecone_client import get_index
from .config import settings

_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Você responde apenas com base no contexto. Se faltar informação, diga que não sabe e sugira indexar mais fontes. Ao final, liste as fontes (URLs)."),
    ("human", "Pergunta: {q}\n\nContexto:\n{ctx}")
])

def _format_docs(docs):
    parts = []
    for d in docs:
        src = d.metadata.get("source", "")
        txt = d.page_content[:500] + ("…" if len(d.page_content) > 500 else "")
        parts.append(f"- {txt}\nFonte: {src}")
    return "\n\n".join(parts)

def get_retriever(namespace: str):
    index = get_index()
    embeddings = OpenAIEmbeddings(model=settings.EMBEDDING_MODEL, api_key=settings.OPENAI_API_KEY)
    vs = PineconeVectorStore(index=index, embedding=embeddings, namespace=namespace)
    # MMR melhora diversidade; k pequeno para respostas curtas
    return vs.as_retriever(search_type="mmr", search_kwargs={"k": settings.TOP_K, "fetch_k": 25, "lambda_mult": 0.5})

def answer(question: str, namespace: str) -> dict:
    retr = get_retriever(namespace)
    docs = retr.get_relevant_documents(question)
    ctx = _format_docs(docs)
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=settings.OPENAI_API_KEY)
    prompt = _PROMPT.format(q=question, ctx=ctx)
    out = llm.invoke(prompt.to_messages())

    # Retornar sources como lista de objetos com url e preview
    sources = []
    seen = set()
    for d in docs:
        src = d.metadata.get("source", "")
        if src and src not in seen:
            # Preview: primeiros 200 caracteres do conteúdo
            preview = d.page_content[:200].strip()
            if len(d.page_content) > 200:
                preview += "..."

            sources.append({
                "url": src,
                "preview": preview
            })
            seen.add(src)

    return {"answer": out.content, "sources": sources}
