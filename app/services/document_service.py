"""
Document Service

Service layer for document operations.
Handles fetching documents by date, retrieving content, and searching.
"""

from typing import Optional, List
from datetime import date
from app.db.database import db
from app.core.logger import logger
from app.schemas.document import (
    DocumentCreate, DocumentResponse, DocumentListResponse,
    DocumentContentResponse, DocumentDateResponse
)


class DocumentService:
    """Service for managing documents"""
    
    @staticmethod
    async def create_document(doc_data: DocumentCreate, schema: str) -> DocumentResponse:
        """
        Create a new document
        
        Args:
            doc_data: Document creation data
            schema: Database schema name
            
        Returns:
            Created document response
        """
        try:
            query = """
                INSERT INTO documents (doc_title, doc_content, uploaded_date, category)
                VALUES (%s, %s, %s, %s)
            """
            
            await db.execute_query(
                query,
                (doc_data.doc_title, doc_data.doc_content, doc_data.uploaded_date, doc_data.category),
                commit=True,
                schema=schema
            )
            
            # Fetch and return the created document
            return await DocumentService.get_document_by_title(doc_data.doc_title, schema)
            
        except Exception as e:
            logger.error(f"Error creating document: {e}")
            raise
    
    @staticmethod
    async def get_all_documents_content(schema: str, limit: int = 100) -> List[DocumentContentResponse]:
        """
        Fetch all documents with content for multi-document RAG search
        
        Args:
            schema: Database schema name
            limit: Maximum number of documents to fetch
            
        Returns:
            List of documents with content
        """
        try:
            query = """
                SELECT id, doc_title, doc_content, uploaded_date, category
                FROM documents
                WHERE is_active = TRUE
                ORDER BY created_at DESC
                LIMIT %s
            """
            
            results = await db.execute_query(
                query,
                (limit,),
                fetch_all=True,
                schema=schema
            )
            
            if not results:
                return []
            
            return [
                DocumentContentResponse(
                    id=row['id'],
                    doc_title=row['doc_title'],
                    doc_content=row['doc_content'],
                    uploaded_date=row['uploaded_date'],
                    category=row['category']
                )
                for row in results
            ]
            
        except Exception as e:
            logger.error(f"Error fetching all documents content: {e}")
            raise
    
    @staticmethod
    async def get_unique_dates(schema: str) -> List[DocumentDateResponse]:
        """
        Fetch all unique uploaded dates with document counts
        
        Args:
            schema: Database schema name
            
        Returns:
            List of unique dates with counts
        """
        try:
            query = """
                SELECT uploaded_date, COUNT(*) as count
                FROM documents
                WHERE is_active = TRUE
                GROUP BY uploaded_date
                ORDER BY uploaded_date DESC
            """
            
            results = await db.execute_query(
                query,
                fetch_all=True,
                schema=schema
            )
            
            if not results:
                return []
            
            return [
                DocumentDateResponse(uploaded_date=row['uploaded_date'], count=row['count'])
                for row in results
            ]
            
        except Exception as e:
            logger.error(f"Error fetching unique dates: {e}")
            raise
    
    @staticmethod
    async def get_documents_by_date_with_content(
        uploaded_date: date,
        schema: str,
        limit: int = 100
    ) -> List[DocumentContentResponse]:
        """
        Fetch documents with content for a specific date (for multi-doc RAG search)
        
        Args:
            uploaded_date: Date to filter documents
            schema: Database schema name
            limit: Maximum number of results
            
        Returns:
            List of documents with content on the specified date
        """
        try:
            query = """
                SELECT id, doc_title, doc_content, uploaded_date, category
                FROM documents
                WHERE uploaded_date = %s AND is_active = TRUE
                ORDER BY created_at DESC
                LIMIT %s
            """
            
            results = await db.execute_query(
                query,
                (uploaded_date, limit),
                fetch_all=True,
                schema=schema
            )
            
            if not results:
                return []
            
            return [
                DocumentContentResponse(
                    id=row['id'],
                    doc_title=row['doc_title'],
                    doc_content=row['doc_content'],
                    uploaded_date=row['uploaded_date'],
                    category=row['category']
                )
                for row in results
            ]
            
        except Exception as e:
            logger.error(f"Error fetching documents by date with content: {e}")
            raise
    
    @staticmethod
    async def get_documents_by_date(
        uploaded_date: date,
        schema: str,
        limit: int = 100
    ) -> List[DocumentListResponse]:
        """
        Fetch document list for a specific date
        
        Args:
            uploaded_date: Date to filter documents
            schema: Database schema name
            limit: Maximum number of results
            
        Returns:
            List of documents on the specified date
        """
        try:
            query = """
                SELECT id, doc_title, uploaded_date, category, created_at
                FROM documents
                WHERE uploaded_date = %s AND is_active = TRUE
                ORDER BY created_at DESC
                LIMIT %s
            """
            
            results = await db.execute_query(
                query,
                (uploaded_date, limit),
                fetch_all=True,
                schema=schema
            )
            
            if not results:
                return []
            
            return [
                DocumentListResponse(
                    id=row['id'],
                    doc_title=row['doc_title'],
                    uploaded_date=row['uploaded_date'],
                    category=row['category'],
                    created_at=row['created_at']
                )
                for row in results
            ]
            
        except Exception as e:
            logger.error(f"Error fetching documents by date: {e}")
            raise
    
    @staticmethod
    async def get_document_content(document_id: int, schema: str) -> Optional[DocumentContentResponse]:
        """
        Retrieve document content by ID
        
        Args:
            document_id: Document ID
            schema: Database schema name
            
        Returns:
            Document content or None if not found
        """
        try:
            query = """
                SELECT id, doc_title, doc_content, uploaded_date, category
                FROM documents
                WHERE id = %s AND is_active = TRUE
            """
            
            result = await db.execute_query(
                query,
                (document_id,),
                fetch_one=True,
                schema=schema
            )
            
            if not result:
                logger.warning(f"Document not found: {document_id}")
                return None
            
            return DocumentContentResponse(
                id=result['id'],
                doc_title=result['doc_title'],
                doc_content=result['doc_content'],
                uploaded_date=result['uploaded_date'],
                category=result['category']
            )
            
        except Exception as e:
            logger.error(f"Error retrieving document content: {e}")
            raise
    
    @staticmethod
    async def get_document_by_id(document_id: int, schema: str) -> Optional[DocumentResponse]:
        """
        Retrieve complete document by ID
        
        Args:
            document_id: Document ID
            schema: Database schema name
            
        Returns:
            Document response or None if not found
        """
        try:
            query = """
                SELECT id, doc_title, doc_content, uploaded_date, category, created_at, updated_at, is_active
                FROM documents
                WHERE id = %s
            """
            
            result = await db.execute_query(
                query,
                (document_id,),
                fetch_one=True,
                schema=schema
            )
            
            if not result:
                return None
            
            return DocumentResponse(
                id=result['id'],
                doc_title=result['doc_title'],
                doc_content=result['doc_content'],
                uploaded_date=result['uploaded_date'],
                category=result['category'],
                created_at=result['created_at'],
                updated_at=result['updated_at'],
                is_active=result['is_active']
            )
            
        except Exception as e:
            logger.error(f"Error retrieving document: {e}")
            raise
    
    @staticmethod
    async def get_document_by_title(title: str, schema: str) -> Optional[DocumentResponse]:
        """
        Retrieve document by title
        
        Args:
            title: Document title
            schema: Database schema name
            
        Returns:
            Document response or None if not found
        """
        try:
            query = """
                SELECT id, doc_title, doc_content, uploaded_date, category, created_at, updated_at, is_active
                FROM documents
                WHERE doc_title = %s AND is_active = TRUE
                LIMIT 1
            """
            
            result = await db.execute_query(
                query,
                (title,),
                fetch_one=True,
                schema=schema
            )
            
            if not result:
                return None
            
            return DocumentResponse(
                id=result['id'],
                doc_title=result['doc_title'],
                doc_content=result['doc_content'],
                uploaded_date=result['uploaded_date'],
                category=result['category'],
                created_at=result['created_at'],
                updated_at=result['updated_at'],
                is_active=result['is_active']
            )
            
        except Exception as e:
            logger.error(f"Error retrieving document by title: {e}")
            raise
    
    @staticmethod
    async def search_documents(
        search_query: str,
        schema: str,
        uploaded_date: Optional[date] = None,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[DocumentListResponse]:
        """
        Search documents by title or content
        
        Args:
            search_query: Search keywords
            schema: Database schema name
            uploaded_date: Optional date filter
            category: Optional category filter
            limit: Results limit
            
        Returns:
            List of matching documents
        """
        try:
            query = """
                SELECT id, doc_title, uploaded_date, category, created_at
                FROM documents
                WHERE is_active = TRUE
                AND (doc_title LIKE %s OR doc_content LIKE %s)
            """
            
            params = [f"%{search_query}%", f"%{search_query}%"]
            
            if uploaded_date:
                query += " AND uploaded_date = %s"
                params.append(uploaded_date)
            
            if category:
                query += " AND category = %s"
                params.append(category)
            
            query += f" ORDER BY created_at DESC LIMIT {limit}"
            
            results = await db.execute_query(
                query,
                tuple(params),
                fetch_all=True,
                schema=schema
            )
            
            if not results:
                return []
            
            return [
                DocumentListResponse(
                    id=row['id'],
                    doc_title=row['doc_title'],
                    uploaded_date=row['uploaded_date'],
                    category=row['category'],
                    created_at=row['created_at']
                )
                for row in results
            ]
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            raise
    
    @staticmethod
    async def update_document(document_id: int, doc_data: dict, schema: str) -> Optional[DocumentResponse]:
        """
        Update document
        
        Args:
            document_id: Document ID
            doc_data: Updated data
            schema: Database schema name
            
        Returns:
            Updated document response or None
        """
        try:
            # Build dynamic update query
            set_clauses = []
            params = []
            
            for key, value in doc_data.items():
                if value is not None:
                    set_clauses.append(f"{key} = %s")
                    params.append(value)
            
            if not set_clauses:
                return await DocumentService.get_document_by_id(document_id, schema)
            
            params.append(document_id)
            query = f"UPDATE documents SET {', '.join(set_clauses)} WHERE id = %s"
            
            await db.execute_query(
                query,
                tuple(params),
                commit=True,
                schema=schema
            )
            
            return await DocumentService.get_document_by_id(document_id, schema)
            
        except Exception as e:
            logger.error(f"Error updating document: {e}")
            raise
    
    @staticmethod
    async def delete_document(document_id: int, schema: str, soft_delete: bool = True) -> bool:
        """
        Delete document (soft or hard delete)
        
        Args:
            document_id: Document ID
            schema: Database schema name
            soft_delete: If True, mark as inactive instead of deleting
            
        Returns:
            True if successful
        """
        try:
            if soft_delete:
                query = "UPDATE documents SET is_active = FALSE WHERE id = %s"
            else:
                query = "DELETE FROM documents WHERE id = %s"
            
            await db.execute_query(
                query,
                (document_id,),
                commit=True,
                schema=schema
            )
            
            logger.info(f"Document deleted (soft_delete={soft_delete}): {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            raise
    
    @staticmethod
    async def get_documents_by_category(
        category: str,
        schema: str,
        limit: int = 100
    ) -> List[DocumentListResponse]:
        """
        Get documents by category
        
        Args:
            category: Category name
            schema: Database schema name
            limit: Results limit
            
        Returns:
            List of documents in category
        """
        try:
            query = """
                SELECT id, doc_title, uploaded_date, category, created_at
                FROM documents
                WHERE category = %s AND is_active = TRUE
                ORDER BY created_at DESC
                LIMIT %s
            """
            
            results = await db.execute_query(
                query,
                (category, limit),
                fetch_all=True,
                schema=schema
            )
            
            if not results:
                return []
            
            return [
                DocumentListResponse(
                    id=row['id'],
                    doc_title=row['doc_title'],
                    uploaded_date=row['uploaded_date'],
                    category=row['category'],
                    created_at=row['created_at']
                )
                for row in results
            ]
            
        except Exception as e:
            logger.error(f"Error fetching documents by category: {e}")
            raise

    @staticmethod
    async def get_all_documents(schema: str, limit: int = 1000) -> List[DocumentResponse]:
        """
        Get all documents for the schema
        
        Args:
            schema: Tenant schema name
            limit: Maximum number of documents to return
        
        Returns:
            List of all documents
        """
        try:
            query = f"""
                SELECT id, doc_title, doc_content, uploaded_date, category, created_at, updated_at, is_active
                FROM `{schema}`.documents
                WHERE is_active = 1
                ORDER BY created_at DESC
                LIMIT {limit}
            """
            
            results = await db.execute_query(
                query,
                fetch_all=True,
                schema=schema
            )
            
            if not results:
                return []
            
            return [
                DocumentResponse(
                    id=row['id'],
                    doc_title=row['doc_title'],
                    doc_content=row['doc_content'],
                    uploaded_date=row['uploaded_date'],
                    category=row['category'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    is_active=row['is_active']
                )
                for row in results
            ]
            
        except Exception as e:
            logger.error(f"Error fetching all documents: {e}")
            raise


# Create singleton instance
document_service = DocumentService()
