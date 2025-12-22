"""
Document Chat API Endpoints

Handles PDF upload, document management, and RAG-based chat queries.
Enhanced with date-based document filtering for the document chat feature.

Date-Based Document Feature Flow:
1. Upload document with title, type, upload_date → stored in MySQL
2. Frontend fetches available dates → displays in date picker dropdown
3. User selects date → Frontend fetches documents for that date
4. User selects document → Document details sent to vector DB and chat
5. Chatbot answers questions using selected document context
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends, Query, Form
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
from datetime import date
import time
import json
import uuid

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
from app.services.llm_service import LLMService
from app.db.repositories.document_repository import DocumentRepository, ChatHistoryRepository
from app.db.database import db
from app.utils.jwt import get_current_user_from_token
from app.core.logger import logger

router = APIRouter()

# Initialize services (lazy-load to avoid blocking startup with expensive imports)
document_service = None  # Will be initialized on first use - depends on transformers/torch
llm_service = LLMService()
vector_db_service = None  # Will be initialized on first use

def get_document_service():
    """Lazy-load document service on first use (imports transformers/torch)"""
    global document_service
    if document_service is None:
        from app.services.document_service import DocumentService
        document_service = DocumentService()
    return document_service

def get_vector_db_service():
    """Lazy-load vector DB service on first use"""
    global vector_db_service
    if vector_db_service is None:
        from app.services.vector_db_service import VectorDBService
        vector_db_service = VectorDBService()
    return vector_db_service


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
    title: str = Form(..., description="Document title"),
    document_type: str = Form(..., description="Type: stand_up_doc, retro_summary, sprint_notes, etc."),
    upload_date: Optional[str] = Form(None, description="Upload date (YYYY-MM-DD, defaults to today)"),
    current_user: Dict = Depends(get_current_user_from_token),
    doc_repo: DocumentRepository = Depends(get_document_repo)
) -> Dict[str, Any]:
    """
    Upload and process a PDF document with metadata.
    
    Steps:
    1. Validate file type (PDF only)
    2. Extract text content from PDF
    3. Save document metadata and body to MySQL
    4. Chunk text and create embeddings
    5. Store chunks in vector database
    
    **Authentication Required**: Bearer token in header
    
    **FormData Fields** (multipart/form-data):
    - file: PDF file (required)
    - title: Document title (required)
    - document_type: stand_up_doc, retro_summary, sprint_notes, task_list, meeting_notes, or other (required)
    - upload_date: Date in YYYY-MM-DD format (optional, defaults to today)
    
    **Returns**:
    - document_id: Unique identifier
    - filename: Original filename
    - title: Document title
    - type: Document type
    - upload_date: Date in ISO format
    - total_chunks: Number of text chunks
    - total_characters: Characters extracted
    """
    document_id = None
    try:
        # Validate file type
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are supported. Upload file must have .pdf extension"
            )
        
        # Parse and validate upload date
        try:
            parsed_date = date.fromisoformat(upload_date) if upload_date else date.today()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD (e.g., 2025-01-15)"
            )
        
        # Get user and tenant info
        user_id = current_user.get("user_id")
        tenant_id = current_user.get("tenant_name")
        
        if not user_id or not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
        
        # Generate unique document ID
        document_id = str(uuid.uuid4())
        
        logger.info(
            f"Starting document upload: id={document_id}, title={title}, "
            f"type={document_type}, user={user_id}, tenant={tenant_id}"
        )
        
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty"
            )
        
        # Reset file pointer for PDF extraction
        await file.seek(0)
        
        # Step 1: Extract text from PDF
        logger.info(f"Extracting text from PDF: {file.filename}")
        doc_service = get_document_service()
        pdf_text = await doc_service.extract_text_from_pdf(file.file, file.filename)
        
        if not pdf_text or pdf_text.strip() == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No text content found in PDF"
            )
        
        # Step 2: Save document metadata and body to MySQL immediately
        logger.info(f"Saving document metadata to database: {document_id}")
        await doc_repo.create_document(
            document_id=document_id,
            TENANT_NAME=tenant_id,
            user_id=user_id,
            filename=file.filename,
            file_size=file_size,
            title=title,
            document_type=document_type,
            body=pdf_text,  # Store full PDF content in database
            upload_date=parsed_date,
            total_chunks=0,  # Will update after chunking
            status="processing"
        )
        
        # Step 3: Chunk the text
        logger.info(f"Chunking document text: {document_id}")
        chunks = await doc_service.chunk_text(pdf_text, document_id, file.filename)
        
        # Step 4: Store chunks in vector database
        logger.info(f"Storing {len(chunks)} chunks in vector database: {document_id}")
        vector_service = get_vector_db_service()
        await vector_service.store_document_chunks(
            tenant_id=tenant_id,
            document_id=document_id,
            chunks=chunks
        )
        
        # Step 5: Update document status and chunk count
        logger.info(f"Finalizing document: {document_id}")
        await doc_repo.update_document_status(document_id, "ready")
        await doc_repo.update_document_chunks(document_id, len(chunks))
        
        logger.info(
            f"Document successfully processed: id={document_id}, title={title}, "
            f"chunks={len(chunks)}, size={len(pdf_text)} characters"
        )
        
        return {
            "success": True,
            "message": "Document uploaded and processed successfully",
            "document_id": document_id,
            "filename": file.filename,
            "title": title,
            "type": document_type,
            "upload_date": parsed_date.isoformat(),
            "total_chunks": len(chunks),
            "total_characters": len(pdf_text)
        }
    
    except HTTPException:
        # Mark document as error if it was created
        if document_id:
            try:
                await doc_repo.update_document_status(document_id, "error")
            except:
                pass
        raise
    except Exception as e:
        # Mark document as error if it was created
        if document_id:
            try:
                await doc_repo.update_document_status(document_id, "error")
            except:
                pass
        
        logger.error(f"Document upload failed (id={document_id}): {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document processing failed: {str(e)}"
        )


# ============================================
# DATE-BASED DOCUMENT SELECTION ENDPOINTS
# ============================================

@router.get(
    "/dates/available",
    summary="Get Available Document Dates",
    description="Fetch all distinct dates that have documents (for date picker dropdown)"
)
async def get_available_dates(
    current_user: Dict = Depends(get_current_user_from_token),
    doc_repo: DocumentRepository = Depends(get_document_repo)
) -> Dict[str, Any]:
    """
    Get list of all dates that have documents for the tenant.
    
    Date-based feature: First step of document selection flow.
    Frontend uses this to populate date picker dropdown.
    
    Flow:
    1. GET /documents/dates/available → list of dates
    2. User selects date → GET /documents/by-date/{date}
    3. GET returns documents for that date → user selects document
    4. Selected document sent to vector DB for chat context
    
    **Authentication Required**: Bearer token
    
    **Returns**:
    - dates: List of dates in ISO format (YYYY-MM-DD)
    - total_dates: Number of distinct dates
    
    **Example Response**:
    ```json
    {
      "success": true,
      "dates": ["2025-01-15", "2025-01-14", "2025-01-13"],
      "total_dates": 3
    }
    ```
    """
    try:
        tenant_id = current_user["tenant_name"]
        
        dates = await doc_repo.get_available_dates(tenant_id)
        
        logger.info(f"Fetched {len(dates)} available dates for tenant {tenant_id}")
        
        return {
            "success": True,
            "dates": dates,
            "total_dates": len(dates)
        }
    
    except Exception as e:
        logger.error(f"Failed to get available dates: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve available dates"
        )


@router.get(
    "/by-date/{upload_date}",
    summary="Get Documents by Date",
    description="Fetch all documents uploaded on a specific date"
)
async def get_documents_by_date(
    upload_date: str,
    current_user: Dict = Depends(get_current_user_from_token),
    doc_repo: DocumentRepository = Depends(get_document_repo)
) -> Dict[str, Any]:
    """
    Get all documents uploaded on a specific date.
    
    Date-based feature: Called after user selects date from dropdown.
    Returns list of documents for that date for user to select from.
    
    **Authentication Required**: Bearer token
    
    **Path Parameters**:
    - upload_date: Date in YYYY-MM-DD format
    
    **Returns**:
    - documents: List of documents with title, type, metadata
    - total: Number of documents
    
    **Example Response**:
    ```json
    {
      "success": true,
      "documents": [
        {
          "document_id": "doc_abc123",
          "title": "Sprint 15 Standup",
          "type": "stand_up_doc",
          "filename": "sprint15.pdf",
          "created_at": "2025-01-15T10:30:00"
        }
      ],
      "total": 1
    }
    ```
    """
    try:
        # Parse date
        try:
            parsed_date = date.fromisoformat(upload_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
        
        tenant_id = current_user["tenant_name"]
        
        documents = await doc_repo.get_documents_by_date(tenant_id, parsed_date)
        
        logger.info(f"Fetched {len(documents)} documents for {tenant_id} on {parsed_date}")
        
        return {
            "success": True,
            "date": upload_date,
            "documents": documents,
            "total": len(documents)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get documents by date: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve documents for this date"
        )


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
        tenant_id = current_user["tenant_name"]  # Using tenant_name from JWT
        
        logger.info(f"Processing PDF upload: {file.filename} for user {user_id}")
        
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Reset file pointer for processing
        await file.seek(0)
        
        # Process PDF: extract text and chunk
        processed = await get_document_service().process_pdf(
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
        await get_vector_db_service().store_document_chunks(
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
        tenant_id = current_user["tenant_name"]  # Using tenant_name from JWT
        
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
        tenant_id = current_user["tenant_name"]  # Using tenant_name from JWT
        
        # Verify document belongs to tenant
        document = await doc_repo.get_document_by_id(document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        if document["TENANT_NAME"] != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this document"
            )
        
        # Delete from vector database
        await get_vector_db_service().delete_document_chunks(tenant_id, document_id)
        
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
    description="Ask a question and get an AI-generated answer based on selected document (RAG)"
)
async def ask_question(
    request: ChatQueryRequest,
    document_id: Optional[str] = Query(None, description="Selected document ID (required for date-based feature)"),
    current_user: Dict = Depends(get_current_user_from_token),
    doc_repo: DocumentRepository = Depends(get_document_repo),
    chat_repo: ChatHistoryRepository = Depends(get_chat_repo)
) -> Dict[str, Any]:
    """
    Ask a question and get an answer using RAG (Retrieval-Augmented Generation).
    
    Date-based feature: Use selected document for context.
    
    **How it works**:
    1. If document_id provided: use that document for context (date-based feature)
    2. Convert question to embedding
    3. Search vector database for relevant chunks from selected document
    4. Pass question + relevant chunks to LLM
    5. LLM generates SHORT answer (concise and relevant)
    6. Return answer with source references
    
    **Authentication Required**: Bearer token
    
    **Query Parameters**:
    - document_id: Selected document ID (recommended for date-based feature)
    
    **Request Body**:
    - question: The question to ask (3-1000 characters)
    - top_k: Number of context chunks to retrieve (1-10, default: 5)
    
    **Returns**:
    - answer: SHORT AI-generated response (concise, 1-3 sentences)
    - sources: List of source chunks used
    - document_id: Document used for context
    - model: LLM model used
    - has_context: Whether relevant context was found
    """
    try:
        start_time = time.time()
        
        tenant_id = current_user["tenant_name"]
        user_id = current_user["user_id"]
        
        logger.info(
            f"Chat query from user {user_id}: {request.question[:100]}... "
            f"(document={document_id})"
        )
        
        # If document_id provided, fetch document details for enhanced context
        selected_document = None
        document_date = None
        if document_id:
            selected_document = await doc_repo.get_document_by_id(document_id)
            if selected_document:
                document_date = selected_document.get("upload_date")
                logger.info(
                    f"Using document {document_id}: '{selected_document.get('title')}' "
                    f"({selected_document.get('type')})"
                )
        
        # Search for relevant chunks in vector database
        similar_chunks = await get_vector_db_service().search_similar_chunks(
            tenant_id=tenant_id,
            query=request.question,
            top_k=request.top_k or 5,
            document_ids=[document_id] if document_id else None  # Limit to selected document
        )
        
        # Generate LLM response with context - REQUEST SHORT ANSWER
        llm_response = await llm_service.generate_short_response(
            prompt=request.question,
            context_chunks=similar_chunks,
            max_length=200  # Force short answer (1-3 sentences)
        )
        
        # Calculate response time
        response_time_ms = (time.time() - start_time) * 1000
        
        # Save to chat history with document reference
        await chat_repo.create_chat_entry(
            tenant_id=tenant_id,
            user_id=user_id,
            question=request.question,
            answer=llm_response["answer"],
            sources=json.dumps(llm_response["sources"]),
            model=llm_response["model"],
            document_id=document_id,
            upload_date=document_date
        )
        
        logger.info(f"Chat query processed in {response_time_ms:.2f}ms")
        
        return {
            "success": True,
            "question": request.question,
            "answer": llm_response["answer"],  # SHORT answer
            "sources": llm_response["sources"],
            "document_id": document_id,
            "document_title": selected_document.get("title") if selected_document else None,
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
        tenant_id = current_user["tenant_name"]  # Using tenant_name from JWT
        user_id = current_user["user_id"]
        
        history = await chat_repo.get_chat_history(
            tenant_id=tenant_id,
            user_id=user_id,
            limit=limit
        )
        
        # Ensure history is a list
        if history is None:
            history = []
        
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
        tenant_id = current_user["tenant_name"]  # Using tenant_name from JWT
        
        # Check LLM availability
        llm_status = await llm_service.check_model_availability()
        
        # Get document stats
        doc_stats = await doc_repo.get_tenant_document_stats(tenant_id)
        
        # Get vector DB stats
        vector_stats = get_vector_db_service().get_collection_stats(tenant_id)
        
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
            "llm_status": {
                "status": "error",
                "configured_model": llm_service.model_name,
                "llm_url": llm_service.llm_url,
                "available_models": [],
                "error": str(e)
            },
            "document_stats": {"total_documents": 0, "total_chunks": 0, "total_size_bytes": 0}
        }
