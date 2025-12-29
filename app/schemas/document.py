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
    document_id: int = Field(..., description="ID of the document to use as context")
    query: str = Field(..., min_length=1, description="User query for the chatbot")


class ChatQueryResponse(BaseModel):
    """Schema for chatbot response"""
    document_id: int
    document_title: str
    user_query: str
    chatbot_response: str
    timestamp: datetime


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
