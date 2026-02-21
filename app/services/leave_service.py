"""
Leave Service

Manages developer leave records linked to sprints.
"""

from typing import List, Dict, Any, Optional
from datetime import date
from fastapi import HTTPException, status
from app.db.database import Database
from app.core.logger import logger

class LeaveService:
    """Service for managing sprint leaves"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def add_sprint_leave(
        self,
        tenant_name: str,
        sprint_id: int,
        project_id: int,
        developer_name: str,
        leave_date: date,
        leave_hours: int,
        leave_type: str = 'Full Day',
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add a leave record for a developer in a specific sprint.
        
        Args:
            tenant_name: Tenant database name
            sprint_id: ID of the sprint
            project_id: ID of the project
            developer_name: Name/ID of the developer
            leave_date: Date of leave
            leave_hours: Number of hours
            leave_type: Type of leave (Full Day, Half Day, Short Leave)
            reason: Reason for leave
            
        Returns:
            Created leave record
        """
        try:
            # Verify project and sprint exist (integrity check)
            # relying on FK constraints usually, but good to be explicit or catch FK errors
            
            query = """
                INSERT INTO sprint_leave (
                    sprint_id, project_id, developer_name, 
                    leave_date, leave_hours, leave_type, reason
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            await self.db.execute_query(
                query,
                (sprint_id, project_id, developer_name, leave_date, leave_hours, leave_type, reason),
                commit=True,
                schema=tenant_name
            )
            
            # Fetch back the created record
            # Use LAST_INSERT_ID() logic or select by parameters
            select_query = """
                SELECT * FROM sprint_leave 
                WHERE sprint_id = %s AND developer_name = %s AND leave_date = %s
                ORDER BY leave_id DESC LIMIT 1
            """
            
            created_leave = await self.db.execute_query(
                select_query,
                (sprint_id, developer_name, leave_date),
                fetch_one=True,
                schema=tenant_name
            )
            
            logger.info(f"Added leave for {developer_name} on {leave_date}")
            return created_leave
            
        except Exception as e:
            logger.error(f"Failed to add sprint leave: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to add leave record: {str(e)}"
            )

    async def get_sprint_leaves(
        self,
        tenant_name: str,
        sprint_id: int
    ) -> List[Dict[str, Any]]:
        """Get all leaves for a specific sprint"""
        try:
            query = "SELECT * FROM sprint_leave WHERE sprint_id = %s ORDER BY leave_date"
            return await self.db.execute_query(
                query,
                (sprint_id,),
                fetch_all=True,
                schema=tenant_name
            ) or []
        except Exception as e:
            logger.error(f"Failed to get sprint leaves: {str(e)}")
            return []
