"""
LLM Utilities

Utility functions for LLM initialization and management.
Supports OpenAI, Anthropic Claude, and Google Gemini.
"""

from typing import Optional, Dict, Any
from app.core.config import settings
from app.core.logger import logger


class LLMFactory:
    """Factory class for creating LLM instances"""
    
    @staticmethod
    def create_openai_llm():
        """Create OpenAI LLM instance"""
        try:
            if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "sk-your-openai-key-here":
                logger.warning("OPENAI_API_KEY not configured")
                return None
            
            from langchain_openai import ChatOpenAI
            
            llm = ChatOpenAI(
                model_name=settings.OPENAI_MODEL or "gpt-4",
                temperature=float(settings.OPENAI_TEMPERATURE or 0.7),
                max_tokens=int(settings.OPENAI_MAX_TOKENS or 2000),
                api_key=settings.OPENAI_API_KEY
            )
            logger.info(f"OpenAI LLM created: {settings.OPENAI_MODEL}")
            return llm
            
        except Exception as e:
            logger.error(f"Error creating OpenAI LLM: {e}")
            return None
    
    @staticmethod
    def create_ollama_llm():
        """Create Ollama/Llama LLM instance (local)"""
        try:
            from langchain_community.llms import Ollama
            
            ollama_base_url = f"{settings.OLLAMA_HOST}:{settings.OLLAMA_PORT}"
            
            llm = Ollama(
                base_url=ollama_base_url,
                model=settings.OLLAMA_MODEL or "llama3.2",
                temperature=float(settings.OLLAMA_TEMPERATURE or 0.7),
                num_predict=int(settings.OLLAMA_MAX_TOKENS or 2000)
            )
            logger.info(f"Ollama LLM created: {settings.OLLAMA_MODEL} at {ollama_base_url}")
            return llm
            
        except Exception as e:
            logger.error(f"Error creating Ollama LLM: {e}")
            return None
    
    @staticmethod
    def create_anthropic_llm():
        """Create Anthropic Claude LLM instance"""
        try:
            from langchain_anthropic import ChatAnthropic
            
            anthropic_key = getattr(settings, 'ANTHROPIC_API_KEY', None)
            if not anthropic_key:
                logger.warning("ANTHROPIC_API_KEY not configured")
                return None
            
            llm = ChatAnthropic(
                model="claude-3-opus-20240229",
                temperature=0.7,
                max_tokens=2048,
                api_key=anthropic_key
            )
            logger.info("Anthropic Claude LLM created")
            return llm
            
        except Exception as e:
            logger.error(f"Error creating Anthropic LLM: {e}")
            return None
    
    @staticmethod
    def create_gemini_llm():
        """Create Google Gemini LLM instance"""
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            
            google_key = getattr(settings, 'GOOGLE_API_KEY', None)
            if not google_key:
                logger.warning("GOOGLE_API_KEY not configured")
                return None
            
            llm = ChatGoogleGenerativeAI(
                model="gemini-pro",
                temperature=0.7,
                api_key=google_key
            )
            logger.info("Google Gemini LLM created")
            return llm
            
        except Exception as e:
            logger.error(f"Error creating Google Gemini LLM: {e}")
            return None
    
    @staticmethod
    def get_llm(provider: Optional[str] = None):
        """
        Get LLM instance based on provider
        
        Args:
            provider: LLM provider name (openai, ollama, anthropic, gemini)
            
        Returns:
            LLM instance or None if not available
        """
        provider = provider or settings.LLM_PROVIDER or "ollama"
        
        if provider.lower() == "ollama":
            return LLMFactory.create_ollama_llm()
        elif provider.lower() == "openai":
            return LLMFactory.create_openai_llm()
        elif provider.lower() == "anthropic":
            return LLMFactory.create_anthropic_llm()
        elif provider.lower() == "gemini":
            return LLMFactory.create_gemini_llm()
        else:
            logger.warning(f"Unknown LLM provider: {provider}, falling back to Ollama")
            return LLMFactory.create_ollama_llm()  # Fallback to Ollama (local)


