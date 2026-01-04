"""
Agent Configuration
Configuration settings for the Mistral 7B model and agent behavior
"""
import os
from pathlib import Path

# Base directory for the agent module
AGENT_DIR = Path(__file__).parent

# Model Configuration
MODEL_PATH = AGENT_DIR / "modal" / "mistral-7b-instruct-v0.2.Q4_K_S.gguf"
MODEL_NAME = "mistral-7b-instruct-v0.2"

# LLM Parameters
LLM_CONFIG = {
    "model_path": str(MODEL_PATH),
    "n_ctx": 4096,  # Context window size
    "n_threads": 8,  # Number of CPU threads to use
    "n_gpu_layers": 0,  # Set to > 0 if you have GPU support
    "temperature": 0.7,  # Sampling temperature (0.0 to 1.0)
    "max_tokens": 2048,  # Maximum tokens to generate
    "top_p": 0.95,  # Nucleus sampling parameter
    "top_k": 40,  # Top-k sampling parameter
    "repeat_penalty": 1.1,  # Penalty for repetition
    "verbose": False,  # Set to True for debug output
}

# Prompt Templates
SYSTEM_PROMPT = """You are a helpful AI assistant specialized in agile project management. 
You help users with sprint planning, task management, retrospectives, and team collaboration."""

INSTRUCTION_TEMPLATE = """<s>[INST] {system_prompt}

{user_input} [/INST]"""

CONVERSATION_TEMPLATE = """<s>[INST] {system_prompt}

{conversation_history}

User: {user_input} [/INST]"""

# Agent Behavior Settings
AGENT_CONFIG = {
    "max_conversation_history": 10,  # Maximum number of messages to keep in history
    "enable_streaming": False,  # Enable streaming responses
    "timeout": 300,  # Timeout in seconds for model inference
}

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = AGENT_DIR / "agent.log"
