"""
Model Loader for Mistral-7B GGUF
Handles lazy loading and caching of the LLM model
"""

import os
import re
import json
import time
from typing import Optional, Any, List, Dict
from pathlib import Path

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

from app.core.logger import logger


class MockLlamaModel:
    """
    Intelligent Mock Llama model for testing/development.
    Uses Chain of Thought reasoning to analyze transcripts.
    """
    
    # Status detection patterns (priority order matters!)
    STATUS_PATTERNS = {
        'DONE': [
            r'\b(finished|completed|complete|done|deployed|merged|resolved|optimized)\b',
            r'\bmarked\s+as\s+complete\b',
            r'^Complete:',  # Line starts with Complete:
            r'\bis\s+done\b', r'\bis\s+complete\b', r'\bare\s+complete\b',
            r'\bhotfix\s+is\s+deployed\b',
            r'\bpassed\b'
        ],
        'BLOCKED': [
            r'\b(blocked|blocker|can\'t\s+proceed|waiting\s+for|stuck|missing)\b',
            r'\b500\s+error\b', r'\bcritical\s+blocker\b',
            r'\bI\s+can\'t\b'
        ],
        'TODO': [
            r'\b(will\s+start|planning\s+to|going\s+to|need\s+to|pending\s+approval)\b',
            r'\bnext\s+sprint\b', r'\bparked\b',
            r'\bpending\s+your\s+approval\b',
            r'\blogged\s+as\b'  # Bug logged = TODO
        ],
        'IN_PROGRESS': [
            r'\b(working\s+on|currently|investigating|looking\s+into|preparing|aggregating)\b',
            r'\btoday\s+I\s+(am|will)\b', r'\bI\'m\s+working\b',
            r'\bwriting\b', r'\bimplementing\b'
        ]
    }
    
    # Blocker extraction patterns
    BLOCKER_PATTERNS = [
        r'(?:blocker|blocked)[:\s]+(.+?)(?:\.|$)',
        r'can\'t\s+proceed\s+(?:without|until)\s+(.+?)(?:\.|$)',
        r'waiting\s+for\s+(.+?)(?:\.|$)',
        r'missing\s+(.+?)(?:\.|$)',
        r'(\d+\s+error.+?)(?:\.|$)',
    ]
    
    def __call__(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Process prompt and extract task updates using CoT reasoning.
        """
        logger.info("[MockLLM] Starting Chain of Thought analysis...")
        
        # Simulate processing delay
        time.sleep(0.5)
        
        # Extract transcript from prompt
        transcript = self._extract_transcript(prompt)
        
        if not transcript:
            logger.warning("[MockLLM] No transcript found in prompt")
            return self._empty_response()
        
        # Step 1: Find all ticket IDs
        logger.info("[MockLLM] Step 1: Extracting ticket IDs...")
        tickets = self._find_tickets(transcript)
        logger.info(f"[MockLLM] Found {len(tickets)} unique tickets")
        
        # Step 2: Analyze each ticket with CoT
        logger.info("[MockLLM] Step 2: Applying Chain of Thought reasoning...")
        extractions = []
        
        for ticket_id in tickets:
            analysis = self._analyze_ticket(ticket_id, transcript)
            if analysis:
                extractions.append(analysis)
                logger.info(f"[MockLLM] → {ticket_id}: {analysis['status']} (confidence: {analysis['confidence']:.2f})")
        
        logger.info(f"[MockLLM] ✓ Extraction complete: {len(extractions)} task updates")
        
        # Return in LLM response format
        return {
            "choices": [
                {
                    "text": json.dumps(extractions, indent=2)
                }
            ]
        }
    
    def _extract_transcript(self, prompt: str) -> str:
        """Extract transcript text from the prompt."""
        # Look for transcript between triple quotes
        match = re.search(r'\"\"\"(.+?)\"\"\"', prompt, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Fallback: look for "Transcript:" section
        match = re.search(r'Transcript:\s*(.+?)(?:Instructions:|$)', prompt, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        return prompt
    
    def _find_tickets(self, text: str) -> List[str]:
        """Find all unique ticket IDs in transcript."""
        # Pattern: WORD-WORD-NUMBER or WORD-NUMBER
        pattern = r'\b([A-Z]+-(?:[A-Z]+-)?[0-9]+)\b'
        tickets = re.findall(pattern, text, re.IGNORECASE)
        
        # Normalize and deduplicate
        seen = set()
        unique = []
        for t in tickets:
            t_upper = t.upper()
            if t_upper not in seen:
                seen.add(t_upper)
                unique.append(t_upper)
        
        return unique
    
    def _analyze_ticket(self, ticket_id: str, transcript: str) -> Optional[Dict[str, Any]]:
        """
        Analyze a single ticket using Chain of Thought reasoning.
        Returns structured extraction or None if insufficient context.
        """
        # Find context around ticket (sentences mentioning it)
        context = self._get_ticket_context(ticket_id, transcript)
        
        if not context:
            return None
        
        # Chain of Thought Step 1: Detect status
        status, status_reasoning = self._detect_status(context)
        
        # Chain of Thought Step 2: Detect blocker (if BLOCKED)
        blocker = None
        if status == 'BLOCKED':
            blocker = self._extract_blocker(context)
        
        # Chain of Thought Step 3: Calculate confidence
        confidence = self._calculate_confidence(context, status)
        
        # Build reasoning explanation
        reasoning = self._build_reasoning(status, status_reasoning, blocker)
        
        return {
            "ticket_id": ticket_id,
            "status": status,
            "blocker": blocker,
            "confidence": confidence,
            "context": context[:200],  # Limit context length
            "reasoning": reasoning
        }
    
    def _get_ticket_context(self, ticket_id: str, transcript: str) -> str:
        """Extract sentences mentioning the ticket."""
        # Split into sentences
        sentences = re.split(r'[.!?\n]+', transcript)
        
        relevant = []
        for sentence in sentences:
            if ticket_id.lower() in sentence.lower():
                relevant.append(sentence.strip())
        
        return ' '.join(relevant)
    
    def _detect_status(self, context: str) -> tuple:
        """Detect status from context using pattern matching."""
        context_lower = context.lower()
        
        # Check patterns in priority order
        for status, patterns in self.STATUS_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, context_lower)
                if match:
                    return status, f"Matched pattern: '{match.group(0)}'"
        
        # Default to IN_PROGRESS if mentioned but no clear status
        return 'IN_PROGRESS', 'No explicit status, defaulting to IN_PROGRESS'
    
    def _extract_blocker(self, context: str) -> Optional[str]:
        """Extract blocker description from context."""
        context_lower = context.lower()
        
        for pattern in self.BLOCKER_PATTERNS:
            match = re.search(pattern, context_lower, re.IGNORECASE)
            if match:
                blocker = match.group(1).strip()
                # Capitalize first letter
                return blocker[0].upper() + blocker[1:] if blocker else None
        
        # Fallback: extract phrase after "blocker"
        if 'blocker' in context_lower:
            idx = context_lower.index('blocker')
            return context[idx:idx+100].split('.')[0]
        
        return "Blocker detected but details unclear"
    
    def _calculate_confidence(self, context: str, status: str) -> float:
        """Calculate confidence score based on context clarity."""
        base_confidence = 0.75
        
        # Boost for explicit keywords
        explicit_keywords = ['finished', 'completed', 'done', 'blocker', 'blocked', 'started']
        for kw in explicit_keywords:
            if kw in context.lower():
                base_confidence += 0.08
        
        # Boost for temporal markers
        temporal = ['yesterday', 'today', 'completed', 'merged', 'deployed']
        for t in temporal:
            if t in context.lower():
                base_confidence += 0.05
        
        # Cap at 0.98
        return min(0.98, base_confidence)
    
    def _build_reasoning(self, status: str, status_reasoning: str, blocker: Optional[str]) -> str:
        """Build human-readable reasoning explanation."""
        parts = [f"Status detected as {status}. {status_reasoning}"]
        
        if blocker:
            parts.append(f"Blocker identified: {blocker}")
        
        return ' '.join(parts)
    
    def _empty_response(self) -> Dict[str, Any]:
        """Return empty response format."""
        return {
            "choices": [
                {
                    "text": "[]"
                }
            ]
        }


class ModelLoader:
    """Singleton model loader for Mistral-7B"""
    
    _instance: Optional['ModelLoader'] = None
    _model: Optional[Any] = None  # Can be Llama or MockLlamaModel
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
