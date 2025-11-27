"""
Document Chat API Endpoints

Handles PDF upload, document management, and RAG-based chat queries.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import time
import json

from app.schemas.document_schemas import (
    DocumentUploadResponse,
    DocumentListResponse,
    DocumentDeleteResponse,
    ChatQueryRequest,
    ChatQueryResponse,
    ChatHistoryResponse,
    SystemHealthResponse,
    LLMStatus,
    DocumentStats
)
from app.services.document_service import DocumentService
from app.services.llm_service import LLMService
from app.services.vector_db_service import VectorDBService
from app.db.repositories.document_repository import DocumentRepository, ChatHistoryRepository
from app.db.database import db
from app.utils.jwt import get_current_user_from_token
from app.core.logger import logger

router = APIRouter()

# Initialize services
document_service = DocumentService()
llm_service = LLMService()
vector_db_service = VectorDBService()


def get_document_repo() -> DocumentRepository:
    """Dependency to get document repository"""
    return DocumentRepository(db)


def get_chat_repo() -> ChatHistoryRepository:
    """Dependency to get chat history repository"""
    return ChatHistoryRepository(db)


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload PDF Document",
    description="Upload a PDF file for processing and RAG-based chat"
)
async def upload_document(
    file: UploadFile = File(..., description="PDF file to upload"),
    current_user: Dict = Depends(get_current_user_from_token),
    doc_repo: DocumentRepository = Depends(get_document_repo)
) -> Dict[str, Any]:
    """
    Upload and process a PDF document.
    
    Steps:
    1. Validate file type (must be PDF)
    2. Extract text from PDF
    3. Chunk text into smaller pieces
    4. Generate embeddings for chunks
    5. Store in vector database
    6. Save metadata to MySQL
    
    **Authentication Required**: Bearer token in header
    
    **Returns**:
    - document_id: Unique identifier for the document
    - filename: Original filename
    - total_chunks: Number of text chunks created
    - total_characters: Total characters extracted
    """
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are supported"
            )
        
        user_id = current_user["user_id"]
        tenant_id = current_user["tenant_id"]
        
        logger.info(f"Processing PDF upload: {file.filename} for user {user_id}")
        
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Reset file pointer for processing
        await file.seek(0)
        
        # Process PDF: extract text and chunk
        processed = await document_service.process_pdf(
            file=file.file,
            filename=file.filename,
            user_id=user_id,
            tenant_id=tenant_id
        )
        
        document_id = processed["document_id"]
        chunks = processed["chunks"]
        
        # Store document metadata in MySQL
        await doc_repo.create_document(
            document_id=document_id,
            tenant_id=tenant_id,
            user_id=user_id,
            filename=file.filename,
            file_size=file_size,
            total_chunks=len(chunks),
            status="processing"
        )
        
        # Store chunks with embeddings in vector database
        await vector_db_service.store_document_chunks(
            tenant_id=tenant_id,
            document_id=document_id,
            chunks=chunks
        )
        
        # Update status to ready
        await doc_repo.update_document_status(document_id, "ready")
        
        logger.info(f"Successfully processed document {document_id}: {file.filename}")
        
        return {
            "success": True,
            "message": "Document uploaded and processed successfully",
            "document_id": document_id,
            "filename": file.filename,
            "total_chunks": len(chunks),
            "total_characters": processed["total_characters"],
            "processed_at": processed["processed_at"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document processing failed: {str(e)}"
        )


@router.get(
    "/list",
    response_model=DocumentListResponse,
    summary="List Documents",
    description="Get list of all uploaded documents for current tenant"
)
async def list_documents(
    current_user: Dict = Depends(get_current_user_from_token),
    doc_repo: DocumentRepository = Depends(get_document_repo)
) -> Dict[str, Any]:
    """
    List all documents uploaded by the current tenant.
    
    **Authentication Required**: Bearer token
    
    **Returns**: List of documents with metadata
    """
    try:
        tenant_id = current_user["tenant_id"]
        
        documents = await doc_repo.list_documents_by_tenant(tenant_id)
        
        return {
            "success": True,
            "documents": documents,
            "total": len(documents)
        }
    
    except Exception as e:
        logger.error(f"Failed to list documents: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve documents"
        )


@router.delete(
    "/{document_id}",
    response_model=DocumentDeleteResponse,
    summary="Delete Document",
    description="Delete a document and all its associated data"
)
async def delete_document(
    document_id: str,
    current_user: Dict = Depends(get_current_user_from_token),
    doc_repo: DocumentRepository = Depends(get_document_repo)
) -> Dict[str, Any]:
    """
    Delete a document from both vector database and MySQL.
    
    **Authentication Required**: Bearer token
    
    **Path Parameters**:
    - document_id: ID of document to delete
    
    **Returns**: Deletion confirmation
    """
    try:
        tenant_id = current_user["tenant_id"]
        
        # Verify document belongs to tenant
        document = await doc_repo.get_document_by_id(document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        if document["tenant_id"] != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this document"
            )
        
        # Delete from vector database
        await vector_db_service.delete_document_chunks(tenant_id, document_id)
        
        # Delete from MySQL
        await doc_repo.delete_document(document_id)
        
        logger.info(f"Document deleted: {document_id}")
        
        return {
            "success": True,
            "message": "Document deleted successfully",
            "document_id": document_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )


@router.post(
    "/chat/ask",
    response_model=ChatQueryResponse,
    summary="Ask Question",
    description="Ask a question and get an AI-generated answer based on uploaded documents (RAG)"
)
async def ask_question(
    request: ChatQueryRequest,
    current_user: Dict = Depends(get_current_user_from_token),
    chat_repo: ChatHistoryRepository = Depends(get_chat_repo)
) -> Dict[str, Any]:
    """
    Ask a question and get an answer using RAG (Retrieval-Augmented Generation).
    
    **How it works**:
    1. Convert question to embedding
    2. Search vector database for relevant document chunks
    3. Pass question + relevant chunks to LLM
    4. Return AI-generated answer with source references
    
    **Authentication Required**: Bearer token
    
    **Request Body**:
    - question: The question to ask (3-1000 characters)
    - document_ids: Optional list of document IDs to search within
    - top_k: Number of context chunks to retrieve (1-10, default: 5)
    
    **Returns**:
    - answer: AI-generated response
    - sources: List of source documents used
    - model: LLM model used
    - has_context: Whether relevant context was found
    """
    try:
        start_time = time.time()
        
        tenant_id = current_user["tenant_id"]
        user_id = current_user["user_id"]
        
        logger.info(f"Processing chat query from user {user_id}: {request.question[:100]}...")
        
        # Search for relevant chunks in vector database
        similar_chunks = await vector_db_service.search_similar_chunks(
            tenant_id=tenant_id,
            query=request.question,
            top_k=request.top_k or 5,
            document_ids=request.document_ids
        )
        
        # Generate LLM response with context
        llm_response = await llm_service.generate_response(
            prompt=request.question,
            context_chunks=similar_chunks
        )
        
        # Calculate response time
        response_time_ms = (time.time() - start_time) * 1000
        
        # Save to chat history
        await chat_repo.create_chat_entry(
            tenant_id=tenant_id,
            user_id=user_id,
            question=request.question,
            answer=llm_response["answer"],
            sources=json.dumps(llm_response["sources"]),
            model=llm_response["model"]
        )
        
        logger.info(f"Chat query processed in {response_time_ms:.2f}ms")
        
        return {
            "success": True,
            "question": request.question,
            "answer": llm_response["answer"],
            "sources": llm_response["sources"],
            "model": llm_response["model"],
            "has_context": llm_response["has_context"],
            "response_time_ms": response_time_ms
        }
    
    except Exception as e:
        logger.error(f"Chat query failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process question: {str(e)}"
        )


@router.get(
    "/chat/history",
    response_model=ChatHistoryResponse,
    summary="Get Chat History",
    description="Retrieve chat history for current user"
)
async def get_chat_history(
    limit: int = 50,
    current_user: Dict = Depends(get_current_user_from_token),
    chat_repo: ChatHistoryRepository = Depends(get_chat_repo)
) -> Dict[str, Any]:
    """
    Get chat history for the current user.
    
    **Authentication Required**: Bearer token
    
    **Query Parameters**:
    - limit: Maximum number of entries to return (default: 50)
    
    **Returns**: List of previous chat interactions
    """
    try:
        tenant_id = current_user["tenant_id"]
        user_id = current_user["user_id"]
        
        history = await chat_repo.get_chat_history(
            tenant_id=tenant_id,
            user_id=user_id,
            limit=limit
        )
        
        # Parse JSON sources
        for entry in history:
            if entry.get("sources"):
                try:
                    entry["sources"] = json.loads(entry["sources"])
                except:
                    entry["sources"] = []
        
        return {
            "success": True,
            "chat_history": history,
            "total": len(history)
        }
    
    except Exception as e:
        logger.error(f"Failed to get chat history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat history"
        )


@router.get(
    "/health",
    response_model=SystemHealthResponse,
    summary="System Health Check",
    description="Check health status of document chat system (vector DB, LLM, stats)"
)
async def health_check(
    current_user: Dict = Depends(get_current_user_from_token),
    doc_repo: DocumentRepository = Depends(get_document_repo)
) -> Dict[str, Any]:
    """
    Check system health for document chat feature.
    
    **Authentication Required**: Bearer token
    
    **Returns**:
    - vector_db_status: Status of ChromaDB
    - llm_status: Status of Ollama/LLM service
    - document_stats: Statistics about uploaded documents
    """
    try:
        tenant_id = current_user["tenant_id"]
        
        # Check LLM availability
        llm_status = await llm_service.check_model_availability()
        
        # Get document stats
        doc_stats = await doc_repo.get_tenant_document_stats(tenant_id)
        
        # Get vector DB stats
        vector_stats = vector_db_service.get_collection_stats(tenant_id)
        
        return {
            "success": True,
            "vector_db_status": "operational" if vector_stats["total_chunks"] >= 0 else "error",
            "llm_status": llm_status,
            "document_stats": doc_stats
        }
    
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "vector_db_status": "error",
            "llm_status": {"status": "error", "error": str(e)},
            "document_stats": {"total_documents": 0, "total_chunks": 0, "total_size_bytes": 0}
        }
