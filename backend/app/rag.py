"""
RAG (Retrieval-Augmented Generation) module with Hybrid Search.

Features:
- Hybrid Search: Combines semantic (vector) + keyword (full-text) search
- Embedding Cache: Reduces OpenAI API calls for repeated queries
- MMR Fallback: Uses Maximal Marginal Relevance if hybrid unavailable
- Chat History: Maintains conversation context
"""
import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from .pgvector_store import search_documents, get_vector_store
from .config import settings
from typing import List, Optional

logger = logging.getLogger(__name__)

# System prompt for the RAG assistant
_SYSTEM_PROMPT = """You are a helpful assistant that answers questions based on the provided context from the user's documents.

Rules:
1. Only answer based on the provided context. Do not make up information.
2. If the context doesn't contain enough information to answer, say so clearly and suggest indexing more documents.
3. Keep your answers concise and relevant.
4. When referencing information, mention the source.
5. Maintain conversation context - remember what was discussed earlier in this conversation.
6. If the user asks a follow-up question, use the conversation history to understand the context.

Context from documents:
{context}"""

_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{question}")
])


def _format_docs(docs):
    """Format retrieved documents into context string"""
    parts = []
    for d in docs:
        src = d.metadata.get("source", "")
        txt = d.page_content[:500] + ("…" if len(d.page_content) > 500 else "")
        parts.append(f"- {txt}\n  Source: {src}")
    return "\n\n".join(parts) if parts else "No relevant documents found."


def _convert_chat_history(chat_history: Optional[List[dict]]) -> list:
    """Convert chat history from API format to LangChain message format"""
    if not chat_history:
        return []

    messages = []
    for msg in chat_history:
        if msg.get("role") == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg.get("role") == "assistant":
            messages.append(AIMessage(content=msg["content"]))

    # Limit history to last 10 messages to avoid token limits
    return messages[-10:]


def get_retriever(user_id: str):
    """Get retriever for user's document collection (legacy MMR-only).

    Note: For new code, prefer using search_documents() directly for hybrid search.
    """
    vs = get_vector_store(user_id)
    # MMR improves diversity; k is number of results
    return vs.as_retriever(
        search_type="mmr",
        search_kwargs={"k": settings.TOP_K, "fetch_k": 25, "lambda_mult": 0.5}
    )


def answer(question: str, user_id: str, chat_history: Optional[List[dict]] = None) -> dict:
    """
    Answer a question using RAG with HYBRID SEARCH and conversation memory.

    Pipeline:
    1. Hybrid Search (semantic + keyword with RRF)
    2. Format context with sources
    3. Generate answer with chat history

    Args:
        question: The user's question
        user_id: User ID for document isolation
        chat_history: Optional list of previous messages [{role, content}, ...]

    Returns:
        dict with answer and sources
    """
    # Get relevant documents using HYBRID SEARCH (semantic + keyword)
    # This uses embedding cache internally to reduce API calls
    # Hybrid search is controlled by ENABLE_HYBRID_SEARCH setting
    docs = search_documents(
        query=question,
        user_id=user_id,
        top_k=settings.TOP_K,
        # use_hybrid defaults to settings.ENABLE_HYBRID_SEARCH
    )

    logger.debug(f"Retrieved {len(docs)} documents for query: {question[:50]}...")

    # Format context from documents
    ctx = _format_docs(docs)

    # Convert chat history to LangChain format
    history_messages = _convert_chat_history(chat_history)

    # Create LLM and generate response
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.1,  # Slight temperature for more natural responses
        api_key=settings.OPENAI_API_KEY
    )

    # Format prompt with context and history
    prompt_messages = _PROMPT.format_messages(
        context=ctx,
        chat_history=history_messages,
        question=question
    )

    out = llm.invoke(prompt_messages)

    # Extract sources from retrieved documents
    sources = []
    seen = set()
    for d in docs:
        src = d.metadata.get("source", "")
        if src and src not in seen:
            preview = d.page_content[:200].strip()
            if len(d.page_content) > 200:
                preview += "..."

            sources.append({
                "url": src,
                "preview": preview
            })
            seen.add(src)

    return {"answer": out.content, "sources": sources}
