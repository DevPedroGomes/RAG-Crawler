"""
Pydantic Schemas

Authentication schemas removed — Better Auth manages users/sessions in the
Next.js layer; the Python backend only validates session cookies.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class CrawlIn(BaseModel):
    url: str


class ChatMessage(BaseModel):
    """A single message in the chat history"""
    role: Literal["user", "assistant"]
    content: str


class ChatIn(BaseModel):
    """Input for chat endpoint with optional conversation history"""
    question: str = Field(..., min_length=1, max_length=2000)
    chat_history: Optional[List[ChatMessage]] = Field(default_factory=list)


class DocumentCountOut(BaseModel):
    """Response for document count endpoint with limit info"""
    count: int  # Number of chunks
    has_documents: bool
    documents_used: int = 0  # Number of unique documents (sources)
    documents_limit: int = 5  # Maximum documents allowed
    can_upload: bool = True  # Whether user can upload more documents
