"""
LLM Report Service

Service for generating AI reports using LLaMA 3.2 via Ollama.
"""

from langchain_ollama import OllamaLLM
from app.core.config import settings
from app.core.logger import logger
from app.schemas.report import DailyStandupReport, SprintMeetingReport, RetrospectiveReport, BrainstormingMeetingReport
from typing import Dict, Any, Union, List
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
    
    def _extract_speakers_from_transcript(self, transcript: str) -> List[str]:
        """Extract unique speaker/person names from transcript content"""
        import re
        # Match patterns like "Speaker Name:" at start of lines or after timestamps like "[10:00:00]"
        speakers = re.findall(r'(?:^|\])\s*([^:\[\]\n]{2,30}):', transcript, re.MULTILINE)
        # Clean and deduplicate
        unique = []
        seen = set()
        for s in speakers:
            name = s.strip()
            if name and name.lower() not in seen and len(name) > 1:
                seen.add(name.lower())
                unique.append(name)
        return unique

    def generate_daily_standup_report(
        self, 
        transcript: str,
        custom_prompt: str = None
    ) -> DailyStandupReport:
        """Generate Daily Standup Report from transcript – developer-centric format"""
        
        if not self.available:
            raise RuntimeError("LLM service is not available")
        
        intro_instruction = custom_prompt if custom_prompt else "Analyze this daily standup transcript and extract structured information."
        
        # Pre-extract speaker names from transcript to help LLM
        speakers = self._extract_speakers_from_transcript(transcript)
        speakers_hint = ""
        if speakers:
            speakers_list = ", ".join(f'"{s}"' for s in speakers)
            speakers_hint = f"\nThe following people/speakers are identified in the transcript: {speakers_list}\nYou MUST use these exact names in your response.\n"
        
        prompt = f"""
You are an expert meeting analyzer. {intro_instruction}

Transcript:
{transcript}
{speakers_hint}
Your task: For each developer/person in this transcript, extract:
1. Their role or title (e.g., Backend Developer, Frontend Developer, QA Engineer) if mentioned
2. What they did yesterday (yesterday's tasks)
3. What they plan to do today (today's tasks)
4. Any blockers, errors, or issues they are facing

Also extract a summary of shared blockers that affect multiple people or the whole team.

Generate a JSON response with this EXACT structure:
{{
    "team_updates": [
        {{
            "name": "Person Name",
            "role": "Their role or title if mentioned, otherwise null",
            "yesterday_tasks": ["what they did yesterday task 1", "task 2"],
            "today_tasks": ["what they plan to do today task 1", "task 2"],
            "blockers": ["any blocker or error they mentioned"]
        }},
        {{
            "name": "Another Person",
            "role": "Their role if mentioned",
            "yesterday_tasks": ["task 1"],
            "today_tasks": ["task 1"],
            "blockers": []
        }}
    ],
    "blockers_summary": [
        {{
            "title": "Short title of the blocker",
            "description": "Detailed description of the blocker or error",
            "reported_by": ["Person1", "Person2"],
            "impact": "How this blocker affects the project"
        }}
    ]
}}

CRITICAL RULES:
1. Each person MUST be a separate object in "team_updates" with ALL their info together
2. Use the REAL speaker/person names from the transcript - never use generic names
3. "yesterday_tasks" = what they completed or worked on yesterday
4. "today_tasks" = what they plan to work on today
5. "blockers" = any issues, errors, bugs, or blockers they mentioned
6. "role" should be extracted if mentioned (e.g., "Backend Developer", "QA"), otherwise set to null
7. "blockers_summary" should list shared/critical blockers that affect the team; if none, use empty array
8. If a blocker or error is mentioned by multiple people, list all their names in "reported_by"
9. Return ONLY valid JSON, nothing else

JSON Response:
"""
        
        try:
            response = self.llm.invoke(prompt)
            logger.info(f"LLM Daily Standup Response: {response[:500]}...")
            
            report_data = self._extract_json_from_response(response)
            
            # Normalize team_updates
            team_updates = report_data.get('team_updates', [])
            if isinstance(team_updates, list):
                for entry in team_updates:
                    if isinstance(entry, dict):
                        for field in ['yesterday_tasks', 'today_tasks', 'blockers']:
                            if field not in entry:
                                entry[field] = []
                            elif isinstance(entry[field], str):
                                entry[field] = [entry[field]]
                        if 'role' not in entry:
                            entry['role'] = None
            
            # If LLM returned old-style format, convert it
            if not team_updates and ('yesterday_work' in report_data or 'today_plan' in report_data):
                team_updates = self._convert_legacy_to_developer_centric(report_data, speakers)
                report_data['team_updates'] = team_updates
            
            # Normalize blockers_summary
            blockers_summary = report_data.get('blockers_summary', [])
            if isinstance(blockers_summary, list):
                for item in blockers_summary:
                    if isinstance(item, dict):
                        if 'reported_by' not in item:
                            item['reported_by'] = []
                        elif isinstance(item['reported_by'], str):
                            item['reported_by'] = [item['reported_by']]
            
            return DailyStandupReport(**report_data)
        
        except Exception as e:
            logger.error(f"Error generating daily standup report: {e}")
            raise
    
    def _convert_legacy_to_developer_centric(self, report_data: Dict[str, Any], speakers: List[str]) -> List[Dict[str, Any]]:
        """Convert old-format (yesterday_work/today_plan/blockers) to developer-centric team_updates"""
        # Build a map of person -> updates
        person_map: Dict[str, Dict[str, Any]] = {}
        
        for field, target_key in [('yesterday_work', 'yesterday_tasks'), ('today_plan', 'today_tasks'), ('blockers', 'blockers')]:
            items = report_data.get(field, [])
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and 'name' in item:
                        name = item['name']
                        if name not in person_map:
                            person_map[name] = {'name': name, 'role': None, 'yesterday_tasks': [], 'today_tasks': [], 'blockers': []}
                        person_map[name][target_key] = item.get('tasks', [])
        
        return list(person_map.values()) if person_map else []

    def _attribute_tasks_to_speakers(self, flat_items: List[str], speakers: List[str]) -> List[Dict[str, Any]]:
        """When LLM returns flat strings, try to attribute them to known speakers"""
        # Try to match tasks to speakers by checking if the task mentions a speaker name
        speaker_tasks: Dict[str, List[str]] = {s: [] for s in speakers}
        unmatched = []
        
        for item in flat_items:
            matched = False
            for speaker in speakers:
                if speaker.lower() in item.lower():
                    # Remove the speaker name prefix if present
                    task = item
                    speaker_tasks[speaker].append(task)
                    matched = True
                    break
            if not matched:
                unmatched.append(item)
        
        # Add unmatched tasks to first speaker or "Team"
        if unmatched:
            if speakers:
                speaker_tasks[speakers[0]].extend(unmatched)
            else:
                speaker_tasks['Team'] = unmatched
        
        # Build result, only include speakers who have tasks
        result = []
        for name, tasks in speaker_tasks.items():
            if tasks:
                result.append({'name': name, 'tasks': tasks})
        
        return result if result else [{'name': 'Team', 'tasks': flat_items}]
    
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
    "decisions_made": [
        {{"decision": "decision description", "assignee": "person name or null"}},
        ...
    ],
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
            
            # Normalize decisions_made: LLM may return plain strings instead of Decision objects
            if 'decisions_made' in report_data and report_data['decisions_made']:
                report_data['decisions_made'] = [
                    d if isinstance(d, dict) else {'decision': str(d)}
                    for d in report_data['decisions_made']
                ]
            
            # Normalize next_steps: LLM may return plain strings instead of ActionItem objects
            if 'next_steps' in report_data and report_data['next_steps']:
                report_data['next_steps'] = [
                    s if isinstance(s, dict) else {'task': str(s)}
                    for s in report_data['next_steps']
                ]
            
            # Normalize ideas_generated: LLM may return plain strings
            if 'ideas_generated' in report_data and report_data['ideas_generated']:
                report_data['ideas_generated'] = [
                    i if isinstance(i, dict) else {'idea': str(i)}
                    for i in report_data['ideas_generated']
                ]
            
            return BrainstormingMeetingReport(**report_data)
        
        except Exception as e:
            logger.error(f"Error generating brainstorming report: {e}")
            raise
    
    def generate_report_from_template(
        self,
        transcript: str,
        template_sections: List[Dict[str, Any]],
        report_type: str,
        custom_prompt: str = None
    ) -> Dict[str, Any]:
        """Generate report using template sections to build a dynamic prompt.
        
        The template sections define which fields the LLM should populate.
        Each section has: title, type (paragraph/bullet_list/numbered_list/table/heading), order.
        """
        if not self.available:
            raise RuntimeError("LLM service is not available")
        
        # Sort sections by order
        sorted_sections = sorted(template_sections, key=lambda s: s.get('order', 0))
        
        # Build the JSON structure description from template sections
        json_fields = {}
        field_descriptions = []
        
        # Map section type to JSON value hints
        type_hints = {
            'paragraph': '"A concise paragraph of text"',
            'heading': '"A brief title or heading"',
            'bullet_list': '["item 1", "item 2", ...]',
            'numbered_list': '["step 1", "step 2", ...]',
            'table': '[{{"item": "description", "assignee": "person", "priority": "high"}}, ...]',
        }
        
        for section in sorted_sections:
            title = section.get('title', 'Untitled')
            sec_type = section.get('type', 'paragraph')
            # Create a snake_case key from the title
            key = title.lower().replace(' ', '_').replace("'", '').replace('-', '_')
            key = re.sub(r'[^a-z0-9_]', '', key)
            json_fields[key] = type_hints.get(sec_type, '"text content"')
            field_descriptions.append(f'- "{key}": {title} (format: {sec_type})')
        
        # Build the JSON example
        json_example_parts = []
        for key, hint in json_fields.items():
            json_example_parts.append(f'    "{key}": {hint}')
        json_example = '{{\n' + ',\n'.join(json_example_parts) + '\n}}'
        
        intro = custom_prompt if custom_prompt else f"Analyze this {report_type.replace('_', ' ')} transcript and generate a structured report."
        
        prompt = f"""You are an expert meeting analyzer and report generator. {intro}

Transcript:
{transcript}

Generate a JSON response with this exact structure based on the template sections:
{json_example}

Section descriptions:
{chr(10).join(field_descriptions)}

Rules:
- Fill each section with relevant content extracted from the transcript
- For bullet_list sections: return an array of strings
- For numbered_list sections: return an array of strings in order
- For paragraph sections: return a single string with 2-3 sentences
- For heading sections: return a brief title string
- For table sections: return an array of objects with relevant fields
- Extract only factual information from the transcript
- Be specific and actionable
- Return ONLY valid JSON, no additional text

JSON Response:
"""
        
        try:
            response = self.llm.invoke(prompt)
            logger.info(f"LLM Template Response: {response[:200]}...")
            
            report_data = self._extract_json_from_response(response)
            
            # Normalize: ensure list fields that got strings are wrapped
            for section in sorted_sections:
                title = section.get('title', '')
                sec_type = section.get('type', 'paragraph')
                key = title.lower().replace(' ', '_').replace("'", '').replace('-', '_')
                key = re.sub(r'[^a-z0-9_]', '', key)
                
                if key in report_data:
                    val = report_data[key]
                    if sec_type in ('bullet_list', 'numbered_list', 'table'):
                        if isinstance(val, str):
                            report_data[key] = [val]
                    elif sec_type in ('paragraph', 'heading'):
                        if isinstance(val, list):
                            report_data[key] = '. '.join(str(v) for v in val)
            
            # Embed section ordering metadata so the frontend can render in correct order
            report_data['_sections_order'] = [
                {
                    'key': re.sub(r'[^a-z0-9_]', '', s.get('title', '').lower().replace(' ', '_').replace("'", '').replace('-', '_')),
                    'title': s.get('title', 'Untitled'),
                    'type': s.get('type', 'paragraph'),
                    'order': s.get('order', 0)
                }
                for s in sorted_sections
            ]
            
            return report_data
            
        except Exception as e:
            logger.error(f"Error generating template-based report: {e}")
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
