"""
AI-Powered Release Note Generation Service
Uses Mistral-7B LLM to generate structured release notes from project backlog data
"""

import json
import logging
from typing import Dict, Any, List, Optional
from app.db.database import Database
from app.ai.task_extractor.llm_client import MistralClient
from app.core.logger import logger

class AIReleaseNoteService:
    """Service for generating AI-powered release notes from backlog data"""
    
    def __init__(self, db: Database):
        self.db = db
        self.mistral_client = MistralClient()
        logger.info("AIReleaseNoteService initialized")
    
    async def generate_release_note_content(
        self,
        tenant_name: str,
        project_id: int,
        start_sprint: Optional[int] = None,
        end_sprint: Optional[int] = None,
        version: str = "1.0.0"
    ) -> Dict[str, Any]:
        """
        Generate AI-powered release note content based on project backlog data
        
        Args:
            tenant_name: Database tenant name
            project_id: Target project ID
            start_sprint: Starting sprint number (optional)
            end_sprint: Ending sprint number (optional)
            version: Version number for context
            
        Returns:
            Dict containing structured release note content
        """
        try:
            logger.info(f"Generating AI release note for project {project_id}, sprints {start_sprint}-{end_sprint}")
            
            # Fetch backlog data for the specified sprints and project
            backlog_data = await self._fetch_backlog_data(
                tenant_name, project_id, start_sprint, end_sprint
            )
            
            if not backlog_data:
                return {
                    "content": {
                        "features": [],
                        "bug_fixes": [],
                        "improvements": [],
                        "breaking_changes": [],
                        "known_issues": []
                    },
                    "summary": "No backlog items found for the specified sprint range."
                }
            
            # Get latest version for suggestion
            latest_version = await self._get_latest_version(tenant_name, project_id)
            
            # Get project info for context
            project_info = await self._get_project_info(tenant_name, project_id)
            
            # Generate AI content using Mistral
            ai_content = await self._generate_ai_content(
                backlog_data, project_info, latest_version, start_sprint, end_sprint
            )
            
            # Add version suggestion to the result
            ai_content["suggested_version"] = self._increment_version(latest_version, ai_content.get("release_type", "MINOR"))
            
            logger.info(f"Successfully generated AI release note content for project {project_id}")
            return ai_content
            
        except Exception as e:
            logger.error(f"Failed to generate AI release note: {e}")
            # Return fallback content on error
            return {
                "content": {
                    "features": ["Error generating AI content - please review backlog manually"],
                    "bug_fixes": [],
                    "improvements": [],
                    "breaking_changes": [],
                    "known_issues": []
                },
                "summary": f"AI generation failed: {str(e)[:100]}"
            }
    
    async def _fetch_backlog_data(
        self,
        tenant_name: str,
        project_id: int,
        start_sprint: Optional[int],
        end_sprint: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Fetch backlog items for the specified project and sprint range"""
        
        # Build sprint filter conditions
        sprint_conditions = []
        params = [project_id]
        
        if start_sprint is not None:
            sprint_conditions.append("sprint_id >= %s")
            params.append(start_sprint)
        
        if end_sprint is not None:
            sprint_conditions.append("sprint_id <= %s")
            params.append(end_sprint)
        
        # If no sprint range specified, get recent items
        if not sprint_conditions:
            sprint_conditions.append("updated_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)")
        
        sprint_filter = "AND " + " AND ".join(sprint_conditions) if sprint_conditions else ""
        
        query = f"""
            SELECT 
                id, summary, description, issue_type, status, priority, 
                severity, assignee, tags, estimated_hours, logged_hours, 
                story_points, sprint_id, parent_task_id, start_date, 
                actual_start_date, end_date, actual_end_date, created_at, updated_at
            FROM `{tenant_name}`.project_backlog 
            WHERE project_id = %s AND issue_type != 'release' AND status IN ('done', 'closed', 'resolved', 'completed', 'finished', 'ready_for_release')
            {sprint_filter}
            ORDER BY 
                issue_type,
                priority DESC,
                created_at DESC
            LIMIT 50
        """
        
        return await self.db.execute_query(query, tuple(params), fetch_all=True)
        
    async def _get_latest_version(self, tenant_name: str, project_id: int) -> str:
        """Get the latest version number for a project"""
        query = f"SELECT version FROM `{tenant_name}`.release_notes WHERE project_id = %s ORDER BY created_at DESC LIMIT 1"
        result = await self.db.execute_query(query, (project_id,), fetch_one=True)
        return result['version'] if result else "1.0.0"

    def _increment_version(self, current_version: str, release_type: str) -> str:
        """Increment version based on release type (MAJOR, MINOR, PATCH, HOTFIX)"""
        try:
            # Clean version string (remove 'v' prefix if exists)
            clean_v = current_version.lower().replace('v', '').strip()
            parts = clean_v.split('.')
            
            # Ensure we have 3 parts (major, minor, patch)
            while len(parts) < 3:
                parts.append('0')
            
            major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
            
            if release_type == 'MAJOR':
                return f"{major + 1}.0.0"
            elif release_type == 'MINOR':
                return f"{major}.{minor + 1}.0"
            else: # PATCH or HOTFIX
                return f"{major}.{minor}.{patch + 1}"
        except:
            return "1.0.1" # Fallback
    
    async def _get_project_info(self, tenant_name: str, project_id: int) -> Dict[str, Any]:
        """Get project information for context"""
        query = f"""
            SELECT project_name, project_type, architecture_type
            FROM `{tenant_name}`.projects 
            WHERE project_id = %s
        """
        
        result = await self.db.execute_query(query, (project_id,), fetch_one=True)
        
        if result:
            return result
        return {"project_name": f"Project {project_id}", "description": "", "status": "active"}
    
    async def _generate_ai_content(
        self,
        backlog_data: List[Dict[str, Any]],
        project_info: Dict[str, Any],
        version: str,
        start_sprint: Optional[int],
        end_sprint: Optional[int]
    ) -> Dict[str, Any]:
        """Generate release note content using Mistral AI"""
        
        if not self.mistral_client.is_loaded():
            logger.warning("Mistral model not available, using structured fallback")
            return self._generate_structured_fallback(backlog_data, project_info)
        
        # Prepare context for AI
        context = self._prepare_ai_context(backlog_data, project_info, version, start_sprint, end_sprint)
        
        # Generate AI prompt
        prompt = self._build_release_note_prompt(context)
        
        try:
            # Generate content with Mistral
            ai_response = self.mistral_client.generate(
                prompt=prompt,
                max_tokens=2048,
                temperature=0.3,  # Lower temperature for more structured output
                top_p=0.95
            )
            
            if ai_response:
                # Parse AI response
                content = self._parse_ai_response(ai_response, backlog_data)
                return content
            else:
                logger.warning("AI generation returned empty response, using fallback")
                return self._generate_structured_fallback(backlog_data, project_info)
                
        except Exception as e:
            logger.error(f"AI generation failed: {e}")
            return self._generate_structured_fallback(backlog_data, project_info)
    
    def _prepare_ai_context(
        self,
        backlog_data: List[Dict[str, Any]],
        project_info: Dict[str, Any],
        version: str,
        start_sprint: Optional[int],
        end_sprint: Optional[int]
    ) -> Dict[str, Any]:
        """Prepare structured context for AI generation"""
        
        # Categorize backlog items by type and status
        categorized = {
            "features": [],
            "bug_fixes": [],
            "improvements": [],
            "tasks": [],
            "completed": [],
            "in_progress": [],
            "pending": []
        }
        
        for item in backlog_data:
            item_type = item.get('issue_type', '').lower()
            status = item.get('status', '').lower()
            
            # Categorize by type
            if item_type in ['story', 'feature', 'epic']:
                categorized['features'].append(item)
            elif item_type in ['bug', 'defect']:
                categorized['bug_fixes'].append(item)
            elif item_type in ['improvement', 'enhancement', 'change']:
                categorized['improvements'].append(item)
            else:
                categorized['tasks'].append(item)
            
            # Categorize by status
            # Be more inclusive of common "completed" statuses
            if status in ['done', 'closed', 'resolved', 'completed', 'finished', 'ready_for_release']:
                categorized['completed'].append(item)
            elif status in ['in_progress', 'doing', 'in_review', 'testing']:
                categorized['in_progress'].append(item)
            else:
                categorized['pending'].append(item)
        
        return {
            "project": project_info,
            "version": version,
            "sprint_range": f"{start_sprint or 'N/A'} - {end_sprint or 'N/A'}",
            "categorized": categorized,
            "total_items": len(backlog_data)
        }
    
    def _build_release_note_prompt(self, context: Dict[str, Any]) -> str:
        """Build AI prompt with few-shot examples for release note generation"""
        
        project_name = context['project'].get('project_name', 'Project')
        version = context['version']
        sprint_range = context['sprint_range']
        categorized = context['categorized']
        
        # Build detailed item lists for AI context
        features_text = "\n".join([
            f"- {item['summary']} | Priority: {item.get('priority', 'Medium')} | Points: {item.get('story_points', 'N/A')}"
            for item in categorized['features'][:8] 
        ])
        
        bugs_text = "\n".join([
            f"- {item['summary']} | Severity: {item.get('severity', 'Medium')} | Priority: {item.get('priority', 'Medium')}"
            for item in categorized['bug_fixes'][:8]
        ])
        
        improvements_text = "\n".join([
            f"- {item['summary']} | Priority: {item.get('priority', 'Medium')}"
            for item in categorized['improvements'][:8]
        ])
        
        prompt = f"""
### TASK
Create professional, user-facing release notes for {project_name} version {version} based on COMPLETED sprint work.

### CONTEXT
- Sprint Range: {sprint_range}
- Total Completed Items: {context['total_items']}

### COMPLETED ITEMS FOR ANALYSIS
FEATURES AND STORIES:
{features_text or "No new features completed"}

BUG FIXES:
{bugs_text or "No bugs fixed"}

IMPROVEMENTS AND CHANGES:
{improvements_text or "No improvements completed"}

### FEW-SHOT EXAMPLES FOR DESCRIPTIONS

Example 1 (Technical to Professional):
- Technical Summary: "IMPLEMENT AUTH"
- Professional Feature: "Integrated robust user authentication system with multi-factor support."

Example 2 (Bug Fix):
- Technical Summary: "FIX LOGIN BUG"
- Professional Bug Fix: "Resolved intermittent login timeout issues for users on slower connections."

Example 3 (Improvement):
- Technical Summary: "FASTER API"
- Professional Improvement: "Optimized primary API endpoints, reducing average response latency by 30%."

### INSTRUCTIONS
1. Transform technical summaries into professional, user-friendly descriptions.
2. Focus on business value and user benefits.
3. Use past tense (e.g., "Added", "Fixed", "Improved", "Optimized").
4. Detect the Release Type:
   - MAJOR: Significant new features or breaking changes.
   - MINOR: New features or significant improvements.
   - PATCH: Small improvements and bug fixes.
   - HOTFIX: Urgent bug fixes only.
5. If no items exist in a category, return an empty list [].
6. Keep descriptions concise (10-15 words).
7. Return ONLY valid JSON in the specified structure.

### JSON RESPONSE STRUCTURE
{{
    "release_type": "MAJOR|MINOR|PATCH|HOTFIX",
    "content": {{
        "features": ["description 1", "description 2"],
        "bug_fixes": ["description 1"],
        "improvements": ["description 1", "description 2"],
        "breaking_changes": [],
        "known_issues": []
    }},
    "summary": "Professional executive summary of this release (2-3 sentences max)."
}}

Return ONLY valid JSON, no additional explanatory text."""
        
        return prompt
    
    def _parse_ai_response(self, ai_response: str, backlog_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Parse and validate AI response"""
        try:
            # Try to extract JSON from response
            response_text = ai_response.strip()
            
            # Find JSON block if wrapped in other text
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')
            
            if start_idx >= 0 and end_idx >= 0:
                json_text = response_text[start_idx:end_idx + 1]
                parsed = json.loads(json_text)
                
                # Validate structure
                if 'content' in parsed and 'summary' in parsed:
                    content = parsed['content']
                    release_type = parsed.get('release_type', 'MINOR').upper()
                    if release_type not in ['MAJOR', 'MINOR', 'PATCH', 'HOTFIX']:
                        release_type = 'MINOR'
                    
                    # Ensure all required keys exist
                    required_keys = ['features', 'bug_fixes', 'improvements', 'breaking_changes', 'known_issues']
                    for key in required_keys:
                        if key not in content:
                            content[key] = []
                    
                    return {
                        'release_type': release_type,
                        'content': content,
                        'summary': parsed['summary']
                    }
            
            # If parsing fails, use fallback
            logger.warning("Failed to parse AI response, using structured fallback")
            return self._generate_structured_fallback(backlog_data, {})
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return self._generate_structured_fallback(backlog_data, {})
    
    def _generate_structured_fallback(
        self,
        backlog_data: List[Dict[str, Any]],
        project_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate structured release note content from completed backlog items"""
        
        content = {
            "features": [],
            "bug_fixes": [],
            "improvements": [],
            "breaking_changes": [],
            "known_issues": []
        }
        
        # Only process completed items (since we're filtering for 'done' status in query)
        for item in backlog_data:
            item_type = item.get('issue_type', '').lower()
            summary = item.get('summary', 'Unnamed item')
            
            # Create user-friendly descriptions
            if item_type in ['story', 'feature', 'epic']:
                # Transform technical summary to user-friendly feature description
                if 'implement' in summary.lower():
                    desc = summary.replace('Implement', 'Added').replace('implement', 'Added')
                elif 'create' in summary.lower():
                    desc = summary.replace('Create', 'Introduced').replace('create', 'Introduced')
                elif 'add' in summary.lower():
                    desc = summary
                else:
                    desc = f"Added {summary}"
                content['features'].append(desc.strip())
                
            elif item_type in ['bug', 'defect']:
                # Transform to fix description
                if 'fix' in summary.lower():
                    desc = summary
                elif 'resolve' in summary.lower():
                    desc = summary
                elif 'issue' in summary.lower() or 'problem' in summary.lower():
                    desc = f"Resolved {summary}"
                else:
                    desc = f"Fixed {summary}"
                content['bug_fixes'].append(desc.strip())
                
            elif item_type in ['improvement', 'enhancement', 'change']:
                # Transform to improvement description
                if 'improve' in summary.lower() or 'enhance' in summary.lower():
                    desc = summary
                elif 'optimize' in summary.lower():
                    desc = summary
                elif 'update' in summary.lower():
                    desc = summary.replace('Update', 'Updated').replace('update', 'Updated')
                else:
                    desc = f"Improved {summary}"
                content['improvements'].append(desc.strip())
        
        # Generate meaningful summary
        total_items = len(backlog_data)
        project_name = project_info.get('project_name', 'the project')
        
        if total_items > 0:
            feature_count = len(content['features'])
            bug_count = len(content['bug_fixes'])
            improvement_count = len(content['improvements'])
            
            summary_parts = []
            if feature_count > 0:
                summary_parts.append(f"{feature_count} new feature{'s' if feature_count != 1 else ''}")
            if bug_count > 0:
                summary_parts.append(f"{bug_count} bug fix{'es' if bug_count != 1 else ''}")
            if improvement_count > 0:
                summary_parts.append(f"{improvement_count} improvement{'s' if improvement_count != 1 else ''}")
            
            if summary_parts:
                summary = f"This release includes {', '.join(summary_parts)} for {project_name}."
            else:
                summary = f"Release prepared for {project_name} with {total_items} completed items."
        else:
            summary = f"No completed items found for this sprint in {project_name}."
        
        return {
            'content': content,
            'summary': summary,
            'release_type': 'PATCH' if len(content['bug_fixes']) > len(content['features']) else 'MINOR'
        }
