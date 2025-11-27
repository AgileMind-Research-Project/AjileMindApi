"""
Document Chat Schemas

Pydantic schemas for document upload, chat queries, and responses.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================
# DOCUMENT SCHEMAS
# ============================================

class DocumentUploadResponse(BaseModel):
    """Response after document upload"""
    success: bool
    message: str
    document_id: str
    filename: str
    total_chunks: int
    total_characters: int
    processed_at: str


class DocumentListItem(BaseModel):
    """Single document in list"""
    document_id: str
    filename: str
    file_size: int
    total_chunks: int
    uploaded_by: str
    uploaded_at: datetime
    status: str  # 'processing', 'ready', 'failed'


class DocumentListResponse(BaseModel):
    """List of documents"""
    success: bool
    documents: List[DocumentListItem]
    total: int


class DocumentDeleteResponse(BaseModel):
    """Response after document deletion"""
    success: bool
    message: str
    document_id: str


# ============================================
# CHAT SCHEMAS
# ============================================

class ChatQueryRequest(BaseModel):
    """User chat query"""
    question: str = Field(..., min_length=3, max_length=1000, description="User's question")
    document_ids: Optional[List[str]] = Field(None, description="Filter by specific documents (optional)")
    top_k: Optional[int] = Field(5, ge=1, le=10, description="Number of context chunks to retrieve")


class SourceReference(BaseModel):
    """Source document reference"""
    filename: str
    chunk_index: int
    relevance_score: float


class ChatQueryResponse(BaseModel):
    """LLM response with sources"""
    success: bool
    question: str
    answer: str
    sources: List[SourceReference]
    model: str
    has_context: bool
    response_time_ms: float


class ChatHistoryItem(BaseModel):
    """Single chat history item"""
    chat_id: str
    question: str
    answer: str
    sources: List[Dict[str, Any]]
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    """Chat history for a tenant"""
    success: bool
    chat_history: List[ChatHistoryItem]
    total: int


# ============================================
# STATUS SCHEMAS
# ============================================

class DocumentStats(BaseModel):
    """Statistics about document collection"""
    total_documents: int
    total_chunks: int
    total_size_bytes: int


class LLMStatus(BaseModel):
    """LLM service status"""
    status: str  # 'available', 'unavailable', 'error'
    configured_model: str
    llm_url: str
    available_models: Optional[List[str]] = None
    error: Optional[str] = None


class SystemHealthResponse(BaseModel):
    """Overall system health for document chat"""
    success: bool
    vector_db_status: str
    llm_status: LLMStatus
    document_stats: DocumentStats
