"""
Task Update Extractor - Main AI Service
Uses Mistral-7B with Few-Shot Learning and Chain of Thought
Now uses AgentService for better logging and debugging
"""

from typing import List, Optional
from app.ai.task_extractor.agent_service import agent_service
from app.task_updates_config.models import TaskUpdateExtract
from app.core.logger import logger


class TaskExtractor:
    """AI-powered task update extractor (wrapper for AgentService)"""
    
    def __init__(self):
        """Initialize extractor"""
        self.agent = agent_service
        logger.info("TaskExtractor initialized with AgentService")
    
    def extract_from_transcript(
        self,
        transcript: str,
        meeting_id: str
    ) -> tuple[List[TaskUpdateExtract], float]:
        """
        Extract task updates from meeting transcript using AI
        
        Args:
            transcript: Meeting transcript text
            meeting_id: Meeting ID for logging
            
        Returns:
            Tuple of (extractions list, processing_time_ms)
        """
        logger.info(f"[TaskExtractor] Starting extraction for meeting {meeting_id}")
        
        extractions, processing_time, debug_info = self.agent.extract_task_updates(
            transcript, 
            meeting_id
        )
        
        # Log debug info
        logger.info(f"[TaskExtractor] Debug info: {debug_info}")
        
        return extractions, processing_time
    
    def get_status(self):
        """Get model status"""
        return self.agent.get_model_status()


# Global instance
_extractor_instance: Optional[TaskExtractor] = None

def get_task_extractor() -> TaskExtractor:
    """Get or create global TaskExtractor instance"""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = TaskExtractor()
    return _extractor_instance
