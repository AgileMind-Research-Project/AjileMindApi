"""
Document Processing Service

Handles PDF extraction, text chunking, and document processing for RAG system.
"""

import os
import uuid
from typing import List, Dict, Any, BinaryIO
from datetime import datetime
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.logger import logger


class DocumentService:
    """Service for processing PDF documents for RAG system"""
    
    def __init__(self):
        """Initialize document service"""
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,  # Characters per chunk
            chunk_overlap=200,  # Overlap between chunks for context
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
    
    async def extract_text_from_pdf(self, file: BinaryIO, filename: str) -> str:
        """
        Extract text content from PDF file.
        
        Args:
            file: Binary file object
            filename: Name of the file
        
        Returns:
            Extracted text content
        
        Raises:
            Exception: If PDF extraction fails
        """
        try:
            logger.info(f"Extracting text from PDF: {filename}")
            
            # Read PDF
            pdf_reader = PdfReader(file)
            
            # Extract text from all pages
            text_content = []
            for page_num, page in enumerate(pdf_reader.pages, start=1):
                page_text = page.extract_text()
                if page_text.strip():
                    text_content.append(f"[Page {page_num}]\n{page_text}")
            
            full_text = "\n\n".join(text_content)
            
            logger.info(f"Extracted {len(full_text)} characters from {len(pdf_reader.pages)} pages")
            
            return full_text
        
        except Exception as e:
            logger.error(f"Failed to extract text from PDF {filename}: {str(e)}", exc_info=True)
            raise Exception(f"PDF extraction failed: {str(e)}")
    
    async def chunk_text(self, text: str, document_id: str, filename: str) -> List[Dict[str, Any]]:
        """
        Split text into chunks for embedding.
        
        Args:
            text: Full text content
            document_id: Unique document identifier
            filename: Original filename
        
        Returns:
            List of chunk dictionaries with metadata
        """
        try:
            logger.info(f"Chunking text for document: {filename}")
            
            # Split text into chunks
            chunks = self.text_splitter.split_text(text)
            
            # Create chunk objects with metadata
            chunk_objects = []
            for idx, chunk_text in enumerate(chunks):
                chunk_obj = {
                    "chunk_id": f"{document_id}_chunk_{idx}",
                    "document_id": document_id,
                    "filename": filename,
                    "chunk_index": idx,
                    "text": chunk_text,
                    "metadata": {
                        "source": filename,
                        "document_id": document_id,
                        "chunk_index": idx,
                        "total_chunks": len(chunks),
                        "created_at": datetime.utcnow().isoformat()
                    }
                }
                chunk_objects.append(chunk_obj)
            
            logger.info(f"Created {len(chunk_objects)} chunks from document {filename}")
            
            return chunk_objects
        
        except Exception as e:
            logger.error(f"Failed to chunk text for {filename}: {str(e)}", exc_info=True)
            raise Exception(f"Text chunking failed: {str(e)}")
    
    async def process_pdf(
        self, 
        file: BinaryIO, 
        filename: str,
        user_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Complete PDF processing pipeline: extract → chunk.
        
        Args:
            file: Binary file object
            filename: Original filename
            user_id: User who uploaded the document
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            Processing result with document_id and chunks
        """
        try:
            # Generate unique document ID
            document_id = f"doc_{uuid.uuid4().hex[:16]}"
            
            logger.info(f"Processing PDF {filename} for user {user_id}, tenant {tenant_id}")
            
            # Extract text
            text = await self.extract_text_from_pdf(file, filename)
            
            if not text or len(text.strip()) < 10:
                raise Exception("No meaningful text extracted from PDF")
            
            # Chunk text
            chunks = await self.chunk_text(text, document_id, filename)
            
            result = {
                "document_id": document_id,
                "filename": filename,
                "user_id": user_id,
                "tenant_id": tenant_id,
                "total_chunks": len(chunks),
                "total_characters": len(text),
                "chunks": chunks,
                "processed_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Successfully processed PDF {filename}: {len(chunks)} chunks")
            
            return result
        
        except Exception as e:
            logger.error(f"Failed to process PDF {filename}: {str(e)}", exc_info=True)
            raise
    
    def get_document_stats(self, text: str) -> Dict[str, Any]:
        """
        Get statistics about document content.
        
        Args:
            text: Document text
        
        Returns:
            Statistics dictionary
        """
        words = text.split()
        return {
            "total_characters": len(text),
            "total_words": len(words),
            "total_lines": len(text.splitlines()),
            "avg_word_length": sum(len(word) for word in words) / len(words) if words else 0
        }
