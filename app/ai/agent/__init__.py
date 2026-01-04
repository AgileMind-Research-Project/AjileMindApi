"""
AI Agent Module
Provides AI agent capabilities using Mistral 7B model
"""
from .agent_service import AgentService, create_agent
from .model_loader import ModelLoader, get_model
from .config import (
    MODEL_PATH,
    MODEL_NAME,
    LLM_CONFIG,
    AGENT_CONFIG,
    SYSTEM_PROMPT
)

__all__ = [
    'AgentService',
    'create_agent',
    'ModelLoader',
    'get_model',
    'MODEL_PATH',
    'MODEL_NAME',
    'LLM_CONFIG',
    'AGENT_CONFIG',
    'SYSTEM_PROMPT',
]
