"""
Document Schemas

Pydantic models for document validation and serialization.
Used for RAG-based chatbot document management.
"""

from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, List


class DocumentBase(BaseModel):
    """Base document schema"""
    doc_title: str = Field(..., min_length=1, max_length=255, description="Document title")
    doc_content: str = Field(..., min_length=1, description="Complete document content")
    uploaded_date: date = Field(..., description="Date when document was uploaded")
    category: Optional[str] = Field(None, max_length=100, description="Optional category")


class DocumentCreate(DocumentBase):
    """Schema for creating a new document"""
    pass


class DocumentUpdate(BaseModel):
    """Schema for updating document"""
    doc_title: Optional[str] = Field(None, min_length=1, max_length=255)
    doc_content: Optional[str] = Field(None, min_length=1)
    uploaded_date: Optional[date] = None
    category: Optional[str] = Field(None, max_length=100)


class DocumentResponse(DocumentBase):
    """Schema for document response"""
    id: int = Field(..., description="Document ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    is_active: bool = Field(default=True, description="Active status")
    
    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """Schema for document list item (without large content)"""
    id: int
    doc_title: str
    uploaded_date: date
    category: Optional[str]
    created_at: datetime


class DocumentContentResponse(BaseModel):
    """Schema for document content retrieval"""
    id: int
    doc_title: str
    doc_content: str
    uploaded_date: date
    category: Optional[str]
    
    model_config = {"from_attributes": True}


class DocumentDateResponse(BaseModel):
    """Schema for unique document dates"""
    uploaded_date: date = Field(..., description="Document upload date")
    count: int = Field(..., description="Number of documents on this date")


class ChatQueryRequest(BaseModel):
    """Schema for chatbot query request"""
    document_id: Optional[int] = Field(None, description="ID of the document to use as context. If None, search all documents")
    query: str = Field(..., min_length=1, description="User query for the chatbot")
    search_all: bool = Field(False, description="If True, search across all documents to find the most relevant one")


class ChatQueryResponse(BaseModel):
    """Schema for chatbot response"""
    document_id: int
    document_title: str
    user_query: str
    chatbot_response: str
    timestamp: datetime
    source_document: Optional[str] = Field(None, description="Name of the document that provided the answer (for multi-doc search)")
    relevant_sources: List['DocumentSource'] = Field(default_factory=list, description="All relevant documents with excerpts (for multi-doc search)")


class DocumentSource(BaseModel):
    """Schema for a relevant document source with excerpts"""
    document_id: int
    document_title: str
    relevance_score: float
    relevant_excerpts: List[str] = Field(default_factory=list, description="Relevant text excerpts from this document")


class MultiDocChatRequest(BaseModel):
    """Schema for chatbot query across multiple documents"""
    query: str = Field(..., min_length=1, description="User query for the chatbot")
    uploaded_date: Optional[date] = Field(None, description="Optional date filter. If None, search all dates")


class MultiDocChatResponse(BaseModel):
    """Schema for multi-document chatbot response"""
    document_id: int
    document_title: str
    user_query: str
    chatbot_response: str
    timestamp: datetime
    relevance_score: float = Field(0.0, description="Relevance score of the matched document")
    searched_documents: int = Field(0, description="Number of documents searched")
    relevant_sources: List[DocumentSource] = Field(default_factory=list, description="All relevant documents with excerpts")


class DocumentSearchRequest(BaseModel):
    """Schema for searching documents"""
    query: str = Field(..., min_length=1, description="Search query")
    uploaded_date: Optional[date] = None
    category: Optional[str] = None
    limit: int = Field(10, ge=1, le=100, description="Results limit")


class DocumentSearchResponse(BaseModel):
    """Schema for search results"""
    total: int
    results: List[DocumentListResponse]
