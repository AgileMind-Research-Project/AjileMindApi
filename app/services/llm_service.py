"""
LLM Service for Ollama Integration

Handles communication with local Ollama or remote LLM servers.
Supports switchable endpoints for development and production.
"""

import os
import json
from typing import List, Dict, Any, Optional
import ollama
from app.core.config import settings
from app.core.logger import logger


class LLMService:
    """Service for interacting with Ollama LLM"""
    
    def __init__(self):
        """Initialize LLM service with configured endpoint"""
        self.llm_url = settings.LLM_API_URL
        self.model_name = settings.LLM_MODEL_NAME
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS
        
        # Configure Ollama client
        if self.llm_url != "http://localhost:11434":
            # For remote servers, set custom host
            os.environ['OLLAMA_HOST'] = self.llm_url
        
        logger.info(f"LLM Service initialized: {self.llm_url} with model {self.model_name}")
    
    async def generate_response(
        self,
        prompt: str,
        context_chunks: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate LLM response with optional context.
        
        Args:
            prompt: User question/prompt
            context_chunks: Retrieved context chunks from vector DB
            system_prompt: System instructions for the LLM
        
        Returns:
            LLM response with metadata
        """
        try:
            logger.info(f"Generating LLM response for prompt: {prompt[:100]}...")
            
            # Build context-aware prompt
            full_prompt = self._build_rag_prompt(prompt, context_chunks, system_prompt)
            
            # Call Ollama API
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {
                        'role': 'user',
                        'content': full_prompt
                    }
                ],
                options={
                    'temperature': self.temperature,
                    'num_predict': self.max_tokens
                }
            )
            
            answer = response['message']['content']
            
            # Extract source references if context was provided
            sources = []
            if context_chunks:
                sources = [
                    {
                        "filename": chunk.get("filename", "Unknown"),
                        "chunk_index": chunk.get("chunk_index", 0),
                        "relevance_score": chunk.get("score", 0.0)
                    }
                    for chunk in context_chunks[:3]  # Top 3 sources
                ]
            
            result = {
                "answer": answer,
                "sources": sources,
                "model": self.model_name,
                "prompt_tokens": len(full_prompt.split()),  # Approximate
                "has_context": bool(context_chunks)
            }
            
            logger.info(f"Generated response with {len(sources)} source references")
            
            return result
        
        except Exception as e:
            logger.error(f"LLM generation failed: {str(e)}", exc_info=True)
            raise Exception(f"Failed to generate LLM response: {str(e)}")
    
    def _build_rag_prompt(
        self,
        user_question: str,
        context_chunks: Optional[List[Dict[str, Any]]],
        system_prompt: Optional[str]
    ) -> str:
        """
        Build RAG prompt with context and instructions.
        
        Args:
            user_question: User's question
            context_chunks: Retrieved context from documents
            system_prompt: Optional system instructions
        
        Returns:
            Formatted prompt for LLM
        """
        # Default system prompt for document Q&A
        default_system = """You are a helpful AI assistant that answers questions based on document content.

Instructions:
- Read the document content carefully and provide direct, accurate answers
- Answer questions using ONLY the information from the document content provided
- Give complete, detailed answers by extracting relevant information from the documents
- If multiple documents are provided, identify which document contains the answer
- If the information is not in the documents, clearly state "I don't have this information in the provided documents."
- Provide specific details, numbers, dates, or quotes from the documents when answering
- Format your answer clearly and professionally"""
        
        system_message = system_prompt or default_system
        
        if not context_chunks:
            # No context available, direct question
            return f"{system_message}\n\nQuestion: {user_question}\n\nAnswer:"
        
        # Build context from chunks
        context_text = "\n\n".join([
            f"Document: {chunk.get('filename', 'Unknown')}\nContent:\n{chunk.get('text', '')}"
            for chunk in context_chunks
        ])
        
        # Assemble RAG prompt
        rag_prompt = f"""{system_message}

Available Document Content:
{context_text}

User Question: {user_question}

Answer (provide direct answer from the document content):"""
        
        return rag_prompt
    
    async def generate_short_response(
        self,
        prompt: str,
        context_chunks: Optional[List[Dict[str, Any]]] = None,
        max_length: int = 200,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a SHORT LLM response (1-3 sentences) using context.
        
        Date-based feature: Used when user selects specific document.
        Forces concise, relevant answers.
        
        Args:
            prompt: User question/prompt
            context_chunks: Retrieved context chunks from vector DB
            max_length: Maximum length in characters (default: 200)
            system_prompt: System instructions for the LLM
        
        Returns:
            Short LLM response with metadata
        """
        try:
            logger.info(f"Generating SHORT LLM response for: {prompt[:100]}...")
            
            # Build short prompt that emphasizes brevity
            full_prompt = self._build_short_rag_prompt(prompt, context_chunks, max_length, system_prompt)
            
            # Call Ollama API with reduced tokens for shorter response
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {
                        'role': 'user',
                        'content': full_prompt
                    }
                ],
                options={
                    'temperature': self.temperature,
                    'num_predict': min(50, self.max_tokens)  # Force shorter responses
                }
            )
            
            answer = response['message']['content'].strip()
            
            # Truncate if still too long
            if len(answer) > max_length:
                answer = answer[:max_length].rsplit(' ', 1)[0] + '...'
            
            # Extract source references if context was provided
            sources = []
            if context_chunks:
                sources = [
                    {
                        "filename": chunk.get("filename", "Unknown"),
                        "chunk_index": chunk.get("chunk_index", 0),
                        "relevance_score": chunk.get("score", 0.0)
                    }
                    for chunk in context_chunks[:2]  # Top 2 sources only
                ]
            
            result = {
                "answer": answer,  # SHORT answer (1-3 sentences)
                "sources": sources,
                "model": self.model_name,
                "prompt_tokens": len(full_prompt.split()),
                "has_context": bool(context_chunks)
            }
            
            logger.info(f"Generated short response ({len(answer)} chars)")
            
            return result
        
        except Exception as e:
            logger.error(f"Short response generation failed: {str(e)}", exc_info=True)
            raise Exception(f"Failed to generate short response: {str(e)}")
    
    def _build_short_rag_prompt(
        self,
        user_question: str,
        context_chunks: Optional[List[Dict[str, Any]]],
        max_length: int,
        system_prompt: Optional[str]
    ) -> str:
        """
        Build SHORT RAG prompt that forces concise answers.
        
        Used for date-based document selection where we want quick, relevant answers.
        
        Args:
            user_question: User's question
            context_chunks: Retrieved context from document
            max_length: Maximum answer length
            system_prompt: Optional system instructions
        
        Returns:
            Formatted short prompt for LLM
        """
        # Emphasis on SHORT, CONCISE responses
        default_system = """You are a concise AI assistant answering questions based on provided documents.

Instructions:
- Answer in 1-3 sentences ONLY
- Be direct and concise
- Use only the provided document content
- Focus on the most relevant information
- If information is not available, say "Not found in document"
- Maximum {max_length} characters"""
        
        system_message = (system_prompt or default_system).format(max_length=max_length)
        
        if not context_chunks:
            return f"{system_message}\n\nQuestion: {user_question}\n\nAnswer (1-3 sentences):"
        
        # Build concise context from first few chunks only
        context_text = "\n".join([
            f"- {chunk.get('text', '')[:300]}"  # Limit chunk preview
            for chunk in context_chunks[:2]  # Use only top 2 chunks
        ])
        
        # Assemble short RAG prompt
        short_prompt = f"""{system_message}

Document Content:
{context_text}

Question: {user_question}

Answer (1-3 sentences, max {max_length} characters):"""
        
        return short_prompt
    
    async def check_model_availability(self) -> Dict[str, Any]:
        """
        Check if the configured model is available.
        
        Returns:
            Status dictionary with model availability
        """
        try:
            # List available models
            models = ollama.list()
            
            models_list = models.get('models', []) if isinstance(models, dict) else []
            available_models = [model.get('name', '') for model in models_list if isinstance(model, dict)]
            model_available = any(self.model_name in model for model in available_models)
            
            return {
                "status": "available" if model_available else "unavailable",
                "configured_model": self.model_name,
                "available_models": available_models,
                "llm_url": self.llm_url
            }
        
        except Exception as e:
            logger.error(f"Failed to check model availability: {str(e)}")
            return {
                "status": "error",
                "configured_model": self.model_name,
                "available_models": [],
                "error": str(e),
                "llm_url": self.llm_url
            }
    
    async def pull_model(self) -> Dict[str, Any]:
        """
        Pull/download the configured model from Ollama.
        
        Returns:
            Pull status dictionary
        """
        try:
            logger.info(f"Pulling model {self.model_name} from Ollama...")
            
            # Pull model
            ollama.pull(self.model_name)
            
            logger.info(f"Successfully pulled model {self.model_name}")
            
            return {
                "status": "success",
                "model": self.model_name,
                "message": f"Model {self.model_name} pulled successfully"
            }
        
        except Exception as e:
            logger.error(f"Failed to pull model {self.model_name}: {str(e)}")
            raise Exception(f"Model pull failed: {str(e)}")
