"""
Recurring Bugs API Endpoints

Simplified approach:
- Store ALL bugs from reports
- Display bugs with same hash appearing 2+ times as "recurring"
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from app.db.database import Database, get_db
from app.utils.jwt import get_current_user_from_token
from app.services.recurring_bug_service import RecurringBugService
from app.core.logger import logger
from typing import Optional

router = APIRouter()


@router.get("/")
async def list_recurring_bugs(
    status: Optional[str] = Query(None, description="Filter by status: open, resolved, dismissed"),
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    show_all: bool = Query(False, description="Show all bugs including non-recurring (mention_count=1)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """
    List recurring bugs (bugs mentioned 2+ times).
    
    By default, only shows bugs mentioned in multiple meetings.
    Set show_all=true to see all bugs including those mentioned only once.
    """
    try:
        tenant_schema = current_user.get('tenant_name') or current_user.get('tenant_schema')
        
        service = RecurringBugService(db)
        result = await service.list_bugs(
            tenant_schema=tenant_schema,
            project_id=project_id,
            status=status,
            show_all=show_all,
            page=page,
            page_size=page_size
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Error listing recurring bugs: {e}")
        raise HTTPException(status_code=500, detail="Failed to list recurring bugs")


@router.get("/{bug_hash}")
async def get_bug_details(
    bug_hash: str,
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """Get all occurrences of a bug by its hash"""
    try:
        tenant_schema = current_user.get('tenant_name') or current_user.get('tenant_schema')
        
        service = RecurringBugService(db)
        result = await service.get_bug_details(
            tenant_schema=tenant_schema,
            bug_hash=bug_hash
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Bug not found")
        
        return {"success": True, "data": result}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting bug details: {e}")
        raise HTTPException(status_code=500, detail="Failed to get bug details")


@router.post("/{bug_hash}/resolve")
async def resolve_bug(
    bug_hash: str,
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """Mark all occurrences of a bug as resolved"""
    try:
        tenant_schema = current_user.get('tenant_name') or current_user.get('tenant_schema')
        
        service = RecurringBugService(db)
        await service.update_bug_status(
            tenant_schema=tenant_schema,
            bug_hash=bug_hash,
            status='resolved'
        )
        
        return {"success": True, "message": "Bug marked as resolved"}
    
    except Exception as e:
        logger.error(f"Error resolving bug: {e}")
        raise HTTPException(status_code=500, detail="Failed to resolve bug")


@router.post("/{bug_hash}/dismiss")
async def dismiss_bug(
    bug_hash: str,
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """Dismiss all occurrences of a bug"""
    try:
        tenant_schema = current_user.get('tenant_name') or current_user.get('tenant_schema')
        
        service = RecurringBugService(db)
        await service.update_bug_status(
            tenant_schema=tenant_schema,
            bug_hash=bug_hash,
            status='dismissed'
        )
        
        return {"success": True, "message": "Bug dismissed"}
    
    except Exception as e:
        logger.error(f"Error dismissing bug: {e}")
        raise HTTPException(status_code=500, detail="Failed to dismiss bug")


@router.post("/{bug_hash}/create-backlog")
async def create_backlog_for_bug(
    bug_hash: str,
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """Create a backlog item for a recurring bug"""
    try:
        tenant_schema = current_user.get('tenant_name') or current_user.get('tenant_schema')
        
        service = RecurringBugService(db)
        backlog_id = await service.create_backlog_item(
            tenant_schema=tenant_schema,
            bug_hash=bug_hash
        )
        
        return {
            "success": True, 
            "message": "Backlog item created",
            "backlog_id": backlog_id
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating backlog for bug: {e}")
        raise HTTPException(status_code=500, detail="Failed to create backlog item")
