"""
Daily Blocker Service - AI-powered blocker analysis
"""

from typing import List, Dict, Any, Optional
from app.db.database import Database
from app.core.logger import logger
from app.services.llm_service import llm_service


class DailyBlockerService:
    """Service for managing and analyzing daily blockers"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def get_daily_blockers(self, tenant_name: str, project_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch task updates with status 'BLOCKED' and analyze them with AI.
        
        Args:
            tenant_name: Tenant schema name
            project_id: Optional project filter
            
        Returns:
            List of analyzed blockers
        """
        try:
            # 1. Fetch blocked task updates
            query = """
                SELECT tu.*, m.title as meeting_title, m.meeting_date, p.project_name
                FROM task_updates tu
                JOIN meetings m ON tu.meeting_id COLLATE utf8mb4_unicode_ci = m.meeting_id COLLATE utf8mb4_unicode_ci
                JOIN projects p ON tu.project_id = p.project_id
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
            
            # 2. Analyze each blocker with AI if needed
            analyzed_blockers = []
            for b in blockers:
                blocker_desc = b.get('blocker_description')
                if blocker_desc:
                    analysis = await llm_service.generate_blocker_suggestions(blocker_desc)
                    b.update({
                        "ai_suggestions": analysis.get("suggestions", []),
                        "suggested_mentor_role": analysis.get("suggested_mentor_role", "Senior Developer")
                    })
                else:
                    b.update({
                        "ai_suggestions": ["Consult with the team lead.", "Update task description for better AI analysis."],
                        "suggested_mentor_role": "Project Manager"
                    })
                analyzed_blockers.append(b)
            
            return analyzed_blockers
            
        except Exception as e:
            logger.error(f"Error fetching daily blockers: {e}")
            raise
