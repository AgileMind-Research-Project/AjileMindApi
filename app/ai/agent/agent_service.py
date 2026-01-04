"""
Agent Service
Main service for interacting with the Mistral 7B model
"""
from typing import List, Dict, Optional, Generator
import logging
from datetime import datetime

try:
    from .model_loader import get_model
    from .config import (
        SYSTEM_PROMPT,
        INSTRUCTION_TEMPLATE,
        CONVERSATION_TEMPLATE,
        AGENT_CONFIG
    )
except ImportError:
    from model_loader import get_model
    from config import (
        SYSTEM_PROMPT,
        INSTRUCTION_TEMPLATE,
        CONVERSATION_TEMPLATE,
        AGENT_CONFIG
    )

logger = logging.getLogger(__name__)


class AgentService:
    """Service for managing agent interactions with the LLM"""
    
    def __init__(self, system_prompt: Optional[str] = None):
        """
        Initialize the agent service
        
        Args:
            system_prompt: Custom system prompt (uses default if not provided)
        """
        self.model = get_model()
        self.system_prompt = system_prompt or SYSTEM_PROMPT
        self.conversation_history: List[Dict[str, str]] = []
        self.max_history = AGENT_CONFIG["max_conversation_history"]
    
    def generate_response(
        self,
        user_input: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False
    ) -> str:
        """
        Generate a response to user input
        
        Args:
            user_input: User's input text
            max_tokens: Maximum tokens to generate (overrides config)
            temperature: Sampling temperature (overrides config)
            stream: Enable streaming response
            
        Returns:
            str: Generated response
        """
        # Build prompt
        if len(self.conversation_history) == 0:
            prompt = INSTRUCTION_TEMPLATE.format(
                system_prompt=self.system_prompt,
                user_input=user_input
            )
        else:
            history_text = self._format_conversation_history()
            prompt = CONVERSATION_TEMPLATE.format(
                system_prompt=self.system_prompt,
                conversation_history=history_text,
                user_input=user_input
            )
        
        logger.info(f"Generating response for input: {user_input[:50]}...")
        
        # Generate response
        response_kwargs = {}
        if max_tokens is not None:
            response_kwargs['max_tokens'] = max_tokens
        if temperature is not None:
            response_kwargs['temperature'] = temperature
        
        try:
            if stream:
                return self._stream_response(prompt, **response_kwargs)
            else:
                output = self.model(
                    prompt,
                    **response_kwargs,
                    echo=False
                )
                response_text = output['choices'][0]['text'].strip()
                
                # Update conversation history
                self._add_to_history(user_input, response_text)
                
                logger.info("Response generated successfully")
                return response_text
                
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise
    
    def _stream_response(
        self,
        prompt: str,
        **kwargs
    ) -> Generator[str, None, None]:
        """
        Stream response tokens
        
        Args:
            prompt: Formatted prompt
            **kwargs: Additional generation parameters
            
        Yields:
            str: Response tokens
        """
        output = self.model(
            prompt,
            stream=True,
            **kwargs
        )
        
        full_response = ""
        for chunk in output:
            token = chunk['choices'][0]['text']
            full_response += token
            yield token
        
        # Store complete response in history
        # Note: You'll need to track user_input separately for streaming
        logger.info("Streaming response completed")
    
    def _format_conversation_history(self) -> str:
        """Format conversation history for prompt"""
        formatted = []
        for entry in self.conversation_history:
            formatted.append(f"User: {entry['user']}")
            formatted.append(f"Assistant: {entry['assistant']}")
        return "\n".join(formatted)
    
    def _add_to_history(self, user_input: str, assistant_response: str):
        """Add interaction to conversation history"""
        self.conversation_history.append({
            "user": user_input,
            "assistant": assistant_response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Trim history if it exceeds max length
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        logger.info("Conversation history cleared")
    
    def get_history(self) -> List[Dict[str, str]]:
        """Get conversation history"""
        return self.conversation_history.copy()
    
    def set_system_prompt(self, prompt: str):
        """Update system prompt"""
        self.system_prompt = prompt
        logger.info("System prompt updated")
    
    def chat(self, message: str) -> str:
        """
        Simple chat interface
        
        Args:
            message: User message
            
        Returns:
            str: Agent response
        """
        return self.generate_response(message)


# Convenience function
def create_agent(system_prompt: Optional[str] = None) -> AgentService:
    """
    Create a new agent instance
    
    Args:
        system_prompt: Custom system prompt
        
    Returns:
        AgentService: New agent instance
    """
    return AgentService(system_prompt=system_prompt)
