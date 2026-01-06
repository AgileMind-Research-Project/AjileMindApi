"""
Model Loader for Mistral-7B GGUF
Handles lazy loading and caching of the LLM model
"""

import os
from typing import Optional, Any
from pathlib import Path

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

from app.core.logger import logger


import json

class MockLlamaModel:
    """Mock Llama model for testing/development"""
    def __call__(self, prompt, **kwargs):
        # Simulate processing delay
        import time
        time.sleep(1.5)
        
        # Return mock JSON response matching the prompt context roughly or generic
        mock_response = [
            {
                "ticket_id": "TASK-101",
                "status": "DONE",
                "extracted_context": "I've completed the login page implementation yesterday.",
                "ai_confidence_score": 0.95,
                "ai_reasoning": "Speaker explicitly mentions completion of the task."
            },
            {
                "ticket_id": "TASK-102",
                "status": "IN_PROGRESS",
                "extracted_context": "I'm currently working on the user profile settings.",
                "ai_confidence_score": 0.88,
                "ai_reasoning": "Speaker indicates ongoing work ('currently working on')."
            },
            {
                "ticket_id": "TASK-103",
                "status": "BLOCKED",
                "blocker": "Waiting for database credentials from DevOps.",
                "extracted_context": "I can't proceed with the API integration until I get the DB credentials.",
                "ai_confidence_score": 0.92,
                "ai_reasoning": "Speaker uses 'can't proceed' and states a dependency."
            },
            {
                "ticket_id": "TASK-104", 
                "status": "TODO",
                "extracted_context": "Next sprint we need to look at the notification system.",
                "ai_confidence_score": 0.85,
                "ai_reasoning": "Speaker mentions future work ('Next sprint')."
             }
        ]
        
        return {
            "choices": [
                {
                    "text": json.dumps(mock_response)
                }
            ]
        }

class ModelLoader:
    """Singleton model loader for Mistral-7B"""
    
    _instance: Optional['ModelLoader'] = None
    _model: Optional[Any] = None # Can be Llama or MockLlamaModel
    _model_path: str = "D:\\Projects\\Research\\Project\\AjileMindApi\\app\\ai\\agent\\models\\mistral-7b-instruct-v0.2.Q4_K_S.gguf"
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize model loader"""
        if not hasattr(self, 'initialized'):
            self.initialized = True
            logger.info("ModelLoader initialized")
    
    def load_model(self, force_reload: bool = False) -> Any:
        """
        Load or return cached Mistral-7B model
        
        Args:
            force_reload: Force reload even if model is cached
            
        Returns:
            Llama model instance or MockLlamaModel
        """
        # Return cached model if available
        if self._model is not None and not force_reload:
            logger.debug("Returning cached model")
            return self._model
        
        use_mock = False
        if Llama is None:
            logger.warning("llama-cpp-python not installed. Using MOCK model.")
            use_mock = True
        elif not os.path.exists(self._model_path):
            logger.warning(f"Model file not found: {self._model_path}. Using MOCK model.")
            use_mock = True
            
        if use_mock:
            self._model = MockLlamaModel()
            return self._model
        
        try:
            logger.info(f"Loading Mistral-7B model from: {self._model_path}")
            logger.info("This may take a few moments...")
            
            self._model = Llama(
                model_path=self._model_path,
                n_ctx=4096,  # Context window
                n_threads=8,  # CPU threads (adjust based on your system)
                n_gpu_layers=0,  # Set > 0 if you have GPU support
                verbose=False,
                n_batch=512,  # Batch size for prompt processing
            )
            
            logger.info("✓ Mistral-7B model loaded successfully")
            logger.info(f"Model size: {os.path.getsize(self._model_path) / (1024**3):.2f} GB")
            
            return self._model
        
        except Exception as e:
            logger.error(f"Failed to load Mistral-7B model: {e}. Using MOCK model.")
            self._model = MockLlamaModel()
            return self._model
    
    def unload_model(self):
        """Unload model from memory"""
        if self._model is not None:
            logger.info("Unloading Mistral-7B model from memory")
            self._model = None
    
    def is_loaded(self) -> bool:
        """Check if model is currently loaded"""
        return self._model is not None
    
    def get_model_info(self) -> dict:
        """Get information about the model"""
        return {
            "model_path": self._model_path,
            "is_loaded": self.is_loaded(),
            "model_exists": os.path.exists(self._model_path),
            "model_size_gb": os.path.getsize(self._model_path) / (1024**3) if os.path.exists(self._model_path) else 0,
            "llama_cpp_available": Llama is not None,
            "using_mock": isinstance(self._model, MockLlamaModel) if self._model else False
        }


# Global instance
model_loader = ModelLoader()
