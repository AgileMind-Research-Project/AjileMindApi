"""
Backlog Priority Management API Endpoints
Handles prioritized backlog items view and rank updates
"""

from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from typing import Dict, Any, List
from pydantic import BaseModel, Field

from app.db.database import db, Database
from app.core.logger import logger
from app.utils.jwt import get_current_user_from_token
from app.services.backlog_service import BacklogService
from app.services.jira_service import JiraService


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
        default=[], 
        description="List of {backlog_id, new_rank} updates"
    )
    sync_to_jira: bool = False


# ============================================
# DEPENDENCIES
# ============================================

async def get_database() -> Database:
    """Dependency to get database instance"""
    return db


async def get_backlog_service(database: Database = Depends(get_database)) -> BacklogService:
    """Dependency to get backlog service instance"""
    return BacklogService(database)


async def get_jira_service(database: Database = Depends(get_database)) -> JiraService:
    """Dependency to get Jira service instance"""
    return JiraService(database)


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
        # Only show items NOT assigned to a sprint yet
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
            WHERE pbp.project_id = %s AND pbp.sprint_id IS NULL
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
    database: Database = Depends(get_database),
    backlog_service: BacklogService = Depends(get_backlog_service),
    jira_service: JiraService = Depends(get_jira_service)
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
        
        if not request.updates and not request.sync_to_jira:
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
        
        if request.sync_to_jira:
            try:
                # Get project key
                project_query = "SELECT `key` FROM projects WHERE project_id = %s"
                project_result = await database.execute_query(
                    project_query,
                    (project_id,),
                    fetch_one=True,
                    schema=tenant_name
                )
                
                if project_result and project_result.get('key'):
                    sync_result = await backlog_service.sync_priority_items_to_jira(
                        tenant_name, 
                        project_id, 
                        project_result['key'], 
                        jira_service
                    )
                    logger.info(f" synced {sync_result.get('synced_count')} items to Jira")
            except Exception as e:
                logger.error(f"Failed to sync to Jira: {str(e)}")
                # Don't fail the whole request, just log error
        
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


@router.get(
    "/projects/{project_id}/available-backlog",
    summary="Get Available Backlog Items",
    description="Get backlog items that are NOT yet in the priority list"
)
async def get_available_backlog(
    project_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    database: Database = Depends(get_database)
) -> Dict[str, Any]:
    """
    Get backlog items that are not yet prioritized.
    
    Returns items from project_backlog that are NOT in project_backlog_priority.
    """
    try:
        tenant_name = current_user.get("tenant_name")
        
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        # Query to get backlog items NOT in priority table
        query = """
            SELECT 
                pb.id as backlog_id,
                pb.summary,
                pb.description,
                pb.issue_type,
                pb.status,
                pb.priority,
                pb.assignee,
                pb.story_points
            FROM project_backlog pb
            WHERE pb.project_id = %s
            AND pb.id NOT IN (
                SELECT backlog_id 
                FROM project_backlog_priority 
                WHERE project_id = %s
            )
            ORDER BY pb.created_at DESC
        """
        
        results = await database.execute_query(
            query,
            (project_id, project_id),
            fetch_all=True,
            schema=tenant_name
        )
        
        items = []
        for row in results:
            items.append({
                "backlog_id": row["backlog_id"],
                "summary": row["summary"],
                "description": row.get("description"),
                "issue_type": row["issue_type"],
                "status": row["status"],
                "priority": row.get("priority"),
                "assignee": row.get("assignee"),
                "story_points": row.get("story_points", 0)
            })
        
        logger.info(f"Retrieved {len(items)} available backlog items for project {project_id}")
        
        return {
            "success": True,
            "message": f"Found {len(items)} available item(s)",
            "data": {
                "project_id": project_id,
                "items": items
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting available backlog: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve available backlog: {str(e)}"
        )


@router.post(
    "/projects/{project_id}/prioritized-backlog/add",
    summary="Add Item to Priority List",
    description="Add a backlog item to the priority list"
)
async def add_to_priority_list(
    project_id: int,
    request: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    database: Database = Depends(get_database)
) -> Dict[str, Any]:
    """
    Add a backlog item to the priority list.
    
    Request body: { "backlog_id": "ITEM-123" }
    """
    try:
        tenant_name = current_user.get("tenant_name")
        
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        backlog_id = request.get("backlog_id")
        if not backlog_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="backlog_id is required"
            )
        
        # Get next rank (max + 1)
        max_rank_query = """
            SELECT COALESCE(MAX(`rank`), 0) as max_rank
            FROM project_backlog_priority
            WHERE project_id = %s
        """
        
        rank_result = await database.execute_query(
            max_rank_query,
            (project_id,),
            fetch_one=True,
            schema=tenant_name
        )
        
        next_rank = (rank_result["max_rank"] if rank_result else 0) + 1
        
        # Insert into priority table
        insert_query = """
            INSERT INTO project_backlog_priority 
            (project_id, backlog_id, `rank`, sprint_id, created_at, updated_at)
            VALUES (%s, %s, %s, NULL, NOW(), NOW())
        """
        
        result = await database.execute_query(
            insert_query,
            (project_id, backlog_id, next_rank),
            commit=True,
            schema=tenant_name
        )
        
        if result:
            logger.info(f"Added item {backlog_id} to priority list with rank {next_rank}")
            return {
                "success": True,
                "message": "Item added to priority list",
                "data": {
                    "project_id": project_id,
                    "backlog_id": backlog_id,
                    "rank": next_rank
                }
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add item to priority list"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding to priority list: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add item: {str(e)}"
        )


@router.post(
    "/projects/{project_id}/prioritized-backlog/sync",
    summary="Sync Prioritized Backlog to Jira",
    description="Sync prioritized backlog items to Jira based on rank. Runs in background."
)
async def sync_priority_items(
    project_id: int,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    database: Database = Depends(get_database)
) -> Dict[str, Any]:
    """
    Sync prioritized items to Jira (Background Task).
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(status_code=400, detail="Tenant name not found")
            
        backlog_service = BacklogService(database)
        project_key = await backlog_service.get_project_key(tenant_name, project_id) # helper or just pass ID
        
        # Add to background tasks
        background_tasks.add_task(
            backlog_service.sync_priority_items_to_jira,
            tenant_name=tenant_name,
            project_id=project_id,
            user_email=current_user.get("email") # Pass user email if needed for assignee fallback or logging
        )
        
        return {
            "success": True,
            "message": "Sync started in background.",
            "data": None
        }

    except Exception as e:
        logger.error(f"Failed to initiate sync for project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate sync: {str(e)}"
        )
@router.delete(
    "/projects/{project_id}/prioritized-backlog/{backlog_id}",
    summary="Remove Item from Priority List",
    description="Remove a backlog item from the priority list"
)
async def remove_from_priority_list(
    project_id: int,
    backlog_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    database: Database = Depends(get_database)
) -> Dict[str, Any]:
    """
    Remove a backlog item from the priority list.
    """
    try:
        tenant_name = current_user.get("tenant_name")
        
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        # Delete from priority table
        delete_query = """
            DELETE FROM project_backlog_priority
            WHERE project_id = %s AND backlog_id = %s
        """
        
        result = await database.execute_query(
            delete_query,
            (project_id, backlog_id),
            commit=True,
            schema=tenant_name
        )
        
        if result:
            logger.info(f"Removed item {backlog_id} from priority list")
            return {
                "success": True,
                "message": "Item removed from priority list",
                "data": {
                    "project_id": project_id,
                    "backlog_id": backlog_id
                }
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found in priority list"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing from priority list: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove item: {str(e)}"
        )
