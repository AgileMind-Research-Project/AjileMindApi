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
from app.core.logger import logger
from typing import List, Optional, Dict, Any
import json
from datetime import datetime


class ReportService:
    """Service for report operations"""
    
    def __init__(self, db: Database):
        self.db = db
        self.llm_service = get_llm_report_service()
    
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
            
            report_data = self.llm_service.generate_report(
                transcript=transcript.transcript_content,
                report_type=report_type,
                custom_prompt=request.custom_prompt if request.use_custom_prompt else None
            )
            
            # Convert Pydantic model to dict
            report_content = report_data.model_dump() if hasattr(report_data, 'model_dump') else report_data.dict()
            
            # Insert report into database
            insert_query = f"""
                INSERT INTO {tenant_schema}.reports
                (transcript_id, report_type, report_content, template_id, version, status, generated_by, tenant_schema)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            result = await self.db.execute_query(
                insert_query,
                (
                    request.transcript_id,
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
            
            # Get the inserted report ID from the cursor
            report_id = result.lastrowid
            
            if not report_id:
                raise Exception("Failed to get report ID after creation")
            
            logger.info(f"Report {report_id} created, verifying in {tenant_schema}.reports")
            
            # Verify record exists
            verify_query = f"SELECT COUNT(*) as cnt FROM {tenant_schema}.reports WHERE id = %s"
            verify_result = await self.db.execute_query(verify_query, (report_id,), fetch_one=True, schema=tenant_schema)
            
            if not verify_result or verify_result['cnt'] == 0:
                raise ValueError(f"Report {report_id} inserted but not found in {tenant_schema}.reports. This may indicate a schema mismatch.")
            
            logger.info(f"Report {report_id} verified, fetching full details")
            
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
