"""
Mistral-7B LLM Client using llama-cpp-python
"""

from typing import Optional, Dict, Any
import json
import os
from pathlib import Path

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None
    print("Warning: llama-cpp-python not installed. Install with: pip install llama-cpp-python")

from app.core.logger import logger


class MistralClient:
    """Wrapper for Mistral-7B GGUF model"""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize Mistral client
        
        Args:
            model_path: Path to .gguf model file
        """
        if model_path is None:
            # Default path from user's specification
            model_path = "D:\\Projects\\Research\\Project\\AjileMindApi\\app\\ai\\agent\\models\\mistral-7b-instruct-v0.2.Q4_K_S.gguf"
        
        self.model_path = model_path
        self.llm = None
        self.mock_mode = False
        
        if Llama is None:
            logger.warning("llama-cpp-python not installed. Switching to MOCK MODE.")
            self.mock_mode = True
            return
        
        if not os.path.exists(model_path):
            logger.warning(f"Model file not found: {model_path}. Switching to MOCK MODE.")
            self.mock_mode = True
            return
        
        try:
            logger.info(f"Loading Mistral-7B model from: {model_path}")
            self.llm = Llama(
                model_path=model_path,
                n_ctx=4096,  # Context window
                n_threads=8,  # CPU threads
                n_gpu_layers=0,  # Set > 0 for GPU, but starting with CPU-only
                verbose=False
            )
            logger.info("✓ Mistral-7B model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}. Switching to MOCK MODE.")
            self.mock_mode = True
            self.llm = None
    
    def generate(
        self, 
        prompt: str, 
        max_tokens: int = 2048,
        temperature: float = 0.2,  # Lower for more deterministic output
        top_p: float = 0.95,
        stop: Optional[list] = None
    ) -> Optional[str]:
        """
        Generate text from prompt
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            top_p: Nucleus sampling parameter
            stop: Stop sequences
            
        Returns:
            Generated text or None if error
        """
        if self.mock_mode:
            logger.info("Generating MOCK response")
            import time
            time.sleep(2) # Simulate processing time
            return json.dumps([
                {
                    "ticket_id": "TASK-101",
                    "detected_status": "DONE",
                    "extracted_context": "I've completed the login page implementation yesterday.",
                    "ai_confidence_score": 0.95,
                    "ai_reasoning": "Speaker explicitly mentions completion of the task."
                },
                {
                    "ticket_id": "TASK-102",
                    "detected_status": "IN_PROGRESS",
                    "extracted_context": "I'm currently working on the user profile settings.",
                    "ai_confidence_score": 0.88,
                    "ai_reasoning": "Speaker indicates ongoing work ('currently working on')."
                },
                {
                    "ticket_id": "TASK-103",
                    "detected_status": "BLOCKED",
                    "blocker_description": "Waiting for database credentials from DevOps.",
                    "extracted_context": "I can't proceed with the API integration until I get the DB credentials.",
                    "ai_confidence_score": 0.92,
                    "ai_reasoning": "Speaker uses 'can't proceed' and states a dependency."
                }
            ])

        if self.llm is None:
            logger.error("Model not loaded and not in mock mode")
            return None
        
        try:
            response = self.llm(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop=stop or ["```\n\n", "\n\nInput:", "\n\nEXAMPLE"],
                echo=False
            )
            
            if response and 'choices' in response and len(response['choices']) > 0:
                return response['choices'][0]['text'].strip()
            
            return None
        
        except Exception as e:
            logger.error(f"Generation error: {e}")
            return None
    
    def extract_json_from_response(self, response_text: str) -> Optional[list]:
        """
        Extract and parse JSON array from LLM response
        
        Args:
            response_text: Raw LLM output
            
        Returns:
            Parsed JSON list or None
        """
        if not response_text:
            return None
        
        try:
            # Try to find JSON array in response
            import re
            json_match = re.search(r'\[[\s\S]*\]', response_text)
            
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
            
            # If no array found, try parsing entire response
            return json.loads(response_text)
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            logger.debug(f"Response text: {response_text}")
            return None
    
    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self.llm is not None or self.mock_mode
