"""
Report Template API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from typing import List, Optional
from app.db.database import Database, get_db
from app.services.template_service import TemplateService
from app.schemas.template import (
    TemplateCreate,
    TemplateUpdate,
    TemplateResponse
)
from app.utils.jwt import get_current_user_from_token
import logging

logger = logging.getLogger("agile_mind")

router = APIRouter()


@router.post("/", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_data: TemplateCreate,
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """
    Create a new report template.
    
    - **template_name**: Name of the template
    - **report_type**: Type of report (daily_standup, sprint_meeting, retrospective)
    - **sections**: Template sections structure
    - **header_content**: Optional header configuration
    - **footer_content**: Optional footer configuration
    - **styles**: Optional styling configuration
    - **is_default**: Whether this is a default template
    """
    try:
        service = TemplateService(db)
        result = await service.create_template(
            template_data=template_data,
            tenant_schema=current_user.get('tenant_schema'),
            created_by=current_user.get('user_id')
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail="Failed to create template")


@router.get("/", response_model=List[TemplateResponse])
async def list_templates(
    report_type: Optional[str] = None,
    is_default: Optional[bool] = None,
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """
    List all report templates with optional filters.
    
    - **report_type**: Filter by report type (optional)
    - **is_default**: Filter by default status (optional)
    """
    try:
        service = TemplateService(db)
        result = await service.list_templates(
            tenant_schema=current_user.get('tenant_schema'),
            report_type=report_type,
            is_default=is_default
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(status_code=500, detail="Failed to list templates")


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: int,
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """Get a specific template by ID."""
    try:
        service = TemplateService(db)
        result = await service.get_template(
            template_id=template_id,
            tenant_schema=current_user.get('tenant_schema')
        )
        
        return result
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching template: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch template")


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: int,
    template_data: TemplateUpdate,
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """
    Update a report template.
    
    Only provided fields will be updated.
    """
    try:
        service = TemplateService(db)
        result = await service.update_template(
            template_id=template_id,
            template_data=template_data,
            tenant_schema=current_user.get('tenant_schema')
        )
        
        return result
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating template: {e}")
        raise HTTPException(status_code=500, detail="Failed to update template")


@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """Delete a report template."""
    try:
        service = TemplateService(db)
        await service.delete_template(
            template_id=template_id,
            tenant_schema=current_user.get('tenant_schema')
        )
        
        return JSONResponse(
            status_code=200,
            content={"message": "Template deleted successfully"}
        )
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting template: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete template")
