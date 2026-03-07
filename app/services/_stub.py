"""
AI Service for Transcript Analysis
Primary: Deterministic regex parser | Fallback: Ollama (llama3.2:1b) | OpenAI
"""

import re
import json
import logging
import aiohttp
import asyncio
from typing import Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

OLLAMA_OPTIONS = {
    "temperature": 0.1, "num_ctx": 2048, "num_predict": 2048,
    "top_k": 10, "top_p": 0.9, "repeat_penalty": 1.1,
    "seed": 42, "num_thread": 4,
}
OLLAMA_CONNECT_TIMEOUT = 10
OLLAMA_READ_TIMEOUT    = 90
OPENAI_TOTAL_TIMEOUT   = 120

