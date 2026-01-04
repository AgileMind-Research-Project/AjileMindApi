"""
Model Loader
Handles loading and initialization of the Mistral 7B model using llama-cpp-python
"""
from llama_cpp import Llama
from typing import Optional
import logging
from pathlib import Path

try:
    from .config import LLM_CONFIG, MODEL_PATH
except ImportError:
    from config import LLM_CONFIG, MODEL_PATH

logger = logging.getLogger(__name__)


class ModelLoader:
    """Singleton class to load and manage the LLM model"""
    
    _instance: Optional['ModelLoader'] = None
    _model: Optional[Llama] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the model loader"""
        if not hasattr(self, 'initialized'):
            self.initialized = False
    
    def load_model(self, **kwargs) -> Llama:
        """
        Load the Mistral 7B model
        
        Args:
            **kwargs: Override default LLM_CONFIG parameters
            
        Returns:
            Llama: Loaded model instance
            
        Raises:
            FileNotFoundError: If model file doesn't exist
            Exception: If model loading fails
        """
        if self._model is not None:
            logger.info("Model already loaded, returning existing instance")
            return self._model
        
        # Check if model file exists
        if not Path(MODEL_PATH).exists():
            raise FileNotFoundError(
                f"Model file not found at {MODEL_PATH}. "
                f"Please ensure the model is downloaded to the correct location."
            )
        
        # Merge config with any overrides
        config = {**LLM_CONFIG, **kwargs}
        
        logger.info(f"Loading model from {config['model_path']}")
        logger.info(f"Model configuration: {config}")
        
        try:
            self._model = Llama(**config)
            self.initialized = True
            logger.info("Model loaded successfully")
            return self._model
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            raise
    
    def get_model(self) -> Optional[Llama]:
        """
        Get the loaded model instance
        
        Returns:
            Optional[Llama]: Model instance if loaded, None otherwise
        """
        return self._model
    
    def unload_model(self):
        """Unload the model from memory"""
        if self._model is not None:
            del self._model
            self._model = None
            self.initialized = False
            logger.info("Model unloaded from memory")
    
    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self._model is not None and self.initialized


# Global instance
model_loader = ModelLoader()


def get_model() -> Llama:
    """
    Get or load the model
    
    Returns:
        Llama: Loaded model instance
    """
    if not model_loader.is_loaded():
        return model_loader.load_model()
    return model_loader.get_model()
