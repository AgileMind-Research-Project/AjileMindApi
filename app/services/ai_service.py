"""
AI Service

Integrates with Ollama to parse meeting transcripts and extract structured data.
"""

import json
import logging
import ollama
from typing import Dict, Any, List, Optional
from app.core.logger import logger

class AIService:
    """Service for AI-powered operations using Ollama"""
    
    def __init__(self, model: str = "llama3"):
        self.model = model
        
    async def parse_meeting_transcript(self, transcript_text: str) -> Dict[str, Any]:
        """
        Parse meeting transcript to extract tasks and leaves.
        
        Args:
            transcript_text: Full text of the meeting transcript
            
        Returns:
            Dictionary containing extracted tasks and leaves
        """
        
        prompt = f"""
        You are an AI Project Assistant. Analyze the following meeting transcript and extract structured data.
        
        Transcript:
        {transcript_text}
        
        Extract the following:
        1. **Tasks**: New tasks or backlog items mentioned.
           - Summary: Brief title
           - Description: Details (if any)
           - Assignee: Name of person assigned (if mapped)
           - Estimate: Time estimate (e.g., "2 days", "4 hours")
           - Type: "Story", "Task", "Bug" (default to "Task")
           - Priority: "High", "Medium", "Low" (default to "Medium")
           
        2. **Leaves**: Developer leave plans.
           - Developer: Name
           - Date: Date of leave (YYYY-MM-DD format if possible, otherwise descriptive)
           - Type: "Full Day", "Half Day", "Short Leave"
           - Hours: Estimate hours (8 for Full, 4 for Half, 2 for Short)
           
        3. **Sprint (Optional)**: If a new sprint is being planned.
           - Name: Suggested sprint name (e.g., "Sprint 10", "MVP Sprint")
           - Goal: Sprint goal if mentioned
           - Start Date: Start date (YYYY-MM-DD)
           - End Date: End date (YYYY-MM-DD)

        Output strictly valid JSON in the following format:
        {{
            "tasks": [
                {{ "summary": "...", "description": "...", "assignee": "...", "estimate": "...", "type": "...", "priority": "..." }}
            ],
            "leaves": [
                {{ "developer_name": "...", "leave_date": "YYYY-MM-DD", "type": "...", "hours": 8 }}
            ],
            "sprint_info": {{
                "name": "...", 
                "goal": "...", 
                "start_date": "...", 
                "end_date": "..."
            }}
        }}
        
        If date is relative (e.g. "tomorrow"), try to estimate or leave as string.
        If no sprint is mentioned, "sprint_info" can be null.
        Do not add any text outside the JSON.
        """
        
        # Check connection before attempting chat
        # Check connection before attempting chat
        if not self.check_ollama_status():
            logger.warning("Ollama not reachable. Using Regex Fallback for parsing.")
            return self.parse_with_regex(transcript_text)

        try:
            response = ollama.chat(model=self.model, messages=[
                {
                    'role': 'user',
                    'content': prompt,
                },
            ])
            
            content = response['message']['content']
            
            # Simple cleanup to ensure JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
                
            data = json.loads(content.strip())
            return data
            
        except Exception as e:
            logger.error(f"Ollama parsing failed: {e}")
            # Return empty structure on failure
            return {"tasks": [], "leaves": []}

    def parse_with_regex(self, text: str) -> Dict[str, Any]:
        """
        Fallback method to parse transcript using Regex when AI is offline.
        """
        import re
        from datetime import datetime, timedelta

        tasks = []
        leaves = []
        sprint_info = None

        # 1. Extract Tasks
        # Pattern: "handle the task "Summary" with task ID TAM-XX, estimated at XX hours"
        # Adjusted to capture variations
        task_pattern = re.compile(
            r'handle (?:the )?(?:sub)?task "([^"]+)"(?: with task ID ([A-Z]+-\d+))?(?:.*?)estimated at (\d+) hours', 
            re.IGNORECASE
        )
        
        # Also capture: "oversee/manage the task..."
        manager_pattern = re.compile(
            r'(?:oversee|manage|supervise) (?:the )?(?:parent )?task "([^"]+)"(?:.*?)estimated at (\d+) hours',
            re.IGNORECASE
        )

        lines = text.split('\n')
        current_speaker = None
        
        for line in lines:
            if line.strip().startswith('[') and ']' in line:
                # Extract speaker e.g. [10:00] email (ROLE)
                parts = line.split(']')
                if len(parts) > 1:
                    raw_speaker = parts[1].strip()
                    # Extract email/name: "email (ROLE)" -> "email"
                    current_speaker = raw_speaker.split('(')[0].strip()
            
            if not current_speaker:
                continue

            # Check for leaves
            # "I will be on leave from Sprint Start to Sprint End" or specific dates?
            # Pattern: "I will be on leave from <Date> to <Date>"
            leave_match = re.search(r'on leave from ([A-Za-z]+ \d+,? \d{4}) to ([A-Za-z]+ \d+,? \d{4})', line, re.IGNORECASE)
            if leave_match:
                start_str = leave_match.group(1)
                # Simple parsing logic or just return string
                leaves.append({
                    "developer_name": current_speaker,
                    "leave_date": f"{start_str} (Range)",
                    "type": "Full Day",
                    "hours": 8
                })

            # Check for tasks
            for match in task_pattern.finditer(line):
                summary = match.group(1)
                est = match.group(3)
                tasks.append({
                    "summary": summary,
                    "description": f"Extracted from transcript. ID: {match.group(2) or 'N/A'}",
                    "assignee": current_speaker,
                    "estimate": f"{est}h",
                    "type": "Task",
                    "priority": "Medium"
                })

            for match in manager_pattern.finditer(line):
                summary = match.group(1)
                est = match.group(2)
                tasks.append({
                    "summary": summary,
                    "description": "Management task",
                    "assignee": current_speaker,
                    "estimate": f"{est}h",
                    "type": "Task",
                    "priority": "Medium"
                })

        # 3. Extract Sprint Info (Basic)
        # Look for "goal for this sprint is to <Goal>"
        goal_match = re.search(r"goal for this sprint is to ([^\.]+)", text, re.IGNORECASE)
        sprint_goal = goal_match.group(1).strip() if goal_match else "Sprint Goal"
        
        # Look for dates if possible or default
        # Assuming current date is start for fallback
        now = datetime.now()
        sprint_info = {
            "name": f"Sprint {now.strftime('%V')}",
            "goal": sprint_goal,
            "start_date": now.strftime("%Y-%m-%d"),
            "end_date": (now + timedelta(days=14)).strftime("%Y-%m-%d")
        }

        return {
            "tasks": tasks,
            "leaves": leaves,
            "sprint_info": sprint_info
        }

    def check_ollama_status(self) -> bool:
        """Check if Ollama is reachable"""
        try:
            ollama.list()
            return True
        except Exception:
            return False
