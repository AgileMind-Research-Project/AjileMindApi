"""
Document Service

Service layer for document operations using reports table data.
Queries reports table and extracts content from report_content JSON.
"""

from typing import Optional, List, Dict, Any
from datetime import date, datetime
import json
from app.db.database import db
from app.core.logger import logger
from app.schemas.document import (
    DocumentCreate, DocumentResponse, DocumentListResponse,
    DocumentContentResponse, DocumentDateResponse
)


class DocumentService:
    """Service for managing documents using reports table data"""
    
    # Valid report types for chatbot
    VALID_REPORT_TYPES = ('daily_standup', 'sprint_meeting', 'retrospective', 'brainstorming')
    
    @staticmethod
    def _extract_text_from_report_content(report_content: Any, report_type: str) -> str:
        """
        Extract readable text from report_content JSON for RAG processing.
        Each report type has different JSON structure.
        """
        if not report_content:
            return ""
        
        # Parse JSON if string
        if isinstance(report_content, str):
            try:
                report_content = json.loads(report_content)
            except:
                return report_content
        
        if not isinstance(report_content, dict):
            return str(report_content)
        
        text_parts = []
        
        # Extract based on report type structure (matching actual schema)
        if report_type == 'daily_standup':
            # DailyStandupReport: yesterday_work, today_plan, blockers
            if 'yesterday_work' in report_content:
                for item in report_content.get('yesterday_work', []):
                    text_parts.append(f"Yesterday's work: {item}")
            if 'today_plan' in report_content:
                for item in report_content.get('today_plan', []):
                    text_parts.append(f"Today's plan: {item}")
            if 'blockers' in report_content:
                for item in report_content.get('blockers', []):
                    text_parts.append(f"Blocker: {item}")
            # Legacy fields
            if 'summary' in report_content:
                text_parts.append(f"Summary: {report_content['summary']}")
            if 'participants' in report_content:
                participants = report_content['participants']
                if isinstance(participants, list):
                    text_parts.append(f"Participants: {', '.join(str(p) for p in participants)}")
                else:
                    text_parts.append(f"Participants: {participants}")
            if 'discussions' in report_content:
                for disc in report_content.get('discussions', []):
                    if isinstance(disc, dict):
                        text_parts.append(f"Discussion: {disc.get('topic', '')} - {disc.get('summary', '')}")
                    else:
                        text_parts.append(f"Discussion: {disc}")
            if 'action_items' in report_content:
                for item in report_content.get('action_items', []):
                    if isinstance(item, dict):
                        text_parts.append(f"Action Item: {item.get('task', '')} - Assigned: {item.get('assignee', 'Unassigned')}")
                    else:
                        text_parts.append(f"Action Item: {item}")
                        
        elif report_type == 'sprint_meeting':
            # SprintMeetingReport: sprint_goals, progress_summary, issues_risks, action_items
            if 'sprint_goals' in report_content:
                goals = report_content['sprint_goals']
                if isinstance(goals, list):
                    for goal in goals:
                        text_parts.append(f"Sprint Goal: {goal}")
                else:
                    text_parts.append(f"Sprint Goals: {goals}")
            if 'progress_summary' in report_content:
                text_parts.append(f"Progress Summary: {report_content['progress_summary']}")
            if 'issues_risks' in report_content:
                for risk in report_content.get('issues_risks', []):
                    text_parts.append(f"Issue/Risk: {risk}")
            if 'action_items' in report_content:
                for item in report_content.get('action_items', []):
                    if isinstance(item, dict):
                        text_parts.append(f"Action Item: {item.get('task', '')} - Assigned: {item.get('assignee', 'Unassigned')}")
                    else:
                        text_parts.append(f"Action Item: {item}")
            # Legacy fields
            if 'summary' in report_content:
                text_parts.append(f"Summary: {report_content['summary']}")
            if 'completed_items' in report_content:
                for item in report_content.get('completed_items', []):
                    text_parts.append(f"Completed: {item}")
            if 'planned_items' in report_content:
                for item in report_content.get('planned_items', []):
                    text_parts.append(f"Planned: {item}")
            if 'risks' in report_content:
                for risk in report_content.get('risks', []):
                    if isinstance(risk, dict):
                        text_parts.append(f"Risk: {risk.get('description', risk)}")
                    else:
                        text_parts.append(f"Risk: {risk}")
                        
        elif report_type == 'retrospective':
            # RetrospectiveReport: what_went_well, what_didnt_go_well, improvements, action_points
            if 'what_went_well' in report_content:
                for item in report_content.get('what_went_well', []):
                    text_parts.append(f"What went well: {item}")
            if 'what_didnt_go_well' in report_content:
                for item in report_content.get('what_didnt_go_well', []):
                    text_parts.append(f"What didn't go well: {item}")
            if 'what_to_improve' in report_content:
                for item in report_content.get('what_to_improve', []):
                    text_parts.append(f"What to improve: {item}")
            if 'improvements' in report_content:
                for item in report_content.get('improvements', []):
                    text_parts.append(f"Improvement suggestion: {item}")
            if 'action_points' in report_content:
                for item in report_content.get('action_points', []):
                    if isinstance(item, dict):
                        text_parts.append(f"Action Point: {item.get('task', item)}")
                    else:
                        text_parts.append(f"Action Point: {item}")
            if 'action_items' in report_content:
                for item in report_content.get('action_items', []):
                    if isinstance(item, dict):
                        text_parts.append(f"Action Item: {item.get('task', item)}")
                    else:
                        text_parts.append(f"Action Item: {item}")
            if 'summary' in report_content:
                text_parts.append(f"Summary: {report_content['summary']}")
                        
        elif report_type == 'brainstorming':
            # BrainstormingMeetingReport: meeting_topic, meeting_objective, participants, ideas_generated, etc.
            if 'meeting_topic' in report_content:
                text_parts.append(f"Meeting Topic: {report_content['meeting_topic']}")
            if 'meeting_objective' in report_content:
                text_parts.append(f"Meeting Objective: {report_content['meeting_objective']}")
            if 'participants' in report_content:
                participants = report_content['participants']
                if isinstance(participants, list):
                    text_parts.append(f"Participants: {', '.join(str(p) for p in participants)}")
            if 'summary' in report_content:
                text_parts.append(f"Summary: {report_content['summary']}")
            if 'ideas_generated' in report_content:
                for idea in report_content.get('ideas_generated', []):
                    if isinstance(idea, dict):
                        text_parts.append(f"Idea: {idea.get('idea', '')} (proposed by: {idea.get('proposed_by', 'Unknown')})")
                    else:
                        text_parts.append(f"Idea: {idea}")
            if 'ideas' in report_content:
                for idea in report_content.get('ideas', []):
                    if isinstance(idea, dict):
                        text_parts.append(f"Idea: {idea.get('title', '')} - {idea.get('description', '')}")
                    else:
                        text_parts.append(f"Idea: {idea}")
            if 'top_ideas' in report_content:
                for idea in report_content.get('top_ideas', []):
                    text_parts.append(f"Top Idea: {idea}")
            if 'key_themes' in report_content:
                themes = report_content['key_themes']
                if isinstance(themes, list):
                    text_parts.append(f"Key Themes: {', '.join(str(t) for t in themes)}")
            if 'themes' in report_content:
                themes = report_content['themes']
                if isinstance(themes, list):
                    text_parts.append(f"Themes: {', '.join(str(t) for t in themes)}")
                else:
                    text_parts.append(f"Themes: {themes}")
            if 'decisions_made' in report_content:
                for decision in report_content.get('decisions_made', []):
                    if isinstance(decision, dict):
                        text_parts.append(f"Decision: {decision.get('decision', '')}")
                    else:
                        text_parts.append(f"Decision: {decision}")
            if 'next_steps' in report_content:
                for step in report_content.get('next_steps', []):
                    if isinstance(step, dict):
                        text_parts.append(f"Next Step: {step.get('task', step)}")
                    else:
                        text_parts.append(f"Next Step: {step}")
        
        # Fallback: extract all text recursively
        if not text_parts:
            text_parts = DocumentService._extract_all_text(report_content)
        
        return "\n".join(text_parts)
    
    @staticmethod
    def _extract_all_text(obj: Any, prefix: str = "") -> List[str]:
        """Recursively extract all text from a JSON object"""
        texts = []
        if isinstance(obj, dict):
            for key, value in obj.items():
                texts.extend(DocumentService._extract_all_text(value, f"{prefix}{key}: "))
        elif isinstance(obj, list):
            for item in obj:
                texts.extend(DocumentService._extract_all_text(item, prefix))
        elif obj is not None:
            text = str(obj).strip()
            if text and len(text) > 2:
                texts.append(f"{prefix}{text}")
        return texts
    
    @staticmethod
    def _generate_report_title(report_type: str, created_at: datetime) -> str:
        """Generate a human-readable title for a report"""
        type_names = {
            'daily_standup': 'Daily Standup',
            'sprint_meeting': 'Sprint Meeting',
            'retrospective': 'Retrospective',
            'brainstorming': 'Brainstorming Session'
        }
        type_name = type_names.get(report_type, report_type.replace('_', ' ').title())
        date_str = created_at.strftime('%Y-%m-%d') if created_at else 'Unknown Date'
        return f"{type_name} - {date_str}"
    
    @staticmethod
    async def create_document(doc_data: DocumentCreate, schema: str) -> DocumentResponse:
        """
        Create a new report entry with the specified report type
        """
        try:
            report_content = json.dumps({
                'summary': doc_data.doc_title,
                'content': doc_data.doc_content,
                'category': doc_data.category
            })

            # Use category as report_type (validated to be one of the ENUM values)
            report_type = doc_data.category if doc_data.category in ['daily_standup', 'sprint_meeting', 'retrospective', 'brainstorming'] else 'brainstorming'

            query = """
                INSERT INTO reports (transcript_id, report_type, report_content, template_id, status, created_at, updated_at)
                VALUES (NULL, %s, %s, NULL, 'published', NOW(), NOW())
            """

            await db.execute_query(
                query,
                (report_type, report_content),
                commit=True,
                schema=schema
            )

            # Get the last inserted report
            get_last = """
                SELECT id, report_type, report_content, created_at, updated_at
                FROM reports
                ORDER BY id DESC LIMIT 1
            """
            result = await db.execute_query(get_last, fetch_one=True, schema=schema)
            
            if result:
                return DocumentResponse(
                    id=result['id'],
                    doc_title=doc_data.doc_title,
                    doc_content=doc_data.doc_content,
                    uploaded_date=doc_data.uploaded_date,
                    category=doc_data.category,
                    created_at=result.get('created_at') or datetime.utcnow(),
                    updated_at=result.get('updated_at') or datetime.utcnow(),
                    is_active=True
                )
            
            raise Exception("Failed to retrieve created report")
            
        except Exception as e:
            logger.error(f"Error creating document: {e}")
            raise
    
    @staticmethod
    async def get_all_documents_content(schema: str, limit: int = 100, filter_date: str = None) -> List[DocumentContentResponse]:
        """
        Fetch all reports with content for multi-document RAG search
        Optionally filter by date (YYYY-MM-DD format)
        """
        try:
            if filter_date:
                query = """
                    SELECT id, report_type, report_content, created_at
                    FROM reports
                    WHERE report_type IN ('daily_standup', 'sprint_meeting', 'retrospective', 'brainstorming')
                      AND DATE(created_at) = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """
                params = (filter_date, limit)
            else:
                query = """
                    SELECT id, report_type, report_content, created_at
                    FROM reports
                    WHERE report_type IN ('daily_standup', 'sprint_meeting', 'retrospective', 'brainstorming')
                    ORDER BY created_at DESC
                    LIMIT %s
                """
                params = (limit,)

            results = await db.execute_query(
                query,
                params,
                fetch_all=True,
                schema=schema
            )
            
            if not results:
                return []
            
            docs: List[DocumentContentResponse] = []
            for row in results:
                report_type = row.get('report_type', 'unknown')
                created_at = row.get('created_at') or datetime.utcnow()
                
                content = DocumentService._extract_text_from_report_content(
                    row.get('report_content'),
                    report_type
                )
                
                if not content or len(content.strip()) < 10:
                    continue
                
                title = DocumentService._generate_report_title(report_type, created_at)
                
                docs.append(DocumentContentResponse(
                    id=row['id'],
                    doc_title=title,
                    doc_content=content,
                    uploaded_date=created_at.date() if isinstance(created_at, datetime) else created_at,
                    category=report_type
                ))

            return docs
            
        except Exception as e:
            logger.error(f"Error fetching all documents content: {e}")
            raise
    
    @staticmethod
    async def get_unique_dates(schema: str) -> List[DocumentDateResponse]:
        """
        Fetch all unique report dates with counts for date picker
        """
        try:
            query = """
                SELECT DATE(created_at) as report_date, COUNT(*) as count
                FROM reports
                WHERE report_type IN ('daily_standup', 'sprint_meeting', 'retrospective', 'brainstorming')
                GROUP BY DATE(created_at)
                ORDER BY report_date DESC
            """

            results = await db.execute_query(
                query,
                fetch_all=True,
                schema=schema
            )
            
            if not results:
                return []
            
            return [
                DocumentDateResponse(
                    uploaded_date=row['report_date'],
                    count=row['count']
                )
                for row in results
                if row.get('report_date')
            ]
            
        except Exception as e:
            logger.error(f"Error fetching unique dates: {e}")
            raise
    
    @staticmethod
    async def get_documents_by_date_with_content(
        uploaded_date: date,
        schema: str,
        limit: int = 100
    ) -> List[DocumentContentResponse]:
        """
        Fetch reports for a specific date with content
        """
        try:
            query = """
                SELECT id, report_type, report_content, created_at
                FROM reports
                WHERE DATE(created_at) = %s
                  AND report_type IN ('daily_standup', 'sprint_meeting', 'retrospective', 'brainstorming')
                ORDER BY created_at DESC
                LIMIT %s
            """

            results = await db.execute_query(
                query,
                (uploaded_date, limit),
                fetch_all=True,
                schema=schema
            )
            
            if not results:
                return []
            
            docs: List[DocumentContentResponse] = []
            for row in results:
                report_type = row.get('report_type', 'unknown')
                created_at = row.get('created_at') or datetime.utcnow()
                
                content = DocumentService._extract_text_from_report_content(
                    row.get('report_content'),
                    report_type
                )
                
                if not content or len(content.strip()) < 10:
                    continue
                
                title = DocumentService._generate_report_title(report_type, created_at)
                
                docs.append(DocumentContentResponse(
                    id=row['id'],
                    doc_title=title,
                    doc_content=content,
                    uploaded_date=created_at.date() if isinstance(created_at, datetime) else created_at,
                    category=report_type
                ))

            return docs
            
        except Exception as e:
            logger.error(f"Error fetching documents by date with content: {e}")
            raise
    
    @staticmethod
    async def get_documents_by_date(
        uploaded_date: date,
        schema: str,
        limit: int = 100
    ) -> List[DocumentListResponse]:
        """
        Fetch report list for a specific date
        """
        try:
            query = """
                SELECT id, report_type, created_at
                FROM reports
                WHERE DATE(created_at) = %s
                  AND report_type IN ('daily_standup', 'sprint_meeting', 'retrospective', 'brainstorming')
                ORDER BY created_at DESC
                LIMIT %s
            """

            results = await db.execute_query(
                query,
                (uploaded_date, limit),
                fetch_all=True,
                schema=schema
            )
            
            if not results:
                return []
            
            docs: List[DocumentListResponse] = []
            for row in results:
                report_type = row.get('report_type', 'unknown')
                created_at = row.get('created_at') or datetime.utcnow()
                
                title = DocumentService._generate_report_title(report_type, created_at)
                
                docs.append(DocumentListResponse(
                    id=row['id'],
                    doc_title=title,
                    uploaded_date=created_at.date() if isinstance(created_at, datetime) else created_at,
                    category=report_type,
                    created_at=created_at
                ))

            return docs
            
        except Exception as e:
            logger.error(f"Error fetching documents by date: {e}")
            raise
    
    @staticmethod
    async def get_document_content(document_id: int, schema: str) -> Optional[DocumentContentResponse]:
        """
        Retrieve report content by ID
        """
        try:
            query = """
                SELECT id, report_type, report_content, created_at
                FROM reports
                WHERE id = %s
            """

            result = await db.execute_query(
                query,
                (document_id,),
                fetch_one=True,
                schema=schema
            )
            
            if not result:
                logger.warning(f"Report not found: {document_id}")
                return None
            
            report_type = result.get('report_type', 'unknown')
            created_at = result.get('created_at') or datetime.utcnow()
            
            content = DocumentService._extract_text_from_report_content(
                result.get('report_content'),
                report_type
            )
            
            if not content:
                content = "No content available for this report."
            
            title = DocumentService._generate_report_title(report_type, created_at)
            
            return DocumentContentResponse(
                id=result['id'],
                doc_title=title,
                doc_content=content,
                uploaded_date=created_at.date() if isinstance(created_at, datetime) else created_at,
                category=report_type
            )
            
        except Exception as e:
            logger.error(f"Error retrieving document content: {e}")
            raise
    
    @staticmethod
    async def get_document_by_id(document_id: int, schema: str) -> Optional[DocumentResponse]:
        """
        Retrieve complete report by ID
        """
        try:
            query = """
                SELECT id, report_type, report_content, created_at, updated_at
                FROM reports
                WHERE id = %s
            """

            result = await db.execute_query(
                query,
                (document_id,),
                fetch_one=True,
                schema=schema
            )
            
            if not result:
                return None

            report_type = result.get('report_type', 'unknown')
            created_at = result.get('created_at') or datetime.utcnow()
            updated_at = result.get('updated_at') or datetime.utcnow()
            
            content = DocumentService._extract_text_from_report_content(
                result.get('report_content'),
                report_type
            )
            
            title = DocumentService._generate_report_title(report_type, created_at)
            
            return DocumentResponse(
                id=result['id'],
                doc_title=title,
                doc_content=content or "No content available",
                uploaded_date=created_at.date() if isinstance(created_at, datetime) else created_at,
                category=report_type,
                created_at=created_at,
                updated_at=updated_at,
                is_active=True
            )
            
        except Exception as e:
            logger.error(f"Error retrieving document: {e}")
            raise
    
    @staticmethod
    async def search_documents(
        search_query: str,
        schema: str,
        uploaded_date: Optional[date] = None,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[DocumentListResponse]:
        """
        Search reports by content
        """
        try:
            query = """
                SELECT id, report_type, report_content, created_at
                FROM reports
                WHERE report_type IN ('daily_standup', 'sprint_meeting', 'retrospective', 'brainstorming')
                  AND (
                    LOWER(JSON_UNQUOTE(JSON_EXTRACT(report_content, '$.summary'))) LIKE LOWER(%s)
                    OR LOWER(CAST(report_content AS CHAR)) LIKE LOWER(%s)
                  )
            """

            params = [f"%{search_query}%", f"%{search_query}%"]
            
            if uploaded_date:
                query += " AND DATE(created_at) = %s"
                params.append(uploaded_date)
            
            if category:
                query += " AND report_type = %s"
                params.append(category)
            
            query += f" ORDER BY created_at DESC LIMIT {limit}"
            
            results = await db.execute_query(
                query,
                tuple(params),
                fetch_all=True,
                schema=schema
            )
            
            if not results:
                return []
            
            docs: List[DocumentListResponse] = []
            for row in results:
                report_type = row.get('report_type', 'unknown')
                created_at = row.get('created_at') or datetime.utcnow()
                
                title = DocumentService._generate_report_title(report_type, created_at)
                
                docs.append(DocumentListResponse(
                    id=row['id'],
                    doc_title=title,
                    uploaded_date=created_at.date() if isinstance(created_at, datetime) else created_at,
                    category=report_type,
                    created_at=created_at
                ))

            return docs
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            raise
    
    @staticmethod
    async def get_documents_by_category(
        category: str,
        schema: str,
        limit: int = 100
    ) -> List[DocumentListResponse]:
        """
        Get reports by type (category = report_type)
        """
        try:
            query = """
                SELECT id, report_type, created_at
                FROM reports
                WHERE report_type = %s
                ORDER BY created_at DESC
                LIMIT %s
            """

            results = await db.execute_query(
                query,
                (category, limit),
                fetch_all=True,
                schema=schema
            )
            
            if not results:
                return []
            
            docs: List[DocumentListResponse] = []
            for row in results:
                report_type = row.get('report_type', 'unknown')
                created_at = row.get('created_at') or datetime.utcnow()
                
                title = DocumentService._generate_report_title(report_type, created_at)
                
                docs.append(DocumentListResponse(
                    id=row['id'],
                    doc_title=title,
                    uploaded_date=created_at.date() if isinstance(created_at, datetime) else created_at,
                    category=report_type,
                    created_at=created_at
                ))

            return docs
            
        except Exception as e:
            logger.error(f"Error fetching documents by category: {e}")
            raise

    @staticmethod
    async def get_documents_by_date_str(schema: str, date_str: str, limit: int = 1000) -> List[DocumentResponse]:
        """
        Get all reports for the schema filtered by date string (YYYY-MM-DD format)
        """
        try:
            query = """
                SELECT id, report_type, report_content, created_at, updated_at
                FROM reports
                WHERE report_type IN ('daily_standup', 'sprint_meeting', 'retrospective', 'brainstorming')
                  AND DATE(created_at) = %s
                ORDER BY created_at DESC
                LIMIT %s
            """
            
            results = await db.execute_query(
                query,
                (date_str, limit),
                fetch_all=True,
                schema=schema
            )
            
            if not results:
                return []
            
            docs: List[DocumentResponse] = []
            for row in results:
                report_type = row.get('report_type', 'unknown')
                created_at = row.get('created_at') or datetime.utcnow()
                updated_at = row.get('updated_at') or datetime.utcnow()
                
                content = DocumentService._extract_text_from_report_content(
                    row.get('report_content'),
                    report_type
                )
                
                if not content or len(content.strip()) < 5:
                    continue
                
                title = DocumentService._generate_report_title(report_type, created_at)
                
                docs.append(DocumentResponse(
                    id=row['id'],
                    doc_title=title,
                    doc_content=content,
                    uploaded_date=created_at.date() if isinstance(created_at, datetime) else created_at,
                    category=report_type,
                    created_at=created_at,
                    updated_at=updated_at,
                    is_active=True
                ))

            return docs

        except Exception as e:
            logger.error(f"Error fetching documents by date string: {e}")
            raise

    @staticmethod
    async def get_all_documents(schema: str, limit: int = 1000) -> List[DocumentResponse]:
        """
        Get all reports for the schema
        """
        try:
            query = """
                SELECT id, report_type, report_content, created_at, updated_at
                FROM reports
                WHERE report_type IN ('daily_standup', 'sprint_meeting', 'retrospective', 'brainstorming')
                ORDER BY created_at DESC
                LIMIT %s
            """
            
            results = await db.execute_query(
                query,
                (limit,),
                fetch_all=True,
                schema=schema
            )
            
            if not results:
                return []
            
            docs: List[DocumentResponse] = []
            for row in results:
                report_type = row.get('report_type', 'unknown')
                created_at = row.get('created_at') or datetime.utcnow()
                updated_at = row.get('updated_at') or datetime.utcnow()
                
                content = DocumentService._extract_text_from_report_content(
                    row.get('report_content'),
                    report_type
                )
                
                if not content or len(content.strip()) < 5:
                    continue
                
                title = DocumentService._generate_report_title(report_type, created_at)
                
                docs.append(DocumentResponse(
                    id=row['id'],
                    doc_title=title,
                    doc_content=content,
                    uploaded_date=created_at.date() if isinstance(created_at, datetime) else created_at,
                    category=report_type,
                    created_at=created_at,
                    updated_at=updated_at,
                    is_active=True
                ))

            return docs

        except Exception as e:
            logger.error(f"Error fetching all documents: {e}")
            raise

    @staticmethod
    async def delete_document(document_id: int, schema: str, soft_delete: bool = True) -> bool:
        """
        Delete report (change status to draft for soft delete)
        """
        try:
            if soft_delete:
                query = "UPDATE reports SET status = 'draft' WHERE id = %s"
            else:
                query = "DELETE FROM reports WHERE id = %s"

            await db.execute_query(
                query,
                (document_id,),
                commit=True,
                schema=schema
            )
            
            logger.info(f"Report deleted (soft_delete={soft_delete}): {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            raise


# Create singleton instance
document_service = DocumentService()
