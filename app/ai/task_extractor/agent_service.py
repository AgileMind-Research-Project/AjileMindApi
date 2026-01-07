"""
AI Agent Service for Task Extraction
Orchestrates the extraction process with detailed logging
"""

import time
from typing import List, Tuple, Dict, Any
from app.ai.task_extractor.model_loader import model_loader
from app.ai.task_extractor.prompt_templates import build_extraction_prompt
from app.task_updates_config.models import TaskUpdateExtract, DetectedStatus
from app.core.logger import logger


class AgentService:
    """AI Agent for extracting task updates from transcripts"""
    
    def __init__(self):
        """Initialize agent service"""
        self.model_loader = model_loader
        logger.info("AgentService initialized")
    
    def extract_task_updates(
        self, 
        transcript: str, 
        meeting_id: str
    ) -> Tuple[List[TaskUpdateExtract], float, Dict[str, Any]]:
        """
        Extract task updates from transcript with detailed logging
        
        Args:
            transcript: Meeting transcript text
            meeting_id: Meeting ID for logging
            
        Returns:
            Tuple of (extractions, processing_time_ms, debug_info)
        """
        start_time = time.time()
        debug_info = {
            "meeting_id": meeting_id,
            "transcript_length": len(transcript),
            "steps": []
        }
        
        try:
            # Step 1: Load model
            logger.info(f"[{meeting_id}] Step 1: Loading Mistral-7B model...")
            debug_info["steps"].append({"step": 1, "action": "Loading model", "status": "started"})
            
            model = self.model_loader.load_model()
            if model is None:
                logger.error(f"[{meeting_id}] Failed to load model")
                debug_info["steps"].append({"step": 1, "action": "Loading model", "status": "failed"})
                return [], 0.0, debug_info
            
            debug_info["steps"].append({"step": 1, "action": "Loading model", "status": "completed"})
            logger.info(f"[{meeting_id}] ✓ Model loaded")
            
            # Step 2: Build prompt
            logger.info(f"[{meeting_id}] Step 2: Building extraction prompt with few-shot examples...")
            debug_info["steps"].append({"step": 2, "action": "Building prompt", "status": "started"})
            
            prompt = build_extraction_prompt(transcript)
            debug_info["prompt_length"] = len(prompt)
            debug_info["steps"].append({"step": 2, "action": "Building prompt", "status": "completed"})
            
            logger.info(f"[{meeting_id}] ✓ Prompt built ({len(prompt)} chars)")
            
            # Step 3: AI Thinking (Generate response)
            logger.info(f"[{meeting_id}] Step 3: AI Thinking - Analyzing transcript...")
            debug_info["steps"].append({"step": 3, "action": "AI Thinking", "status": "started"})
            
            thinking_start = time.time()
            response = model(
                prompt,
                max_tokens=2048,
                temperature=0.2,
                top_p=0.95,
                stop=["```\n\n", "\n\nInput:", "\n\nEXAMPLE"],
                echo=False
            )
            thinking_time = (time.time() - thinking_start) * 1000
            
            debug_info["thinking_time_ms"] = thinking_time
            debug_info["steps"].append({"step": 3, "action": "AI Thinking", "status": "completed", "time_ms": thinking_time})
            
            logger.info(f"[{meeting_id}] ✓ AI thinking completed ({thinking_time:.2f}ms)")
            
            # Step 4: Extract text from response
            if not response or 'choices' not in response or len(response['choices']) == 0:
                logger.error(f"[{meeting_id}] Invalid response from model")
                debug_info["steps"].append({"step": 4, "action": "Extracting response", "status": "failed"})
                return [], 0.0, debug_info
            
            response_text = response['choices'][0]['text'].strip()
            debug_info["response_length"] = len(response_text)
            debug_info["raw_response"] = response_text[:500]  # First 500 chars for debugging
            
            logger.info(f"[{meeting_id}] Step 4: Extracting JSON from response...")
            debug_info["steps"].append({"step": 4, "action": "Extracting JSON", "status": "started"})
            
            # Step 5: Parse JSON
            import re
            import json
            
            json_match = re.search(r'\[[\s\S]*\]', response_text)
            if not json_match:
                logger.warning(f"[{meeting_id}] No JSON array found in response")
                debug_info["steps"].append({"step": 4, "action": "Extracting JSON", "status": "no_json_found"})
                return [], 0.0, debug_info
            
            json_str = json_match.group(0)
            json_data = json.loads(json_str)
            
            debug_info["steps"].append({"step": 4, "action": "Extracting JSON", "status": "completed"})
            logger.info(f"[{meeting_id}] ✓ JSON extracted ({len(json_data)} items)")
            
            # Step 6: Convert to Pydantic models
            logger.info(f"[{meeting_id}] Step 5: Converting to task update models...")
            debug_info["steps"].append({"step": 5, "action": "Converting to models", "status": "started"})
            
            extractions = self._parse_extractions(json_data, meeting_id)
            
            debug_info["steps"].append({"step": 5, "action": "Converting to models", "status": "completed"})
            debug_info["total_extracted"] = len(extractions)
            
            processing_time = (time.time() - start_time) * 1000
            debug_info["total_processing_time_ms"] = processing_time
            
            logger.info(f"[{meeting_id}] ✓ Extraction complete: {len(extractions)} updates in {processing_time:.2f}ms")
            
            return extractions, processing_time, debug_info
        
        except Exception as e:
            logger.error(f"[{meeting_id}] Extraction error: {e}", exc_info=True)
            debug_info["error"] = str(e)
            debug_info["steps"].append({"step": "error", "action": "Exception occurred", "status": "failed"})
            return [], 0.0, debug_info
    
    def _parse_extractions(
        self, 
        json_data: List[Dict[str, Any]], 
        meeting_id: str
    ) -> List[TaskUpdateExtract]:
        """
        Parse JSON data into TaskUpdateExtract models
        
        Args:
            json_data: List of dicts from LLM
            meeting_id: Meeting ID for logging
            
        Returns:
            List of TaskUpdateExtract objects
        """
        extractions = []
        
        for idx, item in enumerate(json_data):
            try:
                # Map status string to enum
                status_str = item.get('status', '').upper().replace(' ', '_')
                
                try:
                    status = DetectedStatus(status_str)
                except ValueError:
                    logger.warning(f"[{meeting_id}] Invalid status '{status_str}' for item {idx}, defaulting to IN_PROGRESS")
                    status = DetectedStatus.IN_PROGRESS
                
                extraction = TaskUpdateExtract(
                    ticket_id=item.get('ticket_id', 'UNKNOWN'),
                    detected_status=status,
                    blocker_description=item.get('blocker'),
                    ai_confidence_score=float(item.get('confidence', 0.5)),
                    ai_reasoning=item.get('reasoning', 'No reasoning provided'),
                    extracted_context=item.get('context', '')
                )
                extractions.append(extraction)
                
                logger.debug(f"[{meeting_id}] Parsed: {extraction.ticket_id} -> {extraction.detected_status.value}")
            
            except Exception as e:
                logger.error(f"[{meeting_id}] Error parsing item {idx}: {e}")
                continue
        
        return extractions
    
    def get_model_status(self) -> Dict[str, Any]:
        """Get current model status"""
        return self.model_loader.get_model_info()


# Global instance
agent_service = AgentService()
