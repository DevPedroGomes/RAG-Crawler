"""
RAG (Retrieval-Augmented Generation) module with Hybrid Search.

Features:
- Hybrid Search: Combines semantic (vector) + keyword (full-text) search
- Embedding Cache: Reduces OpenAI API calls for repeated queries
- MMR Fallback: Uses Maximal Marginal Relevance if hybrid unavailable
- Chat History: Maintains conversation context
- Graceful degradation when OpenAI is unavailable
"""
import logging
from functools import lru_cache
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from openai import APIError, APIConnectionError, RateLimitError, APITimeoutError
from .pgvector_store import search_documents, get_vector_store
from .config import settings
from typing import List, Optional

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_llm() -> ChatOpenAI:
    """Get cached LLM instance (singleton)."""
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.1,
        api_key=settings.OPENAI_API_KEY
    )

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
        parts.append(f"- {d.page_content}\n  Source: {src}")
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


def _extract_sources(docs) -> list:
    """Extract unique sources from retrieved documents."""
    sources = []
    seen = set()
    for d in docs:
        src = d.metadata.get("source", "")
        if src and src not in seen:
            preview = d.page_content[:200].strip()
            if len(d.page_content) > 200:
                preview += "..."
            sources.append({"url": src, "preview": preview})
            seen.add(src)
    return sources


def _retrieve_docs(question: str, user_id: str):
    """Retrieve documents using hybrid search. Returns (docs, error_dict_or_none)."""
    try:
        docs = search_documents(
            query=question,
            user_id=user_id,
            top_k=settings.TOP_K,
        )
        return docs, None
    except (APIConnectionError, APITimeoutError) as e:
        logger.error(f"OpenAI embedding search failed: {e}")
        return [], {
            "answer": "I'm unable to search your documents right now because the AI service is temporarily unavailable. Please try again in a moment.",
            "sources": [],
        }
    except RateLimitError as e:
        logger.warning(f"OpenAI rate limit hit during search: {e}")
        return [], {
            "answer": "The AI service is currently rate-limited. Please wait a moment and try again.",
            "sources": [],
        }


def answer(question: str, user_id: str, chat_history: Optional[List[dict]] = None) -> dict:
    """Answer a question using RAG (non-streaming)."""
    docs, err = _retrieve_docs(question, user_id)
    if err:
        return err

    logger.debug(f"Retrieved {len(docs)} documents for query: {question[:50]}...")

    ctx = _format_docs(docs)
    history_messages = _convert_chat_history(chat_history)
    llm = _get_llm()
    prompt_messages = _PROMPT.format_messages(
        context=ctx, chat_history=history_messages, question=question
    )

    try:
        out = llm.invoke(prompt_messages)
    except RateLimitError as e:
        logger.warning(f"OpenAI rate limit hit during LLM call: {e}")
        return {"answer": "The AI service is currently rate-limited. Please wait a moment and try again.", "sources": []}
    except (APIConnectionError, APITimeoutError) as e:
        logger.error(f"OpenAI LLM unavailable: {e}")
        return {"answer": "The AI service is temporarily unavailable. Please try again in a moment.", "sources": []}
    except APIError as e:
        logger.error(f"OpenAI API error: {e}")
        return {"answer": "An error occurred while generating the response. Please try again.", "sources": []}

    return {"answer": out.content, "sources": _extract_sources(docs)}


def answer_stream(question: str, user_id: str, chat_history: Optional[List[dict]] = None):
    """
    Stream an answer using SSE events.

    Yields SSE-formatted strings:
      event: sources  -> JSON array of source objects
      event: token    -> text chunk from LLM
      event: done     -> signals completion
      event: error    -> error message
    """
    import json

    docs, err = _retrieve_docs(question, user_id)
    if err:
        yield f"event: error\ndata: {json.dumps({'message': err['answer']})}\n\n"
        return

    sources = _extract_sources(docs)
    yield f"event: sources\ndata: {json.dumps(sources)}\n\n"

    ctx = _format_docs(docs)
    history_messages = _convert_chat_history(chat_history)
    llm = _get_llm()
    prompt_messages = _PROMPT.format_messages(
        context=ctx, chat_history=history_messages, question=question
    )

    try:
        for chunk in llm.stream(prompt_messages):
            if chunk.content:
                yield f"event: token\ndata: {json.dumps({'text': chunk.content})}\n\n"
    except RateLimitError:
        yield f"event: error\ndata: {json.dumps({'message': 'The AI service is currently rate-limited.'})}\n\n"
        return
    except (APIConnectionError, APITimeoutError):
        yield f"event: error\ndata: {json.dumps({'message': 'The AI service is temporarily unavailable.'})}\n\n"
        return
    except APIError:
        yield f"event: error\ndata: {json.dumps({'message': 'An error occurred while generating the response.'})}\n\n"
        return

    yield f"event: done\ndata: {{}}\n\n"
