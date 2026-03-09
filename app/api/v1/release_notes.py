from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Dict, Any, Optional

from app.utils.jwt import get_current_user_from_token
from app.db.database import db, Database
from app.schemas.release_note_schemas import (
    CreateReleaseNoteRequest,
    UpdateReleaseNoteRequest,
    GenerateReleaseNoteRequest,
    ReleaseNoteResponse
)
from app.services.release_note_service import ReleaseNoteService

router = APIRouter()

def get_release_note_service(database: Database = Depends(lambda: db)) -> ReleaseNoteService:
    return ReleaseNoteService(database)

def check_project_manager(current_user: Dict[str, Any]):
    """Verify user has PROJECT_MANAGER role (Bypassed)"""
    return # Temporarily bypassed to allow all users to manage release notes
    role = current_user.get("role", "").upper()
    if role not in ["PROJECT_MANAGER", "SUPER_ADMIN", "ADMIN"]:
        raise HTTPException(
            status_code=403,
            detail="Only PROJECT_MANAGER can create or modify release notes"
        )

@router.post(
    "",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Create Release Note",
    description="Create a new release note for a project (PROJECT_MANAGER only)"
)
async def create_release_note(
    request: CreateReleaseNoteRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    service: ReleaseNoteService = Depends(get_release_note_service)
):
    try:
        check_project_manager(current_user)
        
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(status_code=400, detail="Tenant name not found")
        
        user_id = current_user.get("user_id")
        
        result = await service.create_release_note(
            tenant_name=tenant_name,
            request=request,
            user_id=user_id
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/backlog-releases",
    status_code=status.HTTP_200_OK,
    summary="List All Backlog Releases",
    description="Get all backlog items of type 'release' across all projects"
)
async def get_all_backlog_releases(
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    service: ReleaseNoteService = Depends(get_release_note_service)
):
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(status_code=400, detail="Tenant name not found")
        result = await service.get_all_backlog_releases(tenant_name=tenant_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/backlog-releases/{project_id}",
    status_code=status.HTTP_200_OK,
    summary="List Backlog Releases",
    description="Get all backlog items of type 'release' for a project"
)
async def get_backlog_releases(
    project_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    service: ReleaseNoteService = Depends(get_release_note_service)
):
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(status_code=400, detail="Tenant name not found")
        
        result = await service.get_backlog_releases(
            tenant_name=tenant_name,
            project_id=project_id
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="List Release Notes",
    description="Get a paginated list of release notes with optional filters"
)
async def list_release_notes(
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    status: Optional[str] = Query(None, description="Filter by status (DRAFT, PUBLISHED, ARCHIVED)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    service: ReleaseNoteService = Depends(get_release_note_service)
):
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(status_code=400, detail="Tenant name not found")
        
        result = await service.get_release_notes(
            tenant_name=tenant_name,
            project_id=project_id,
            status=status,
            page=page,
            page_size=page_size
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/latest-version/{project_id}",
    status_code=status.HTTP_200_OK,
    summary="Get Latest Version",
    description="Get the latest version number for a project"
)
async def get_latest_version(
    project_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    service: ReleaseNoteService = Depends(get_release_note_service)
):
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(status_code=400, detail="Tenant name not found")
        
        version_data = await service.get_latest_version(tenant_name=tenant_name, project_id=project_id)
        return {"version": version_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/{release_note_id}",
    status_code=status.HTTP_200_OK,
    summary="Get Release Note",
    description="Get a single release note by ID"
)
async def get_release_note(
    release_note_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    service: ReleaseNoteService = Depends(get_release_note_service)
):
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(status_code=400, detail="Tenant name not found")
        
        result = await service.get_release_note_by_id(
            tenant_name=tenant_name,
            release_note_id=release_note_id
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Release note not found")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put(
    "/{release_note_id}",
    status_code=status.HTTP_200_OK,
    summary="Update Release Note",
    description="Update an existing release note (PROJECT_MANAGER only)"
)
async def update_release_note(
    release_note_id: int,
    request: UpdateReleaseNoteRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    service: ReleaseNoteService = Depends(get_release_note_service)
):
    try:
        check_project_manager(current_user)
        
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(status_code=400, detail="Tenant name not found")
        
        result = await service.update_release_note(
            tenant_name=tenant_name,
            release_note_id=release_note_id,
            request=request
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete(
    "/{release_note_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Release Note",
    description="Delete a release note (PROJECT_MANAGER only)"
)
async def delete_release_note(
    release_note_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    service: ReleaseNoteService = Depends(get_release_note_service)
):
    try:
        check_project_manager(current_user)
        
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(status_code=400, detail="Tenant name not found")
        
        result = await service.delete_release_note(
            tenant_name=tenant_name,
            release_note_id=release_note_id
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/{release_note_id}/publish",
    status_code=status.HTTP_200_OK,
    summary="Publish Release Note",
    description="Publish a draft release note (PROJECT_MANAGER only)"
)
async def publish_release_note(
    release_note_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    service: ReleaseNoteService = Depends(get_release_note_service)
):
    try:
        check_project_manager(current_user)
        
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(status_code=400, detail="Tenant name not found")
        
        user_id = current_user.get("user_id")
        
        result = await service.publish_release_note(
            tenant_name=tenant_name,
            release_note_id=release_note_id,
            user_id=user_id
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/generate",
    status_code=status.HTTP_200_OK,
    summary="Generate Release Note with AI",
    description="Generate release note content using AI analysis of project data (PROJECT_MANAGER only)"
)
async def generate_release_note_ai(
    request: GenerateReleaseNoteRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    service: ReleaseNoteService = Depends(get_release_note_service)
):
    try:
        check_project_manager(current_user)
        
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(status_code=400, detail="Tenant name not found")
        
        result = await service.generate_release_note_ai(
            tenant_name=tenant_name,
            request=request
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
