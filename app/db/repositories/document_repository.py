"""
Document Repository

Database operations for document metadata storage.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from app.db.database import Database
from app.core.logger import logger
import uuid


class DocumentRepository:
    """Repository for document metadata operations"""
    
    def __init__(self, db: Database):
        """Initialize repository with database instance"""
        self.db = db
    
    async def create_document(
        self,
        document_id: str,
        tenant_id: str,
        user_id: str,
        filename: str,
        file_size: int,
        total_chunks: int,
        status: str = "processing"
    ) -> Dict[str, Any]:
        """
        Create document metadata record.
        
        Args:
            document_id: Unique document identifier
            tenant_id: Tenant ID
            user_id: User who uploaded
            filename: Original filename
            file_size: File size in bytes
            total_chunks: Number of chunks created
            status: Processing status
        
        Returns:
            Created document record
        """
        try:
            query = """
            INSERT INTO DOCUMENTS (
                DOCUMENT_ID, TENANT_ID, USER_ID, FILENAME, 
                FILE_SIZE, TOTAL_CHUNKS, STATUS, CREATED_AT, UPDATED_AT
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """
            
            await self.db.execute_query(
                query,
                (document_id, tenant_id, user_id, filename, file_size, total_chunks, status),
                commit=True
            )
            
            logger.info(f"Document metadata created: {document_id} - {filename}")
            
            return await self.get_document_by_id(document_id)
        
        except Exception as e:
            logger.error(f"Failed to create document metadata: {str(e)}", exc_info=True)
            raise
    
    async def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        query = """
        SELECT 
            DOCUMENT_ID as document_id,
            TENANT_ID as tenant_id,
            USER_ID as user_id,
            FILENAME as filename,
            FILE_SIZE as file_size,
            TOTAL_CHUNKS as total_chunks,
            STATUS as status,
            CREATED_AT as uploaded_at,
            UPDATED_AT as updated_at
        FROM DOCUMENTS
        WHERE DOCUMENT_ID = %s
        """
        
        result = await self.db.fetch_one(query, (document_id,))
        return result
    
    async def list_documents_by_tenant(
        self,
        tenant_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List all documents for a tenant.
        
        Args:
            tenant_id: Tenant ID
            limit: Maximum results
            offset: Pagination offset
        
        Returns:
            List of documents
        """
        query = """
        SELECT 
            d.DOCUMENT_ID as document_id,
            d.FILENAME as filename,
            d.FILE_SIZE as file_size,
            d.TOTAL_CHUNKS as total_chunks,
            d.STATUS as status,
            d.CREATED_AT as uploaded_at,
            u.EMAIL as uploaded_by
        FROM DOCUMENTS d
        LEFT JOIN USERS u ON d.USER_ID = u.USER_ID
        WHERE d.TENANT_ID = %s
        ORDER BY d.CREATED_AT DESC
        LIMIT %s OFFSET %s
        """
        
        results = await self.db.fetch_all(query, (tenant_id, limit, offset))
        return results
    
    async def update_document_status(
        self,
        document_id: str,
        status: str
    ) -> None:
        """Update document processing status"""
        query = """
        UPDATE DOCUMENTS
        SET STATUS = %s, UPDATED_AT = NOW()
        WHERE DOCUMENT_ID = %s
        """
        
        await self.db.execute_query(query, (status, document_id), commit=True)
        logger.info(f"Document {document_id} status updated to {status}")
    
    async def delete_document(self, document_id: str) -> None:
        """Delete document metadata"""
        query = "DELETE FROM DOCUMENTS WHERE DOCUMENT_ID = %s"
        await self.db.execute_query(query, (document_id,), commit=True)
        logger.info(f"Document metadata deleted: {document_id}")
    
    async def get_tenant_document_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Get document statistics for tenant"""
        query = """
        SELECT 
            COUNT(*) as total_documents,
            COALESCE(SUM(TOTAL_CHUNKS), 0) as total_chunks,
            COALESCE(SUM(FILE_SIZE), 0) as total_size_bytes
        FROM DOCUMENTS
        WHERE TENANT_ID = %s AND STATUS = 'ready'
        """
        
        result = await self.db.fetch_one(query, (tenant_id,))
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
        model: str
    ) -> Dict[str, Any]:
        """
        Create chat history entry.
        
        Args:
            tenant_id: Tenant ID
            user_id: User ID
            question: User's question
            answer: LLM's answer
            sources: JSON string of source references
            model: LLM model used
        
        Returns:
            Created chat entry
        """
        chat_id = f"chat_{uuid.uuid4().hex[:16]}"
        
        query = """
        INSERT INTO CHAT_HISTORY (
            CHAT_ID, TENANT_ID, USER_ID, QUESTION, 
            ANSWER, SOURCES, MODEL, CREATED_AT
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        """
        
        await self.db.execute_query(
            query,
            (chat_id, tenant_id, user_id, question, answer, sources, model),
            commit=True
        )
        
        logger.info(f"Chat history entry created: {chat_id}")
        
        return {
            "chat_id": chat_id,
            "question": question,
            "answer": answer
        }
    
    async def get_chat_history(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get chat history for tenant (optionally filtered by user).
        
        Args:
            tenant_id: Tenant ID
            user_id: Optional user ID filter
            limit: Maximum results
        
        Returns:
            List of chat entries
        """
        if user_id:
            query = """
            SELECT 
                CHAT_ID as chat_id,
                QUESTION as question,
                ANSWER as answer,
                SOURCES as sources,
                MODEL as model,
                CREATED_AT as created_at
            FROM CHAT_HISTORY
            WHERE TENANT_ID = %s AND USER_ID = %s
            ORDER BY CREATED_AT DESC
            LIMIT %s
            """
            params = (tenant_id, user_id, limit)
        else:
            query = """
            SELECT 
                CHAT_ID as chat_id,
                QUESTION as question,
                ANSWER as answer,
                SOURCES as sources,
                MODEL as model,
                CREATED_AT as created_at
            FROM CHAT_HISTORY
            WHERE TENANT_ID = %s
            ORDER BY CREATED_AT DESC
            LIMIT %s
            """
            params = (tenant_id, limit)
        
        results = await self.db.fetch_all(query, params)
        return results
