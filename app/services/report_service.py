"""
Report Service

Service layer for report management and generation operations.
"""

from app.db.database import Database
from app.schemas.report import (
    ReportGenerateRequest, ReportResponse, ReportExportRequest,
    ReportType, ReportStatus
)
from app.services.llm_report_service import get_llm_report_service
from app.services.transcript_service import TranscriptService
from app.services.new_task_service import NewTaskService
from app.services.recurring_bug_service import RecurringBugService
from app.services.template_service import TemplateService
from app.core.logger import logger
from typing import List, Optional, Dict, Any
import json
import re
from datetime import datetime, date


class ReportService:
    """Service for report operations"""
    
    def __init__(self, db: Database):
        self.db = db
        self.llm_service = get_llm_report_service()
    
    async def _get_transcript_speakers(self, transcript_id: int, tenant_schema: str) -> List[str]:
        """Extract speaker names from transcript content"""
        try:
            query = f"SELECT transcript_content FROM {tenant_schema}.transcripts WHERE id = %s"
            result = await self.db.execute_query(query, (transcript_id,), fetch_one=True, schema=tenant_schema)
            if result and result.get('transcript_content'):
                speakers = re.findall(r'(?:^|\])\s*([^:\[\]\n]{2,30}):', result['transcript_content'], re.MULTILINE)
                unique = []
                seen = set()
                for s in speakers:
                    name = s.strip()
                    if name and name.lower() not in seen and len(name) > 1:
                        seen.add(name.lower())
                        unique.append(name)
                return unique
        except Exception as e:
            logger.warning(f"Failed to extract speakers from transcript {transcript_id}: {e}")
        return []
    
    def _distribute_items_to_speakers(self, items: List[str], speakers: List[str]) -> List[Dict[str, Any]]:
        """Distribute flat string items to speakers, or group under 'Team' if no speakers"""
        if not speakers:
            return [{'name': 'Team', 'tasks': items}]
        
        # Try to match items to speakers by name mention
        speaker_tasks: Dict[str, List[str]] = {s: [] for s in speakers}
        unmatched = []
        
        for item in items:
            matched = False
            for speaker in speakers:
                if speaker.lower() in item.lower():
                    speaker_tasks[speaker].append(item)
                    matched = True
                    break
            if not matched:
                unmatched.append(item)
        
        # If no items matched any speaker, just group all under each speaker evenly
        has_matches = any(len(tasks) > 0 for tasks in speaker_tasks.values())
        if not has_matches:
            # Can't attribute - group under "Team" with all items
            return [{'name': 'Team', 'tasks': items}]
        
        # Add unmatched to first speaker
        if unmatched and speakers:
            speaker_tasks[speakers[0]].extend(unmatched)
        
        result = []
        for name, tasks in speaker_tasks.items():
            if tasks:
                result.append({'name': name, 'tasks': tasks})
        return result if result else [{'name': 'Team', 'tasks': items}]
    
    async def generate_report(
        self,
        request: ReportGenerateRequest,
        tenant_schema: str,
        generated_by: str
    ) -> ReportResponse:
        """Generate a new report from transcript using LLM"""
        try:
            logger.info(f"Generating report in schema: {tenant_schema}, by user: {generated_by}")
            
            # Validate schema exists
            check_query = "SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = %s"
            schema_check = await self.db.execute_query(check_query, (tenant_schema,), fetch_one=True)
            
            if not schema_check:
                raise ValueError(f"Schema '{tenant_schema}' does not exist. Available schemas should include: sas, saas, visionexdigital")
            
            # Get transcript
            transcript_service = TranscriptService(self.db)
            transcript = await transcript_service.get_transcript(
                request.transcript_id,
                tenant_schema
            )
            
            # Determine report type from transcript category
            # Handle both enum values and string values
            category_str = str(transcript.category).upper()
            
            # Remove enum class prefix if present (e.g., "TranscriptCategory.DAILY_STANDUP" -> "DAILY_STANDUP")
            if "." in category_str:
                category_str = category_str.split(".")[-1]
            
            report_type_map = {
                "DAILY_STANDUP": "daily_standup",
                "SPRINT_MEETING": "sprint_meeting",
                "SPRINT_PLANNING": "sprint_meeting",
                "RETROSPECTIVE": "retrospective",
                "BRAINSTORMING": "brainstorming"
            }
            report_type = report_type_map.get(category_str)
            
            if not report_type:
                raise ValueError(f"Unknown transcript category: {transcript.category}")
            
            # Generate report using LLM
            logger.info(f"Generating {report_type} report for transcript {request.transcript_id}")
            
            # If a template is selected, use template-aware generation
            template_sections = None
            if request.template_id:
                try:
                    template_service = TemplateService(self.db)
                    template = await template_service.get_template(request.template_id, tenant_schema)
                    template_sections = template.sections
                    logger.info(f"Using template {request.template_id} with {len(template_sections)} sections")
                except Exception as tmpl_err:
                    logger.warning(f"Failed to fetch template {request.template_id}, falling back to default: {tmpl_err}")
            
            if template_sections:
                # Template-based generation
                report_content = self.llm_service.generate_report_from_template(
                    transcript=transcript.transcript_content,
                    template_sections=template_sections,
                    report_type=report_type,
                    custom_prompt=request.custom_prompt if request.use_custom_prompt else None
                )
            else:
                # Default generation by report type
                report_data = self.llm_service.generate_report(
                    transcript=transcript.transcript_content,
                    report_type=report_type,
                    custom_prompt=request.custom_prompt if request.use_custom_prompt else None
                )
                # Convert Pydantic model to dict
                report_content = report_data.model_dump() if hasattr(report_data, 'model_dump') else report_data.dict()
            
            # Get project_id from transcript
            project_id = getattr(transcript, 'project_id', None)
            
            # Insert report into database
            insert_query = f"""
                INSERT INTO {tenant_schema}.reports
                (transcript_id, project_id, report_type, report_content, template_id, version, status, generated_by, tenant_schema)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            result = await self.db.execute_query(
                insert_query,
                (
                    request.transcript_id,
                    project_id,
                    report_type,
                    json.dumps(report_content),
                    request.template_id,
                    1,  # Initial version
                    ReportStatus.DRAFT.value,
                    generated_by,
                    tenant_schema
                ),
                commit=True,
                schema=tenant_schema
            )
            
            # Get the inserted report ID (execute_query returns lastrowid directly)
            report_id = result
            
            if not report_id:
                raise Exception("Failed to get report ID after creation")
            
            logger.info(f"Report {report_id} created, verifying in {tenant_schema}.reports")
            
            # Verify record exists
            verify_query = f"SELECT COUNT(*) as cnt FROM {tenant_schema}.reports WHERE id = %s"
            verify_result = await self.db.execute_query(verify_query, (report_id,), fetch_one=True, schema=tenant_schema)
            
            if not verify_result or verify_result['cnt'] == 0:
                raise ValueError(f"Report {report_id} inserted but not found in {tenant_schema}.reports. This may indicate a schema mismatch.")
            
            logger.info(f"Report {report_id} verified, fetching full details")
            
            # Update transcript's report_generated status to 'done'
            await transcript_service.update_report_generated_status(
                transcript_id=request.transcript_id,
                tenant_schema=tenant_schema,
                status='done'
            )
            logger.info(f"Transcript {request.transcript_id} report_generated status updated to 'done'")
            
            # Extract and store tasks/bugs based on report type
            try:
                if report_type == 'brainstorming':
                    # Extract new tasks from brainstorming report's next_steps
                    next_steps = report_content.get('next_steps', [])
                    if next_steps:
                        new_task_service = NewTaskService(self.db)
                        await new_task_service.create_tasks_from_report(
                            report_id=report_id,
                            transcript_id=request.transcript_id,
                            project_id=project_id,
                            next_steps=next_steps,
                            tenant_schema=tenant_schema
                        )
                        logger.info(f"Extracted {len(next_steps)} new tasks from brainstorming report {report_id}")
                
                elif report_type in ['retrospective', 'daily_standup', 'sprint_meeting']:
                    # Store ALL bugs/issues from report to recurring_bugs table
                    if project_id:
                        bug_service = RecurringBugService(self.db)
                        meeting_date = getattr(transcript, 'meeting_date', None) or date.today()
                        await bug_service.store_bugs_from_report(
                            tenant_schema=tenant_schema,
                            report_id=report_id,
                            transcript_id=request.transcript_id,
                            project_id=project_id,
                            report_type=report_type,
                            report_content=report_content,
                            meeting_date=meeting_date
                        )
                        logger.info(f"Stored issues from {report_type} report {report_id}")
            
            except Exception as extract_error:
                # Log but don't fail the report generation if extraction fails
                logger.warning(f"Error extracting tasks/bugs from report {report_id}: {extract_error}")
            
            # Fetch the created report with explicit schema
            return await self.get_report(report_id, tenant_schema)
        
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            raise
    
    async def get_report(
        self,
        report_id: int,
        tenant_schema: str
    ) -> ReportResponse:
        """Get a report by ID"""
        try:
            query = f"""
                SELECT id, transcript_id, report_type, report_content, template_id,
                       version, status, generated_by, created_at, updated_at
                FROM {tenant_schema}.reports
                WHERE id = %s
            """
            
            logger.info(f"Fetching report {report_id} from {tenant_schema}.reports")
            result = await self.db.execute_query(
                query, 
                (report_id,), 
                fetch_one=True,
                schema=tenant_schema
            )
            
            if not result:
                raise ValueError(f"Report with ID {report_id} not found in schema {tenant_schema}")
            
            # Parse report_content JSON
            report_content = json.loads(result['report_content']) if result.get('report_content') else {}
            
            # Migrate old daily standup formats to developer-centric format
            if result['report_type'] == 'daily_standup' and 'team_updates' not in report_content:
                # Old format has yesterday_work/today_plan/blockers as separate sections
                if any(k in report_content for k in ['yesterday_work', 'today_plan', 'blockers']):
                    speaker_names = await self._get_transcript_speakers(result['transcript_id'], tenant_schema)
                    
                    # First ensure items are person-grouped (not flat strings)
                    for field in ['yesterday_work', 'today_plan', 'blockers']:
                        items = report_content.get(field, [])
                        if isinstance(items, list) and len(items) > 0 and isinstance(items[0], str):
                            report_content[field] = self._distribute_items_to_speakers(items, speaker_names)
                    
                    # Convert to developer-centric team_updates
                    person_map = {}
                    for field, target in [('yesterday_work', 'yesterday_tasks'), ('today_plan', 'today_tasks'), ('blockers', 'blockers')]:
                        for person in (report_content.get(field) or []):
                            if isinstance(person, dict):
                                name = person.get('name', 'Team')
                                if name not in person_map:
                                    person_map[name] = {'name': name, 'role': None, 'yesterday_tasks': [], 'today_tasks': [], 'blockers': []}
                                person_map[name][target] = person.get('tasks', [])
                    
                    report_content['team_updates'] = list(person_map.values())
                    if 'blockers_summary' not in report_content:
                        report_content['blockers_summary'] = []
            
            return ReportResponse(
                id=result['id'],
                transcript_id=result['transcript_id'],
                report_type=result['report_type'],
                report_content=report_content,
                template_id=result.get('template_id'),
                version=result['version'],
                status=result['status'],
                generated_by=result['generated_by'],
                created_at=result['created_at'],
                updated_at=result['updated_at']
            )
        
        except Exception as e:
            logger.error(f"Error fetching report: {e}")
            raise
    
    async def list_reports(
        self,
        tenant_schema: str,
        transcript_id: Optional[int] = None,
        report_type: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """List reports with filters"""
        try:
            # Build WHERE clause
            where_clauses = []
            params = []
            
            if transcript_id:
                where_clauses.append("transcript_id = %s")
                params.append(transcript_id)
            
            if report_type:
                where_clauses.append("report_type = %s")
                params.append(report_type)
            
            if status:
                where_clauses.append("status = %s")
                params.append(status)
            
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            
            # Count total
            count_query = f"""
                SELECT COUNT(*) as total
                FROM {tenant_schema}.reports
                {where_sql}
            """
            count_result = await self.db.execute_query(count_query, tuple(params), fetch_one=True)
            total = count_result['total'] if count_result else 0
            
            # Fetch reports
            offset = (page - 1) * page_size
            list_query = f"""
                SELECT id, transcript_id, report_type, template_id, version, status, generated_by, created_at, updated_at
                FROM {tenant_schema}.reports
                {where_sql}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            params.extend([page_size, offset])
            
            results = await self.db.execute_query(list_query, tuple(params), fetch_all=True)
            
            reports = []
            for row in results or []:
                reports.append({
                    'id': row['id'],
                    'transcript_id': row['transcript_id'],
                    'report_type': row['report_type'],
                    'template_id': row.get('template_id'),
                    'version': row['version'],
                    'status': row['status'],
                    'generated_by': row['generated_by'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                })
            
            return {
                'reports': reports,
                'total': total,
                'page': page,
                'page_size': page_size
            }
        
        except Exception as e:
            logger.error(f"Error listing reports: {e}")
            raise
    
    async def update_report_content(
        self,
        report_id: int,
        report_content: Dict[str, Any],
        tenant_schema: str
    ) -> ReportResponse:
        """Update report content (for editing)"""
        try:
            query = f"""
                UPDATE {tenant_schema}.reports
                SET report_content = %s,
                    version = version + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            
            await self.db.execute_query(
                query,
                (json.dumps(report_content), report_id),
                commit=True
            )
            
            return await self.get_report(report_id, tenant_schema)
        
        except Exception as e:
            logger.error(f"Error updating report content: {e}")
            raise
    
    async def update_report_status(
        self,
        report_id: int,
        status: ReportStatus,
        tenant_schema: str
    ) -> ReportResponse:
        """Update report status"""
        try:
            query = f"""
                UPDATE {tenant_schema}.reports
                SET status = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            
            await self.db.execute_query(
                query,
                (status.value, report_id),
                commit=True
            )
            
            return await self.get_report(report_id, tenant_schema)
        
        except Exception as e:
            logger.error(f"Error updating report status: {e}")
            raise
    
    async def delete_report(
        self,
        report_id: int,
        tenant_schema: str
    ) -> bool:
        """Delete a report"""
        try:
            query = f"""
                DELETE FROM {tenant_schema}.reports
                WHERE id = %s
            """
            
            await self.db.execute_query(query, (report_id,), commit=True)
            
            logger.info(f"Report {report_id} deleted successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting report: {e}")
            raise
    
    async def get_reports_by_transcript(
        self,
        transcript_id: int,
        tenant_schema: str
    ) -> List[ReportResponse]:
        """Get all reports for a transcript"""
        try:
            query = f"""
                SELECT id, transcript_id, report_type, report_content, template_id,
                       version, status, generated_by, created_at, updated_at
                FROM {tenant_schema}.reports
                WHERE transcript_id = %s
                ORDER BY created_at DESC
            """
            
            results = await self.db.execute_query(query, (transcript_id,), fetch_all=True)
            
            reports = []
            for row in results or []:
                report_content = json.loads(row['report_content']) if row.get('report_content') else {}
                # Migrate old daily standup flat-string format
                if row['report_type'] == 'daily_standup':
                    needs_migration = False
                    for field in ['yesterday_work', 'today_plan', 'blockers']:
                        items = report_content.get(field, [])
                        if isinstance(items, list) and len(items) > 0 and isinstance(items[0], str):
                            needs_migration = True
                            break
                    if needs_migration:
                        speaker_names = await self._get_transcript_speakers(row['transcript_id'], tenant_schema)
                        for field in ['yesterday_work', 'today_plan', 'blockers']:
                            items = report_content.get(field, [])
                            if isinstance(items, list) and len(items) > 0 and isinstance(items[0], str):
                                report_content[field] = self._distribute_items_to_speakers(items, speaker_names)
                reports.append(ReportResponse(
                    id=row['id'],
                    transcript_id=row['transcript_id'],
                    report_type=row['report_type'],
                    report_content=report_content,
                    template_id=row.get('template_id'),
                    version=row['version'],
                    status=row['status'],
                    generated_by=row['generated_by'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                ))
            
            return reports
        
        except Exception as e:
            logger.error(f"Error fetching reports by transcript: {e}")
            raise
