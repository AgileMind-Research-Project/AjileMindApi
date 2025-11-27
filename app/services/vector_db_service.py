"""
Vector Database Service using ChromaDB

Handles embedding generation, storage, and retrieval for RAG system.
"""

import os
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from app.core.config import settings
from app.core.logger import logger


class VectorDBService:
    """Service for managing embeddings and vector search with ChromaDB"""
    
    def __init__(self):
        """Initialize ChromaDB and embedding model"""
        # ChromaDB persistence directory
        self.persist_directory = settings.CHROMA_PERSIST_DIR
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize embedding model
        self.embedding_model_name = settings.EMBEDDING_MODEL_NAME
        logger.info(f"Loading embedding model: {self.embedding_model_name}")
        self.embedding_model = SentenceTransformer(self.embedding_model_name)
        
        logger.info(f"Vector DB Service initialized with ChromaDB at {self.persist_directory}")
    
    def get_or_create_collection(self, tenant_id: str) -> chromadb.Collection:
        """
        Get or create a collection for a tenant (multi-tenant isolation).
        
        Args:
            tenant_id: Tenant identifier
        
        Returns:
            ChromaDB collection
        """
        collection_name = f"tenant_{tenant_id}_documents"
        
        try:
            collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"tenant_id": tenant_id}
            )
            return collection
        except Exception as e:
            logger.error(f"Failed to get/create collection for tenant {tenant_id}: {str(e)}")
            raise
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for text chunks.
        
        Args:
            texts: List of text strings
        
        Returns:
            List of embedding vectors
        """
        try:
            logger.info(f"Generating embeddings for {len(texts)} text chunks")
            
            # Generate embeddings using sentence-transformers
            embeddings = self.embedding_model.encode(
                texts,
                show_progress_bar=False,
                convert_to_numpy=True
            )
            
            # Convert to list of lists
            embeddings_list = embeddings.tolist()
            
            logger.info(f"Generated {len(embeddings_list)} embeddings")
            
            return embeddings_list
        
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {str(e)}", exc_info=True)
            raise Exception(f"Embedding generation failed: {str(e)}")
    
    async def store_document_chunks(
        self,
        tenant_id: str,
        document_id: str,
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Store document chunks with embeddings in vector database.
        
        Args:
            tenant_id: Tenant identifier
            document_id: Document identifier
            chunks: List of chunk dictionaries with text and metadata
        
        Returns:
            Storage result dictionary
        """
        try:
            logger.info(f"Storing {len(chunks)} chunks for document {document_id}")
            
            # Get tenant collection
            collection = self.get_or_create_collection(tenant_id)
            
            # Extract texts for embedding
            texts = [chunk['text'] for chunk in chunks]
            
            # Generate embeddings
            embeddings = await self.generate_embeddings(texts)
            
            # Prepare data for ChromaDB
            ids = [chunk['chunk_id'] for chunk in chunks]
            metadatas = [chunk['metadata'] for chunk in chunks]
            
            # Store in ChromaDB
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas
            )
            
            logger.info(f"Successfully stored {len(chunks)} chunks for document {document_id}")
            
            return {
                "status": "success",
                "document_id": document_id,
                "chunks_stored": len(chunks),
                "collection": collection.name
            }
        
        except Exception as e:
            logger.error(f"Failed to store chunks for document {document_id}: {str(e)}", exc_info=True)
            raise Exception(f"Vector storage failed: {str(e)}")
    
    async def search_similar_chunks(
        self,
        tenant_id: str,
        query: str,
        top_k: int = 5,
        document_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using semantic search.
        
        Args:
            tenant_id: Tenant identifier
            query: Search query
            top_k: Number of results to return
            document_ids: Optional filter by specific documents
        
        Returns:
            List of similar chunks with scores
        """
        try:
            logger.info(f"Searching for similar chunks: query='{query[:100]}...', top_k={top_k}")
            
            # Get tenant collection
            collection = self.get_or_create_collection(tenant_id)
            
            # Generate query embedding
            query_embeddings = await self.generate_embeddings([query])
            query_embedding = query_embeddings[0]
            
            # Prepare filter if document_ids provided
            where_filter = None
            if document_ids:
                where_filter = {"document_id": {"$in": document_ids}}
            
            # Search in ChromaDB
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results
            similar_chunks = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    chunk = {
                        "chunk_id": results['ids'][0][i],
                        "text": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i],
                        "score": 1 - results['distances'][0][i],  # Convert distance to similarity
                        "filename": results['metadatas'][0][i].get('source', 'Unknown'),
                        "document_id": results['metadatas'][0][i].get('document_id', ''),
                        "chunk_index": results['metadatas'][0][i].get('chunk_index', 0)
                    }
                    similar_chunks.append(chunk)
            
            logger.info(f"Found {len(similar_chunks)} similar chunks")
            
            return similar_chunks
        
        except Exception as e:
            logger.error(f"Vector search failed: {str(e)}", exc_info=True)
            raise Exception(f"Vector search failed: {str(e)}")
    
    async def delete_document_chunks(
        self,
        tenant_id: str,
        document_id: str
    ) -> Dict[str, Any]:
        """
        Delete all chunks for a specific document.
        
        Args:
            tenant_id: Tenant identifier
            document_id: Document identifier
        
        Returns:
            Deletion result
        """
        try:
            logger.info(f"Deleting chunks for document {document_id}")
            
            # Get tenant collection
            collection = self.get_or_create_collection(tenant_id)
            
            # Delete chunks with matching document_id
            collection.delete(
                where={"document_id": document_id}
            )
            
            logger.info(f"Successfully deleted chunks for document {document_id}")
            
            return {
                "status": "success",
                "document_id": document_id,
                "message": "Document chunks deleted from vector database"
            }
        
        except Exception as e:
            logger.error(f"Failed to delete document chunks: {str(e)}", exc_info=True)
            raise Exception(f"Chunk deletion failed: {str(e)}")
    
    def get_collection_stats(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get statistics about a tenant's collection.
        
        Args:
            tenant_id: Tenant identifier
        
        Returns:
            Collection statistics
        """
        try:
            collection = self.get_or_create_collection(tenant_id)
            count = collection.count()
            
            return {
                "collection_name": collection.name,
                "total_chunks": count,
                "tenant_id": tenant_id,
                "embedding_model": self.embedding_model_name
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {str(e)}")
            return {
                "collection_name": f"tenant_{tenant_id}_documents",
                "total_chunks": 0,
                "error": str(e)
            }
