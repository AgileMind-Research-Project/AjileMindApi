"""
LLM Report Service

Service for generating AI reports using LLaMA 3.2 via Ollama.
"""

from langchain_ollama import OllamaLLM
from app.core.config import settings
from app.core.logger import logger
from app.schemas.report import DailyStandupReport, SprintMeetingReport, RetrospectiveReport, BrainstormingMeetingReport
from typing import Dict, Any, Union
import json
import re


class LLMReportService:
    """Service for generating reports using LLM"""
    
    def __init__(self):
        """Initialize Ollama LLM"""
        try:
            ollama_base_url = f"{settings.OLLAMA_HOST}:{settings.OLLAMA_PORT}"
            self.llm = OllamaLLM(
                base_url=ollama_base_url,
                model=settings.OLLAMA_MODEL,
                temperature=0.3,  # Lower temperature for structured output
                num_predict=6000
            )
            self.available = True
            logger.info(f"LLM Report Service initialized with {settings.OLLAMA_MODEL}")
        except Exception as e:
            logger.error(f"Error initializing LLM Report Service: {e}")
            self.available = False
    
    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """Extract JSON from LLM response with robust parsing"""
        # Clean response - remove control characters except newlines and tabs
        cleaned = ''.join(char for char in response if char == '\n' or char == '\t' or (ord(char) >= 32 and ord(char) < 127) or ord(char) > 127)
        
        # Find the JSON object by tracking braces
        start_idx = cleaned.find('{')
        if start_idx == -1:
            raise ValueError("No JSON object found in response")
        
        brace_count = 0
        end_idx = start_idx
        in_string = False
        escape_next = False
        
        for i, char in enumerate(cleaned[start_idx:], start=start_idx):
            if escape_next:
                escape_next = False
                continue
            if char == '\\' and in_string:
                escape_next = True
                continue
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i
                    break
        
        if brace_count == 0 and end_idx > start_idx:
            json_str = cleaned[start_idx:end_idx + 1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse failed after extraction: {e}")
        
        # Fallback: try the old regex approach with the cleaned string
        try:
            json_match = re.search(r'\{[\s\S]*\}', cleaned)
            if json_match:
                return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
        
        # Last resort: try to repair truncated JSON
        logger.warning("Attempting to repair truncated JSON")
        json_str = cleaned[start_idx:] if start_idx >= 0 else cleaned
        
        # Count brackets and braces to fix truncation
        open_braces = json_str.count('{')
        close_braces = json_str.count('}')
        open_brackets = json_str.count('[')
        close_brackets = json_str.count(']')
        
        # Add missing closures
        json_str = json_str.rstrip()
        json_str += ']' * (open_brackets - close_brackets)
        json_str += '}' * (open_braces - close_braces)
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON even after repair: {e}")
            logger.error(f"Response was: {response}")
            raise ValueError("Failed to parse structured report from LLM response")
    
    def generate_daily_standup_report(
        self, 
        transcript: str,
        custom_prompt: str = None
    ) -> DailyStandupReport:
        """Generate Daily Standup Report from transcript"""
        
        if not self.available:
            raise RuntimeError("LLM service is not available")
        
        intro_instruction = custom_prompt if custom_prompt else "Analyze this daily standup transcript and extract structured information."
        
        prompt = f"""
You are an expert meeting analyzer. {intro_instruction}

Transcript:
{transcript}

Generate a JSON response with this exact structure:
{{
    "yesterday_work": ["task 1 by person name", "task 2 by person name", ...],
    "today_plan": ["task 1 by person name", "task 2 by person name", ...],
    "blockers": ["blocker 1 - person name", "blocker 2 - person name", ...]
}}

Rules:
- Extract only factual information from the transcript
- Include team member names with their tasks
- Use bullet points for each item
- If no blockers mentioned, use empty array
- Be concise and clear
- Return ONLY valid JSON, no additional text

JSON Response:
"""
        
        try:
            response = self.llm.invoke(prompt)
            logger.info(f"LLM Response: {response[:200]}...")
            
            report_data = self._extract_json_from_response(response)
            return DailyStandupReport(**report_data)
        
        except Exception as e:
            logger.error(f"Error generating daily standup report: {e}")
            raise
    
    def generate_sprint_meeting_report(
        self, 
        transcript: str,
        custom_prompt: str = None
    ) -> SprintMeetingReport:
        """Generate Sprint Meeting Summary from transcript"""
        
        if not self.available:
            raise RuntimeError("LLM service is not available")
        
        intro_instruction = custom_prompt if custom_prompt else "Analyze this sprint meeting transcript and create a comprehensive summary."
        
        prompt = f"""
You are an expert Agile coach. {intro_instruction}

Transcript:
{transcript}

Generate a JSON response with this exact structure:
{{
    "sprint_goals": ["goal 1", "goal 2", ...],
    "progress_summary": "Overall progress description in 2-3 sentences",
    "issues_risks": ["issue 1", "risk 1", ...],
    "action_items": [
        {{"task": "action description", "assignee": "person name", "due_date": "estimate", "priority": "high"}},
        ...
    ]
}}

Rules:
- Extract sprint goals discussed
- Summarize overall progress concisely
- Identify issues and risks
- List all action items with assignees
- Be specific and actionable
- Return ONLY valid JSON, no additional text

JSON Response:
"""
        
        try:
            response = self.llm.invoke(prompt)
            logger.info(f"LLM Response: {response[:200]}...")
            
            report_data = self._extract_json_from_response(response)
            return SprintMeetingReport(**report_data)
        
        except Exception as e:
            logger.error(f"Error generating sprint meeting report: {e}")
            raise
    
    def generate_retrospective_report(
        self, 
        transcript: str,
        custom_prompt: str = None
    ) -> RetrospectiveReport:
        """Generate Retrospective Meeting Summary from transcript"""
        
        if not self.available:
            raise RuntimeError("LLM service is not available")
        
        intro_instruction = custom_prompt if custom_prompt else "Analyze this retrospective transcript."
        
        prompt = f"""
You are an expert Agile retrospective facilitator. {intro_instruction}

Transcript:
{transcript}

Generate a JSON response with this exact structure:
{{
    "what_went_well": ["positive 1", "positive 2", ...],
    "what_didnt_go_well": ["issue 1", "issue 2", ...],
    "improvements": ["improvement 1", "improvement 2", ...],
    "action_points": [
        {{"task": "action description", "assignee": "person", "priority": "high"}},
        ...
    ]
}}

Rules:
- Separate positives, negatives, and improvements clearly
- Include team insights and discussions
- List actionable improvement points
- Assign owners to action points
- Prioritize actions (high/medium/low)
- Return ONLY valid JSON, no additional text

JSON Response:
"""
        
        try:
            response = self.llm.invoke(prompt)
            logger.info(f"LLM Response: {response[:200]}...")
            
            report_data = self._extract_json_from_response(response)
            return RetrospectiveReport(**report_data)
        
        except Exception as e:
            logger.error(f"Error generating retrospective report: {e}")
            raise
    
    def generate_brainstorming_report(
        self, 
        transcript: str,
        custom_prompt: str = None
    ) -> BrainstormingMeetingReport:
        """Generate Brainstorming Meeting Summary Report from transcript"""
        
        if not self.available:
            raise RuntimeError("LLM service is not available")
        
        intro_instruction = custom_prompt if custom_prompt else "Analyze this brainstorming session transcript and create a comprehensive summary."
        
        prompt = f"""
You are an expert meeting facilitator specializing in brainstorming sessions. {intro_instruction}

Transcript:
{transcript}

Generate a JSON response with this exact structure:
{{
    "meeting_topic": "The main topic or challenge being brainstormed",
    "meeting_objective": "The goal or objective of the brainstorming session",
    "participants": ["participant 1", "participant 2", ...],
    "ideas_generated": [
        {{"idea": "idea description", "proposed_by": "person name", "category": "category name", "votes": 0}},
        ...
    ],
    "top_ideas": ["most promising idea 1", "most promising idea 2", ...],
    "categories": ["category 1", "category 2", ...],
    "key_themes": ["recurring theme 1", "recurring theme 2", ...],
    "decisions_made": ["decision 1", "decision 2", ...],
    "next_steps": [
        {{"task": "action description", "assignee": "person name", "due_date": "estimate", "priority": "high"}},
        ...
    ],
    "summary": "Brief 2-3 sentence summary of the brainstorming session outcomes"
}}

Rules:
- Extract all ideas mentioned in the transcript
- Group ideas into logical categories
- Identify the most promising or voted-on ideas as top ideas
- Capture any decisions or conclusions reached
- List actionable next steps with assignees
- Include all participants mentioned
- Identify recurring themes across ideas
- Be specific and capture the creative output
- Return ONLY valid JSON, no additional text

JSON Response:
"""
        
        try:
            response = self.llm.invoke(prompt)
            logger.info(f"LLM Response: {response[:200]}...")
            
            report_data = self._extract_json_from_response(response)
            return BrainstormingMeetingReport(**report_data)
        
        except Exception as e:
            logger.error(f"Error generating brainstorming report: {e}")
            raise
    
    def generate_report(
        self, 
        transcript: str, 
        report_type: str,
        custom_prompt: str = None
    ) -> Union[DailyStandupReport, SprintMeetingReport, RetrospectiveReport, BrainstormingMeetingReport]:
        """Generate report based on type"""
        
        if report_type == "daily_standup":
            return self.generate_daily_standup_report(transcript, custom_prompt)
        elif report_type == "sprint_meeting":
            return self.generate_sprint_meeting_report(transcript, custom_prompt)
        elif report_type == "retrospective":
            return self.generate_retrospective_report(transcript, custom_prompt)
        elif report_type == "brainstorming":
            return self.generate_brainstorming_report(transcript, custom_prompt)
        else:
            raise ValueError(f"Unknown report type: {report_type}")


# Singleton instance
_llm_report_service = None

def get_llm_report_service() -> LLMReportService:
    """Get or create LLM report service instance"""
    global _llm_report_service
    if _llm_report_service is None:
        _llm_report_service = LLMReportService()
    return _llm_report_service
