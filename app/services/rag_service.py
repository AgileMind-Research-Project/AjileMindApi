"""
RAG (Retrieval Augmented Generation) Service

Service layer for RAG-based chatbot with LLM integration.
Features:
- OpenAI GPT-4 integration
- Document chunking and context retrieval
- Semantic search capabilities
- Multi-document search support
- Fallback to simple RAG without LLM
"""

from typing import Optional, List, Dict, Tuple
from app.core.config import settings
from app.core.logger import logger
from app.schemas.document import ChatQueryResponse, DocumentContentResponse, MultiDocChatResponse
from datetime import datetime
import re
from abc import ABC, abstractmethod


class RAGServiceBase(ABC):
    """Base class for RAG services"""
    
    SYSTEM_PROMPT = """You are a helpful assistant with access to document context. 
Use the following document content to answer the user's question accurately and concisely.
If the answer is not in the document, politely say that you don't know based on the selected document. 
Do not use outside knowledge - only rely on the provided document content."""
    
    @staticmethod
    def chunk_document(content: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """
        Split document content into overlapping chunks
        
        Args:
            content: Full document content
            chunk_size: Size of each chunk
            overlap: Number of characters to overlap between chunks
            
        Returns:
            List of document chunks
        """
        if not content:
            return []
        
        # Ensure valid parameters to prevent infinite loop
        chunk_size = max(100, chunk_size)  # Minimum 100 chars per chunk
        overlap = min(overlap, chunk_size - 1)  # Overlap must be less than chunk_size
        overlap = max(0, overlap)  # No negative overlap
        
        chunks = []
        start = 0
        content_len = len(content)
        
        # Safety limit to prevent infinite loops
        max_iterations = (content_len // max(1, chunk_size - overlap)) + 10
        iterations = 0
        
        while start < content_len and iterations < max_iterations:
            iterations += 1
            end = min(start + chunk_size, content_len)
            chunk = content[start:end]
            if chunk.strip():
                chunks.append(chunk.strip())
            
            # Move forward - ensure we always advance
            new_start = end - overlap
            if new_start <= start:
                new_start = start + 1  # Force advancement
            start = new_start
            
        return [c for c in chunks if len(c) > 50]  # Filter out small chunks
    
    @staticmethod
    def find_relevant_chunks(
        chunks: List[str],
        query: str,
        top_k: int = 3
    ) -> List[str]:
        """
        Find most relevant chunks using keyword matching
        
        Args:
            chunks: List of document chunks
            query: User query
            top_k: Number of top results to return
            
        Returns:
            List of most relevant chunks
        """
        query_words = set(query.lower().split())
        scored_chunks = []
        
        for chunk in chunks:
            chunk_lower = chunk.lower()
            # Count matching words
            matches = sum(1 for word in query_words if word in chunk_lower)
            if matches > 0:
                scored_chunks.append((chunk, matches))
        
        # Sort by relevance and return top-k
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return [chunk for chunk, _ in scored_chunks[:top_k]]
    
    @staticmethod
    def calculate_document_relevance(
        content: str,
        query: str
    ) -> float:
        """
        Calculate relevance score of a document for a query
        
        Args:
            content: Document content
            query: User query
            
        Returns:
            Relevance score (0.0 to 1.0)
        """
        if not content or not query:
            return 0.0
        
        query_words = set(query.lower().split())
        content_lower = content.lower()
        
        # Count matching words
        matches = sum(1 for word in query_words if word in content_lower)
        
        # Calculate score as percentage of matching words
        if len(query_words) == 0:
            return 0.0
        
        return matches / len(query_words)
    
    @staticmethod
    def find_most_relevant_document(
        documents: List[DocumentContentResponse],
        query: str
    ) -> Tuple[Optional[DocumentContentResponse], float]:
        """
        Find the most relevant document for a query from a list of documents
        
        Args:
            documents: List of documents to search
            query: User query
            
        Returns:
            Tuple of (most relevant document, relevance score)
        """
        if not documents:
            return None, 0.0
        
        best_doc = None
        best_score = 0.0
        
        for doc in documents:
            score = RAGServiceBase.calculate_document_relevance(
                doc.doc_content if doc.doc_content else "",
                query
            )
            if score > best_score:
                best_score = score
                best_doc = doc
        
        return best_doc, best_score
    
    @abstractmethod
    async def generate_response(
        self,
        document: DocumentContentResponse,
        user_query: str
    ) -> ChatQueryResponse:
        """Generate response - to be implemented by subclasses"""
        pass
    
    async def generate_response_from_multiple_documents(
        self,
        documents: List[DocumentContentResponse],
        user_query: str
    ) -> MultiDocChatResponse:
        """
        Generate response by searching across multiple documents
        
        Args:
            documents: List of documents to search
            user_query: User's question
            
        Returns:
            MultiDocChatResponse with answer from most relevant document
        """
        if not documents:
            return MultiDocChatResponse(
                document_id=0,
                document_title="No Documents",
                user_query=user_query,
                chatbot_response="No documents available to search. Please upload documents first.",
                timestamp=datetime.utcnow(),
                relevance_score=0.0,
                searched_documents=0
            )
        
        # Find the most relevant document
        best_doc, relevance_score = self.find_most_relevant_document(documents, user_query)
        
        if not best_doc or relevance_score == 0.0:
            # No relevant document found, try to give a general response
            # Use the first document as fallback
            best_doc = documents[0]
            relevance_score = 0.0
        
        # Generate response using the best matching document
        response = await self.generate_response(best_doc, user_query)
        
        return MultiDocChatResponse(
            document_id=response.document_id,
            document_title=response.document_title,
            user_query=user_query,
            chatbot_response=response.chatbot_response,
            timestamp=datetime.utcnow(),
            relevance_score=relevance_score,
            searched_documents=len(documents)
        )


class SimpleRAGService(RAGServiceBase):
    """
    Simplified RAG Service for development/testing without external LLM
    Uses chunking and keyword matching with template-based responses
    """
    
    async def generate_response(
        self,
        document: DocumentContentResponse,
        user_query: str
    ) -> ChatQueryResponse:
        """
        Generate simple response based on keyword matching and chunking
        
        Args:
            document: Document with content to use as context
            user_query: User's question
            
        Returns:
            ChatQueryResponse with template-based response
        """
        try:
            # Safely get document content
            doc_content = document.doc_content if document and document.doc_content else ""
            doc_title = document.doc_title if document and document.doc_title else "Unknown Document"
            doc_id = document.id if document else 0
            
            logger.debug(f"SimpleRAG processing document {doc_id}, content length: {len(doc_content)}")
            
            if not doc_content or len(doc_content.strip()) < 50:
                response_text = f"The document '{doc_title}' appears to be empty or too short to analyze. Please ensure the document has content."
                logger.warning(f"No content found for document {doc_id}")
            else:
                # Split document into chunks
                chunks = self.chunk_document(
                    doc_content,
                    chunk_size=settings.RAG_CHUNK_SIZE,
                    overlap=settings.RAG_OVERLAP
                )
                
                if not chunks:
                    response_text = f"The document '{doc_title}' appears to be empty or too short to analyze."
                    logger.warning(f"No chunks found for document {doc_id}")
                else:
                    # Find relevant chunks
                    relevant_chunks = self.find_relevant_chunks(
                        chunks,
                        user_query,
                        top_k=settings.RAG_TOP_K_RESULTS
                    )
                    
                    if relevant_chunks:
                        context_preview = " ".join(relevant_chunks)[:500]
                        response_text = f"Based on the document '{doc_title}', I found relevant information:\n\n" \
                                       f"**Context found:**\n{context_preview}...\n\n" \
                                       f"**Your question:** {user_query}\n\n" \
                                       f"Note: This is a keyword-based response. For AI-powered analysis, ensure Ollama is running."
                    else:
                        # No matching chunks, provide general summary
                        summary = doc_content[:500] if len(doc_content) > 500 else doc_content
                        response_text = f"I couldn't find specific information about '{user_query}' in the document '{doc_title}'.\n\n" \
                                       f"**Document preview:**\n{summary}...\n\n" \
                                       f"Try rephrasing your question or using different keywords."
            
            chat_response = ChatQueryResponse(
                document_id=doc_id,
                document_title=doc_title,
                user_query=user_query,
                chatbot_response=response_text,
                timestamp=datetime.utcnow()
            )
            
            logger.info(f"Simple RAG response generated for document {doc_id}")
            return chat_response
            
        except Exception as e:
            logger.error(f"Error generating simple RAG response: {e}", exc_info=True)
            # Return a fallback response instead of raising
            return ChatQueryResponse(
                document_id=document.id if document else 0,
                document_title=document.doc_title if document else "Unknown",
                user_query=user_query,
                chatbot_response=f"I encountered an error processing your request. Please try again or select a different document. Error: {str(e)}",
                timestamp=datetime.utcnow()
            )


class RAGServiceWithOpenAI(RAGServiceBase):
    """
    RAG Service with OpenAI LLM integration for production use
    Requires OPENAI_API_KEY environment variable
    Uses proper context retrieval and LLM-based response generation
    """
    
    def __init__(self):
        """Initialize RAG service with OpenAI"""
        self.llm = None
        self.available = False
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize OpenAI LLM"""
        try:
            if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "sk-your-openai-key-here":
                logger.warning("OPENAI_API_KEY not configured. OpenAI RAG will be unavailable.")
                self.available = False
                return
            
            from langchain_openai import ChatOpenAI
            
            self.llm = ChatOpenAI(
                model_name=settings.OPENAI_MODEL or "gpt-4",
                temperature=settings.OPENAI_TEMPERATURE or 0.7,
                max_tokens=settings.OPENAI_MAX_TOKENS or 2000,
                api_key=settings.OPENAI_API_KEY
            )
            self.available = True
            logger.info(f"OpenAI RAG Service initialized with model: {settings.OPENAI_MODEL}")
            
        except ImportError:
            logger.warning("LangChain not available. OpenAI RAG will use fallback.")
            self.available = False
        except Exception as e:
            logger.error(f"Error initializing OpenAI RAG Service: {e}")
            self.available = False
    
    async def generate_response(
        self,
        document: DocumentContentResponse,
        user_query: str
    ) -> ChatQueryResponse:
        """
        Generate response using OpenAI LLM with RAG context
        Falls back to SimpleRAGService if OpenAI not available
        
        Args:
            document: Document with content to use as context
            user_query: User's question
            
        Returns:
            ChatQueryResponse with LLM-generated response
        """
        if not self.available or not self.llm:
            logger.info("OpenAI not available, falling back to SimpleRAGService")
            simple_rag = SimpleRAGService()
            return await simple_rag.generate_response(document, user_query)
        
        try:
            # Split document into chunks
            chunks = self.chunk_document(
                document.doc_content,
                chunk_size=settings.RAG_CHUNK_SIZE,
                overlap=settings.RAG_OVERLAP
            )
            
            if not chunks:
                # No content to work with
                response_text = f"The document '{document.doc_title}' appears to be empty or too short to analyze."
                logger.warning(f"No chunks found for document {document.id}")
            else:
                # Find most relevant chunks for context
                relevant_chunks = self.find_relevant_chunks(
                    chunks,
                    user_query,
                    top_k=settings.RAG_TOP_K_RESULTS
                )
                
                context = "\n---\n".join(relevant_chunks) if relevant_chunks else document.doc_content[:2000]
                
                # Prepare prompt with context
                prompt_text = f"""{self.SYSTEM_PROMPT}

Document Title: {document.doc_title}

Document Content (Context):
---
{context}
---

User Question: {user_query}

Please provide a helpful and accurate answer based ONLY on the document content above:"""
                
                # Generate response using OpenAI
                response = self.llm.invoke(prompt_text)
                response_text = response.content if hasattr(response, 'content') else str(response)
            
            chat_response = ChatQueryResponse(
                document_id=document.id,
                document_title=document.doc_title,
                user_query=user_query,
                chatbot_response=response_text,
                timestamp=datetime.utcnow()
            )
            
            logger.info(f"OpenAI RAG Response generated for document {document.id}")
            return chat_response
            
        except Exception as e:
            logger.error(f"Error generating OpenAI RAG response: {e}")
            # Fallback to simple service
            simple_rag = SimpleRAGService()
            return await simple_rag.generate_response(document, user_query)


class RAGServiceWithOllama(RAGServiceBase):
    """
    RAG Service with Ollama/Llama LLM integration for local use
    Uses local Llama models (no API key needed, free)
    Requires Ollama to be running on the configured host/port
    """
    
    def __init__(self):
        """Initialize RAG service with Ollama"""
        self.llm = None
        self.available = False
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize Ollama LLM"""
        try:
            from langchain_community.llms import Ollama
            
            ollama_base_url = f"{settings.OLLAMA_HOST}:{settings.OLLAMA_PORT}"
            
            self.llm = Ollama(
                base_url=ollama_base_url,
                model=settings.OLLAMA_MODEL or "llama3.2",
                temperature=settings.OLLAMA_TEMPERATURE or 0.7,
                num_predict=settings.OLLAMA_MAX_TOKENS or 2000
            )
            
            # Test connection
            self._test_connection()
            self.available = True
            logger.info(f"Ollama RAG Service initialized with model: {settings.OLLAMA_MODEL} at {ollama_base_url}")
            
        except ImportError:
            logger.warning("langchain_community not available. Install with: pip install langchain-community")
            self.available = False
        except Exception as e:
            logger.error(f"Error initializing Ollama RAG Service: {e}")
            logger.error("Make sure Ollama is running: ollama serve")
            self.available = False
    
    def _test_connection(self):
        """Test connection to Ollama"""
        try:
            import requests
            response = requests.get(f"{settings.OLLAMA_HOST}:{settings.OLLAMA_PORT}/api/tags", timeout=2)
            if response.status_code != 200:
                raise Exception("Ollama server not responding")
            logger.info("Ollama connection successful")
        except Exception as e:
            logger.warning(f"Ollama connection test failed: {e}")
            raise
    
    async def generate_response(
        self,
        document: DocumentContentResponse,
        user_query: str
    ) -> ChatQueryResponse:
        """
        Generate response using Ollama/Llama with RAG context
        Falls back to SimpleRAGService if Ollama not available
        
        Args:
            document: Document with content to use as context
            user_query: User's question
            
        Returns:
            ChatQueryResponse with LLM-generated response
        """
        if not self.available or not self.llm:
            logger.info("Ollama not available, falling back to SimpleRAGService")
            simple_rag = SimpleRAGService()
            return await simple_rag.generate_response(document, user_query)
        
        try:
            # Split document into chunks
            chunks = self.chunk_document(
                document.doc_content,
                chunk_size=settings.RAG_CHUNK_SIZE,
                overlap=settings.RAG_OVERLAP
            )
            
            if not chunks:
                # No content to work with
                response_text = f"The document '{document.doc_title}' appears to be empty or too short to analyze."
                logger.warning(f"No chunks found for document {document.id}")
            else:
                # Find most relevant chunks for context
                relevant_chunks = self.find_relevant_chunks(
                    chunks,
                    user_query,
                    top_k=settings.RAG_TOP_K_RESULTS
                )
                
                context = "\n---\n".join(relevant_chunks) if relevant_chunks else document.doc_content[:2000]
                
                # Prepare prompt with context
                prompt_text = f"""{self.SYSTEM_PROMPT}

Document Title: {document.doc_title}

Document Content (Context):
---
{context}
---

User Question: {user_query}

Please provide a helpful and accurate answer based ONLY on the document content above:"""
                
                # Generate response using Ollama/Llama
                response_text = self.llm.invoke(prompt_text)
            
            chat_response = ChatQueryResponse(
                document_id=document.id,
                document_title=document.doc_title,
                user_query=user_query,
                chatbot_response=response_text,
                timestamp=datetime.utcnow()
            )
            
            logger.info(f"Ollama RAG Response generated for document {document.id}")
            return chat_response
            
        except Exception as e:
            logger.error(f"Error generating Ollama RAG response: {e}", exc_info=True)
            # Fallback to simple service - but catch its errors too
            try:
                simple_rag = SimpleRAGService()
                return await simple_rag.generate_response(document, user_query)
            except Exception as e2:
                logger.error(f"SimpleRAG fallback also failed: {e2}")
                return ChatQueryResponse(
                    document_id=document.id if document else 0,
                    document_title=document.doc_title if document else "Unknown",
                    user_query=user_query,
                    chatbot_response=f"I encountered an error processing your request. Please try again. Error: {str(e)}",
                    timestamp=datetime.utcnow()
                )


# Factory function to create appropriate RAG service
def create_rag_service():
    """
    Create RAG service instance based on configuration
    
    Priority:
    1. Ollama/Llama (local, free, recommended)
    2. OpenAI (requires API key)
    3. Simple RAG (fallback, no LLM needed)
    
    Returns appropriate RAG service based on LLM_PROVIDER configuration
    """
    provider = (settings.LLM_PROVIDER or "ollama").lower()
    
    if provider == "ollama":
        logger.info("Using Ollama RAG Service (Local Llama)")
        try:
            return RAGServiceWithOllama()
        except Exception as e:
            logger.warning(f"Ollama not available: {e}, trying OpenAI...")
            try:
                return RAGServiceWithOpenAI()
            except Exception as e2:
                logger.warning(f"OpenAI not available: {e2}, using Simple RAG")
                return SimpleRAGService()
    
    elif provider == "openai":
        logger.info("Using OpenAI RAG Service")
        try:
            return RAGServiceWithOpenAI()
        except Exception as e:
            logger.warning(f"OpenAI not available: {e}, trying Ollama...")
            try:
                return RAGServiceWithOllama()
            except Exception as e2:
                logger.warning(f"Ollama not available: {e2}, using Simple RAG")
                return SimpleRAGService()
    
    else:
        logger.warning(f"Unknown provider: {provider}, defaulting to Ollama")
        try:
            return RAGServiceWithOllama()
        except:
            return SimpleRAGService()


_default_rag_service = None

def get_rag_service():
    """
    Lazily create and return the RAG service instance.

    Initializing heavy LLM clients (Ollama/OpenAI) can perform
    network calls at import time which may block request handling.
    Use this getter to initialize on first use instead of module import.
    """
    global _default_rag_service
    if _default_rag_service is None:
        try:
            _default_rag_service = create_rag_service()
        except Exception as e:
            logger.error(f"Failed to create RAG service: {e}")
            # Fallback to SimpleRAGService to avoid blocking the API
            _default_rag_service = SimpleRAGService()
    return _default_rag_service

# Helper functions to create optional providers on demand
def create_openai_rag_service():
    try:
        return RAGServiceWithOpenAI()
    except Exception as e:
        logger.warning(f"OpenAI RAG Service not available: {e}")
        return None

def create_ollama_rag_service():
    try:
        return RAGServiceWithOllama()
    except Exception as e:
        logger.warning(f"Ollama RAG Service not available: {e}")
        return None
