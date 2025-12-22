"""
Document Repository

Database operations for document metadata storage.
Enhanced with date-based filtering for document chat feature.

Date-Based Document Feature:
- Documents indexed by upload_date for efficient filtering
- Frontend displays available dates → user selects date → gets documents for that date
- Selected document is sent to vector DB for RAG-based answers
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date
from app.db.database import Database
from app.core.logger import logger
import uuid


class DocumentRepository:
    """Repository for document metadata operations with date-based filtering"""
    
    def __init__(self, db: Database):
        """Initialize repository with database instance"""
        self.db = db
    
    async def create_document(
        self,
        document_id: str,
        TENANT_NAME: str,
        user_id: str,
        title: str,
        document_type: str,
        body: str,
        filename: str,
        file_size: int,
        total_chunks: int,
        upload_date: date,
        status: str = "processing"
    ) -> Dict[str, Any]:
        """
        Create document metadata record with title, type, and body.
        
        Date-based feature: upload_date is stored for grouping documents by date.
        This allows frontend to display: Date → Documents on that date → Chat
        
        Args:
            document_id: Unique document identifier
            TENANT_NAME: Tenant ID
            user_id: User who uploaded
            title: Document title (e.g., "Sprint 15 Standup")
            document_type: Type (stand_up_doc, retro_summary, etc.)
            body: Full document content
            filename: Original filename
            file_size: File size in bytes
            total_chunks: Number of chunks created for vector DB
            upload_date: Date of upload (used for grouping)
            status: Processing status
        
        Returns:
            Created document record
        """
        try:
            query = """
            INSERT INTO DOCUMENTS (
                DOCUMENT_ID, TENANT_NAME, USER_ID, TITLE, DOCUMENT_TYPE,
                BODY, FILENAME, FILE_SIZE, TOTAL_CHUNKS, UPLOAD_DATE, STATUS, CREATED_AT, UPDATED_AT
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """
            
            await self.db.execute_query(
                query,
                (document_id, TENANT_NAME, user_id, title, document_type, 
                 body, filename, file_size, total_chunks, upload_date, status),
                commit=True
            )
            
            logger.info(
                f"Document created: {document_id}, title='{title}', type='{document_type}', "
                f"date={upload_date}, chunks={total_chunks}"
            )
            
            return await self.get_document_by_id(document_id)
        
        except Exception as e:
            logger.error(f"Failed to create document metadata: {str(e)}", exc_info=True)
            raise
    
    async def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete document details by ID.
        
        Returns full document including body for vector DB storage.
        
        Args:
            document_id: Document ID
        
        Returns:
            Complete document details
        """
        query = """
        SELECT 
            DOCUMENT_ID as document_id,
            TENANT_NAME as tenant_name,
            USER_ID as user_id,
            TITLE as title,
            DOCUMENT_TYPE as type,
            BODY as body,
            FILENAME as filename,
            FILE_SIZE as file_size,
            TOTAL_CHUNKS as total_chunks,
            UPLOAD_DATE as upload_date,
            STATUS as status,
            CREATED_AT as uploaded_at,
            UPDATED_AT as updated_at
        FROM DOCUMENTS
        WHERE DOCUMENT_ID = %s
        """
        
        result = await self.db.execute_query(query, (document_id,), fetch_one=True)
        return result
    
    async def get_available_dates(self, TENANT_NAME: str) -> List[str]:
        """
        Get all distinct dates that have documents for the tenant.
        
        Date-based feature: First step of document selection flow.
        Returns list of dates to populate date picker dropdown on frontend.
        
        Flow:
        1. Frontend calls this → displays dates in dropdown
        2. User selects date → fetch documents for that date
        3. User selects document → send to vector DB and chat
        
        Args:
            TENANT_NAME: Tenant ID
        
        Returns:
            List of dates (ISO format strings) in descending order
        """
        try:
            query = """
            SELECT DISTINCT UPLOAD_DATE
            FROM DOCUMENTS
            WHERE TENANT_NAME = %s AND STATUS = 'ready'
            ORDER BY UPLOAD_DATE DESC
            """
            
            results = await self.db.execute_query(
                query, (TENANT_NAME,), fetch_all=True
            )
            
            # Convert dates to ISO format strings
            dates = [row['UPLOAD_DATE'].isoformat() if hasattr(row['UPLOAD_DATE'], 'isoformat') 
                    else str(row['UPLOAD_DATE']) for row in (results or [])]
            
            logger.info(f"Found {len(dates)} distinct document dates for tenant {TENANT_NAME}")
            
            return dates
        
        except Exception as e:
            logger.error(f"Failed to fetch available dates: {str(e)}", exc_info=True)
            raise
    
    async def get_documents_by_date(
        self,
        TENANT_NAME: str,
        upload_date: date
    ) -> List[Dict[str, Any]]:
        """
        Fetch all documents uploaded on a specific date.
        
        Date-based feature: Called after user selects date from dropdown.
        Returns list of documents for that date to display in document dropdown.
        
        Args:
            TENANT_NAME: Tenant ID
            upload_date: Date to filter documents
        
        Returns:
            List of documents with metadata
        """
        try:
            query = """
            SELECT 
                DOCUMENT_ID as document_id,
                TITLE as title,
                DOCUMENT_TYPE as type,
                FILENAME as filename,
                CREATED_AT as created_at,
                USER_ID as user_id,
                FILE_SIZE as file_size
            FROM DOCUMENTS
            WHERE TENANT_NAME = %s AND UPLOAD_DATE = %s AND STATUS = 'ready'
            ORDER BY CREATED_AT DESC
            """
            
            results = await self.db.execute_query(
                query, (TENANT_NAME, upload_date), fetch_all=True
            )
            
            logger.info(f"Found {len(results or [])} documents for {TENANT_NAME} on {upload_date}")
            
            return results or []
        
        except Exception as e:
            logger.error(f"Failed to fetch documents by date: {str(e)}", exc_info=True)
            raise
    
    async def list_documents_by_tenant(
        self,
        TENANT_NAME: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List all documents for a tenant.
        
        Args:
            TENANT_NAME: Tenant ID
            limit: Maximum results
            offset: Pagination offset
        
        Returns:
            List of documents
        """
        query = """
        SELECT 
            d.DOCUMENT_ID as document_id,
            d.TITLE as title,
            d.DOCUMENT_TYPE as type,
            d.FILENAME as filename,
            d.FILE_SIZE as file_size,
            d.TOTAL_CHUNKS as total_chunks,
            d.STATUS as status,
            d.UPLOAD_DATE as upload_date,
            d.CREATED_AT as uploaded_at,
            d.USER_ID as uploaded_by
        FROM DOCUMENTS d
        WHERE d.TENANT_NAME = %s
        ORDER BY d.UPLOAD_DATE DESC, d.CREATED_AT DESC
        LIMIT %s OFFSET %s
        """
        
        results = await self.db.execute_query(query, (TENANT_NAME, limit, offset), fetch_all=True)
        return results or []
    
    async def update_document_status(
        self,
        document_id: str,
        status: str
    ) -> None:
        """
        Update document processing status.
        
        Status progression:
        - 'processing': Chunks being generated
        - 'ready': Ready for chat (vectors stored in ChromaDB)
        - 'failed': Processing failed
        
        Args:
            document_id: Document ID
            status: New status
        """
        query = """
        UPDATE DOCUMENTS
        SET STATUS = %s, UPDATED_AT = NOW()
        WHERE DOCUMENT_ID = %s
        """
        
        await self.db.execute_query(query, (status, document_id), commit=True)
        logger.info(f"Document {document_id} status updated to {status}")
    
    async def update_document_chunks(
        self,
        document_id: str,
        total_chunks: int
    ) -> None:
        """
        Update total number of chunks for a document.
        
        Args:
            document_id: Document ID
            total_chunks: Total number of chunks created
        """
        query = """
        UPDATE DOCUMENTS
        SET TOTAL_CHUNKS = %s, UPDATED_AT = NOW()
        WHERE DOCUMENT_ID = %s
        """
        
        await self.db.execute_query(query, (total_chunks, document_id), commit=True)
        logger.info(f"Document {document_id} chunks updated to {total_chunks}")
    
    async def delete_document(self, document_id: str) -> None:
        """Delete document metadata"""
        query = "DELETE FROM DOCUMENTS WHERE DOCUMENT_ID = %s"
        await self.db.execute_query(query, (document_id,), commit=True)
        logger.info(f"Document metadata deleted: {document_id}")
    
    async def get_tenant_document_stats(self, TENANT_NAME: str) -> Dict[str, Any]:
        """Get document statistics for tenant"""
        query = """
        SELECT 
            COUNT(*) as total_documents,
            COALESCE(SUM(TOTAL_CHUNKS), 0) as total_chunks,
            COALESCE(SUM(FILE_SIZE), 0) as total_size_bytes
        FROM DOCUMENTS
        WHERE TENANT_NAME = %s AND STATUS = 'ready'
        """
        
        result = await self.db.execute_query(query, (TENANT_NAME,), fetch_one=True)
        return result or {
            "total_documents": 0,
            "total_chunks": 0,
            "total_size_bytes": 0
        }


class ChatHistoryRepository:
    """Repository for chat history operations"""
    
    def __init__(self, db: Database):
        """Initialize repository with database instance"""
        self.db = db
    
    async def create_chat_entry(
        self,
        tenant_id: str,
        user_id: str,
        question: str,
        answer: str,
        sources: str,  # JSON string
        model: str,
        document_id: Optional[str] = None,
        upload_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Create chat history entry.
        
        Date-based feature: Tracks which document was used for each answer.
        Enables audit trail: question → document → answer
        
        Args:
            tenant_id: Tenant identifier
            user_id: User ID
            question: User's question
            answer: LLM's answer
            sources: JSON string of source references
            model: LLM model used
            document_id: Source document used
            upload_date: Date of source document
        
        Returns:
            Created chat entry
        """
        chat_id = f"chat_{uuid.uuid4().hex[:16]}"
        
        query = """
        INSERT INTO CHAT_HISTORY (
            CHAT_ID, TENANT_NAME, USER_ID, QUESTION, 
            ANSWER, SOURCES, MODEL, DOCUMENT_ID, UPLOAD_DATE, CREATED_AT
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """
        
        await self.db.execute_query(
            query,
            (chat_id, tenant_id, user_id, question, answer, sources, model, 
             document_id, upload_date),
            commit=True
        )
        
        logger.info(
            f"Chat history entry created: {chat_id}, document={document_id}, date={upload_date}"
        )
        
        return {
            "chat_id": chat_id,
            "question": question,
            "answer": answer,
            "document_id": document_id
        }
    
    async def get_chat_history(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
        limit: int = 50,
        document_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get chat history for tenant (optionally filtered by user or document).
        
        Args:
            tenant_id: Tenant identifier
            user_id: Optional user ID filter
            limit: Maximum results
            document_id: Optional document filter
        
        Returns:
            List of chat entries
        """
        if document_id:
            # Get chat history for specific document
            query = """
            SELECT 
                CHAT_ID as chat_id,
                QUESTION as question,
                ANSWER as answer,
                SOURCES as sources,
                MODEL as model,
                DOCUMENT_ID as document_id,
                UPLOAD_DATE as upload_date,
                CREATED_AT as created_at
            FROM CHAT_HISTORY
            WHERE TENANT_NAME = %s AND DOCUMENT_ID = %s
            ORDER BY CREATED_AT DESC
            LIMIT %s
            """
            results = await self.db.execute_query(query, (tenant_id, document_id, limit), fetch_all=True)
        elif user_id:
            query = """
            SELECT 
                CHAT_ID as chat_id,
                QUESTION as question,
                ANSWER as answer,
                SOURCES as sources,
                MODEL as model,
                DOCUMENT_ID as document_id,
                UPLOAD_DATE as upload_date,
                CREATED_AT as created_at
            FROM CHAT_HISTORY
            WHERE TENANT_NAME = %s AND USER_ID = %s
            ORDER BY CREATED_AT DESC
            LIMIT %s
            """
            results = await self.db.execute_query(query, (tenant_id, user_id, limit), fetch_all=True)
        else:
            query = """
            SELECT 
                CHAT_ID as chat_id,
                QUESTION as question,
                ANSWER as answer,
                SOURCES as sources,
                MODEL as model,
                DOCUMENT_ID as document_id,
                UPLOAD_DATE as upload_date,
                CREATED_AT as created_at
            FROM CHAT_HISTORY
            WHERE TENANT_NAME = %s
            ORDER BY CREATED_AT DESC
            LIMIT %s
            """
            results = await self.db.execute_query(query, (tenant_id, limit), fetch_all=True)
        
        return results or []
