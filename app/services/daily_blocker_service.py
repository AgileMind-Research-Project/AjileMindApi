"""
Daily Blocker Service - AI-powered blocker analysis
"""

from typing import List, Dict, Any, Optional
from app.db.database import Database
from app.core.logger import logger
from app.services.llm_service import llm_service
from app.core.config import settings


class DailyBlockerService:
    """Service for managing and analyzing daily blockers"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def get_daily_blockers(self, tenant_name: str, project_id: Optional[int] = None, include_ai: bool = False) -> List[Dict[str, Any]]:
        """
        Fetch task updates with status 'BLOCKED' and optionally analyze them with AI.
        
        Args:
            tenant_name: Tenant schema name
            project_id: Optional project filter
            include_ai: Whether to perform AI analysis immediately
            
        Returns:
            List of blockers
        """
        try:
            # 1. Fetch blocked task updates joined with project_backlog for assignee
            # Using TRIM and COLLATE to handle potential spacing/collation mismatches
            # Also joining on project_id for better accuracy
            query = """
                SELECT 
                    tu.*, 
                    m.title as meeting_title, 
                    m.meeting_date, 
                    p.project_name,
                    pb.assignee as assignee_email
                FROM task_updates tu
                JOIN meetings m ON tu.meeting_id COLLATE utf8mb4_unicode_ci = m.meeting_id COLLATE utf8mb4_unicode_ci
                JOIN projects p ON tu.project_id = p.project_id
                LEFT JOIN project_backlog pb ON (
                    TRIM(tu.ticket_id) COLLATE utf8mb4_unicode_ci = TRIM(pb.id) COLLATE utf8mb4_unicode_ci
                    OR (tu.task_id IS NOT NULL AND tu.task_id = pb.id)
                )
                WHERE tu.detected_status = 'BLOCKED'
            """
            params = []
            if project_id:
                query += " AND tu.project_id = %s"
                params.append(project_id)
            
            query += " ORDER BY tu.created_at DESC"
            
            blockers = await self.db.execute_query(
                query, 
                tuple(params) if params else None, 
                fetch_all=True, 
                schema=tenant_name
            ) or []
            
            # 2. Add assignee info and optionally analyze with AI
            processed_blockers = []
            for b in blockers:
                # Fetch assignee names from tenant user table
                assignee_val = b.get('assignee_email')
                b.update({
                    "assignee_first_name": None,
                    "assignee_last_name": None,
                    "ai_suggestions": [],
                    "suggested_mentor_role": None
                })
                
                if assignee_val:
                    # If it's an email, look up names in the central users table
                    if "@" in assignee_val:
                        try:
                            # User tables are in the central database (settings.DB_NAME) named after the tenant
                            user_query = f"SELECT first_name, last_name FROM `{settings.DB_NAME}`.`{tenant_name}` WHERE email = %s"
                            user_data = await self.db.execute_query(user_query, (assignee_val,), fetch_one=True)
                            if user_data:
                                b.update({
                                    "assignee_first_name": user_data.get('first_name'),
                                    "assignee_last_name": user_data.get('last_name')
                                })
                            else:
                                # Fallback if user not found in central table: use email as name
                                b["assignee_first_name"] = assignee_val.split('@')[0]
                        except Exception as user_err:
                            logger.warning(f"Failed to fetch user data for {assignee_val}: {user_err}")
                    else:
                        # If not an email, assume it's already a name or username
                        b["assignee_first_name"] = assignee_val
                
                if include_ai:
                    blocker_desc = b.get('blocker_description')
                    if blocker_desc:
                        analysis = await llm_service.generate_blocker_suggestions(blocker_desc)
                        b.update({
                            "ai_suggestions": analysis.get("suggestions", []),
                            "suggested_mentor_role": analysis.get("suggested_mentor_role", "Senior Developer")
                        })
                    else:
                        b.update({
                            "ai_suggestions": ["Consult with the team lead."],
                            "suggested_mentor_role": "Project Manager"
                        })
                
                processed_blockers.append(b)
            
            return processed_blockers
            
        except Exception as e:
            logger.error(f"Error fetching daily blockers: {e}")
            raise

    async def analyze_blocker(self, tenant_name: str, blocker_id: int) -> Dict[str, Any]:
        """
        Perform AI analysis for a specific blocker.
        """
        try:
            # Fetch the blocker details
            query = "SELECT blocker_description FROM task_updates WHERE id = %s"
            blocker = await self.db.execute_query(query, (blocker_id,), fetch_one=True, schema=tenant_name)
            
            if not blocker:
                raise ValueError(f"Blocker with ID {blocker_id} not found")
            
            blocker_desc = blocker.get('blocker_description')
            if blocker_desc:
                analysis = await llm_service.generate_blocker_suggestions(blocker_desc)
                return {
                    "ai_suggestions": analysis.get("suggestions", []),
                    "suggested_mentor_role": analysis.get("suggested_mentor_role", "Senior Developer")
                }
            else:
                return {
                    "ai_suggestions": ["No description provided. Consult with your lead."],
                    "suggested_mentor_role": "Project Manager"
                }
                
        except Exception as e:
            logger.error(f"Error analyzing blocker {blocker_id}: {e}")
            raise
