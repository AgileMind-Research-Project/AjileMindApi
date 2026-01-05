"""
Backlog Priority Management API Endpoints
Handles prioritized backlog items view and rank updates
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, List
from pydantic import BaseModel, Field

from app.db.database import db, Database
from app.core.logger import logger
from app.utils.jwt import get_current_user_from_token


router = APIRouter()


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class BacklogPriorityItem(BaseModel):
    """Prioritized backlog item"""
    backlog_id: str
    rank: int
    summary: str
    description: str | None
    issue_type: str
    status: str
    priority: str | None
    assignee: str | None
    story_points: int
    sprint_id: int | None


class UpdateRankRequest(BaseModel):
    """Request to update backlog item ranks"""
    updates: List[Dict[str, Any]] = Field(
        ..., 
        description="List of {backlog_id, new_rank} updates"
    )


# ============================================
# DEPENDENCIES
# ============================================

async def get_database() -> Database:
    """Dependency to get database instance"""
    return db


# ============================================
# PRIORITIZED BACKLOG ENDPOINTS
# ============================================

@router.get(
    "/projects/{project_id}/prioritized-backlog",
    summary="Get Prioritized Backlog Items",
    description="Get all prioritized backlog items for a project, ordered by rank"
)
async def get_prioritized_backlog(
    project_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    database: Database = Depends(get_database)
) -> Dict[str, Any]:
    """
    Get prioritized backlog items for a project.
    
    Returns backlog items with their priority rankings, ordered by rank (1 = highest).
    """
    try:
        tenant_name = current_user.get("tenant_name")
        
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        # Query to get prioritized backlog items with details
        query = """
            SELECT 
                pbp.backlog_id,
                pbp.`rank`,
                pbp.sprint_id,
                pb.summary,
                pb.description,
                pb.issue_type,
                pb.status,
                pb.priority,
                pb.assignee,
                pb.story_points
            FROM project_backlog_priority pbp
            INNER JOIN project_backlog pb ON pbp.backlog_id = pb.id
            WHERE pbp.project_id = %s
            ORDER BY pbp.`rank` ASC
        """
        
        results = await database.execute_query(
            query,
            (project_id,),
            fetch_all=True,
            schema=tenant_name
        )
        
        if not results:
            return {
                "success": True,
                "message": "No prioritized backlog items found",
                "data": {
                    "project_id": project_id,
                    "items": []
                }
            }
        
        # Format results
        items = []
        for row in results:
            items.append({
                "backlog_id": row["backlog_id"],
                "rank": row["rank"],
                "sprint_id": row.get("sprint_id"),
                "summary": row["summary"],
                "description": row.get("description"),
                "issue_type": row["issue_type"],
                "status": row["status"],
                "priority": row.get("priority"),
                "assignee": row.get("assignee"),
                "story_points": row.get("story_points", 0)
            })
        
        logger.info(f"Retrieved {len(items)} prioritized backlog items for project {project_id}")
        
        return {
            "success": True,
            "message": f"Found {len(items)} prioritized item(s)",
            "data": {
                "project_id": project_id,
                "items": items
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prioritized backlog: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve prioritized backlog: {str(e)}"
        )


@router.put(
    "/projects/{project_id}/prioritized-backlog/update-ranks",
    summary="Update Backlog Item Ranks",
    description="Update the priority ranks of backlog items"
)
async def update_backlog_ranks(
    project_id: int,
    request: UpdateRankRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    database: Database = Depends(get_database)
) -> Dict[str, Any]:
    """
    Update priority ranks for backlog items.
    
    Accepts a list of backlog_id and new_rank updates.
    """
    try:
        tenant_name = current_user.get("tenant_name")
        
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        if not request.updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No updates provided"
            )
        
        # Update each backlog item's rank
        update_query = """
            UPDATE project_backlog_priority
            SET `rank` = %s, updated_at = NOW()
            WHERE project_id = %s AND backlog_id = %s
        """
        
        updated_count = 0
        
        for update in request.updates:
            backlog_id = update.get("backlog_id")
            new_rank = update.get("new_rank")
            
            if not backlog_id or new_rank is None:
                continue
            
            result = await database.execute_query(
                update_query,
                (new_rank, project_id, backlog_id),
                commit=True,
                schema=tenant_name
            )
            
            if result:
                updated_count += 1
        
        logger.info(f"Updated {updated_count} backlog item ranks for project {project_id}")
        
        return {
            "success": True,
            "message": f"Successfully updated {updated_count} item rank(s)",
            "data": {
                "project_id": project_id,
                "updated_count": updated_count
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating backlog ranks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update backlog ranks: {str(e)}"
        )