class PromptTemplates:
    """Predefined prompt templates for different use cases"""
    
    RAG_SYSTEM_PROMPT = """You are a helpful assistant with access to document context. 
Use ONLY the provided document content to answer the user's question.
Be accurate, concise, and factual.
If the answer is not in the document, clearly state that information is not available in the provided document.
Do NOT use outside knowledge or make assumptions beyond the document content."""
    
    DOCUMENT_SUMMARY_PROMPT = """Provide a concise summary of the following document.
Focus on the main points and key information.
Keep the summary to 2-3 paragraphs maximum.

Document Content:
{content}

Summary:"""
    
    DOCUMENT_QA_PROMPT = """Based on the following document content, answer the user's question.
Provide a clear and accurate answer.
If the information is not in the document, state that clearly.

Document Title: {title}

Document Content:
{content}

User Question: {question}

Answer:"""
    
    DOCUMENT_SEARCH_PROMPT = """Based on the following document chunks, find the most relevant information to answer the user's question.

Document Chunks:
{chunks}

User Question: {question}

Relevant Information:"""
    
    @staticmethod
    def format_rag_prompt(
        document_title: str,
        document_content: str,
        user_query: str,
        context_chunks: Optional[list] = None
    ) -> str:
        """
        Format RAG prompt with document context
        
        Args:
            document_title: Title of the document
            document_content: Full or chunked document content
            user_query: User's question
            context_chunks: Optional list of relevant chunks
            
        Returns:
            Formatted prompt string
        """
        context = "\n---\n".join(context_chunks) if context_chunks else document_content
        
        return f"""{PromptTemplates.RAG_SYSTEM_PROMPT}

Document Title: {document_title}

Document Content:
---
{context}
---

User Question: {user_query}

Please provide a helpful and accurate answer based ONLY on the document content above:"""
    
    @staticmethod
    def format_summary_prompt(document_content: str, document_title: str = "") -> str:
        """Format document summary prompt"""
        return f"""Title: {document_title}

{PromptTemplates.DOCUMENT_SUMMARY_PROMPT}"""
    
    @staticmethod
    def format_qa_prompt(
        title: str,
        content: str,
        question: str
    ) -> str:
        """Format Q&A prompt"""
        return PromptTemplates.DOCUMENT_QA_PROMPT.format(
            title=title,
            content=content,
            question=question
        )


class LLMResponseFormatter:
    """Utility class for formatting LLM responses"""
    
    @staticmethod
    def extract_text(response: Any) -> str:
        """
        Extract text from LLM response
        
        Args:
            response: LLM response object
            
        Returns:
            Extracted text
        """
        if hasattr(response, 'content'):
            return response.content
        elif hasattr(response, 'text'):
            return response.text
        else:
            return str(response)
    
    @staticmethod
    def clean_response(text: str) -> str:
        """
        Clean and format LLM response
        
        Args:
            text: Raw response text
            
        Returns:
            Cleaned response text
        """
        # Remove markdown code blocks if present
        if text.startswith("```"):
            lines = text.split("\n")
            if len(lines) > 2:
                text = "\n".join(lines[1:-1])
        
        # Strip excessive whitespace
        text = text.strip()
        
        return text
    
    @staticmethod
    def format_for_json(text: str, max_length: int = None) -> str:
        """
        Format response for JSON serialization
        
        Args:
            text: Response text
            max_length: Optional maximum length
            
        Returns:
            JSON-safe text
        """
        text = LLMResponseFormatter.clean_response(text)
        
        if max_length and len(text) > max_length:
            text = text[:max_length] + "..."
        
        return text


class TokenCounter:
    """Utility class for token counting"""
    
    @staticmethod
    def count_tokens(text: str, model: str = "gpt-4") -> int:
        """
        Estimate token count for text
        Rough estimate: ~1 token per 4 characters
        
        Args:
            text: Text to count
            model: Model name for accurate counting (if available)
            
        Returns:
            Estimated token count
        """
        try:
            import tiktoken
            
            # Try to use tiktoken for accurate count
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(text))
            
        except Exception:
            # Fallback to rough estimate
            return len(text) // 4
    
    @staticmethod
    def truncate_for_model(text: str, max_tokens: int = 2000) -> str:
        """
        Truncate text to fit within token limit
        
        Args:
            text: Text to truncate
            max_tokens: Maximum allowed tokens
            
        Returns:
            Truncated text
        """
        # Rough estimate: truncate to ~4 characters per token
        max_chars = max_tokens * 4
        
        if len(text) > max_chars:
            return text[:max_chars] + "..."
        
        return text


# Singleton instances
_llm_instance = None

def get_llm():
    """Get or create LLM instance"""
    global _llm_instance
    
    if _llm_instance is None:
        _llm_instance = LLMFactory.get_llm()
    
    return _llm_instance


def reset_llm():
    """Reset LLM instance"""
    global _llm_instance
    _llm_instance = None
