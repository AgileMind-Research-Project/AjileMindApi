"""
Reports API Endpoints

Handles report generation, management, and export.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, Response
from app.db.database import Database, get_db
from app.utils.jwt import get_current_user_from_token
from app.schemas.report import (
    ReportGenerateRequest, ReportResponse, ReportExportRequest,
    ReportStatus, ReportType
)
from app.services.report_service import ReportService
from app.utils.report_export import export_report
from app.core.logger import logger
from typing import Optional, List, Dict, Any

router = APIRouter()


@router.post("/generate", response_model=ReportResponse, status_code=201)
async def generate_report(
    request: ReportGenerateRequest,
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """
    Generate a new report from a transcript using LLM.
    
    - **transcript_id**: ID of the transcript to generate report from
    - **template_id**: Optional template ID to apply
    - **use_custom_prompt**: Whether to use a custom prompt
    - **custom_prompt**: Optional custom prompt for LLM generation
    """
    try:
        service = ReportService(db)
        result = await service.generate_report(
            request=request,
            tenant_schema=current_user.get('tenant_schema'),
            generated_by=current_user.get('user_id')
        )
        
        return result
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@router.get("/", response_model=Dict[str, Any])
async def list_reports(
    transcript_id: Optional[int] = Query(None),
    report_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """
    List reports with optional filters.
    
    - **transcript_id**: Filter by transcript ID
    - **report_type**: Filter by report type (daily_standup, sprint_meeting, retrospective, brainstorming)
    - **status**: Filter by status (draft, published)
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    """
    try:
        # Validate report_type if provided
        if report_type and report_type not in ['daily_standup', 'sprint_meeting', 'retrospective', 'brainstorming']:
            raise HTTPException(status_code=400, detail="Invalid report_type")
        
        # Validate status if provided
        if status:
            try:
                ReportStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid status")
        
        service = ReportService(db)
        result = await service.list_reports(
            tenant_schema=current_user.get('tenant_schema'),
            transcript_id=transcript_id,
            report_type=report_type,
            status=status,
            page=page,
            page_size=page_size
        )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing reports: {e}")
        raise HTTPException(status_code=500, detail="Failed to list reports")


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: int,
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """Get a specific report by ID."""
    try:
        service = ReportService(db)
        result = await service.get_report(
            report_id=report_id,
            tenant_schema=current_user.get('tenant_schema')
        )
        
        return result
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching report: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch report")


@router.get("/transcript/{transcript_id}", response_model=List[ReportResponse])
async def get_reports_by_transcript(
    transcript_id: int,
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """Get all reports for a specific transcript."""
    try:
        service = ReportService(db)
        result = await service.get_reports_by_transcript(
            transcript_id=transcript_id,
            tenant_schema=current_user.get('tenant_schema')
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Error fetching reports by transcript: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch reports")


@router.put("/{report_id}", response_model=ReportResponse)
async def update_report_content(
    report_id: int,
    report_content: Dict[str, Any],
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """
    Update report content (for editing).
    
    Updates the report content and increments the version number.
    """
    try:
        service = ReportService(db)
        result = await service.update_report_content(
            report_id=report_id,
            report_content=report_content,
            tenant_schema=current_user.get('tenant_schema')
        )
        
        return result
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating report: {e}")
        raise HTTPException(status_code=500, detail="Failed to update report")


@router.patch("/{report_id}/status", response_model=ReportResponse)
async def update_report_status(
    report_id: int,
    status: str,
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """
    Update report status (draft or published).
    
    - **status**: New status ('draft' or 'published')
    """
    try:
        # Validate status
        try:
            status_enum = ReportStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status. Must be 'draft' or 'published'")
        
        service = ReportService(db)
        result = await service.update_report_status(
            report_id=report_id,
            status=status_enum,
            tenant_schema=current_user.get('tenant_schema')
        )
        
        return result
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating report status: {e}")
        raise HTTPException(status_code=500, detail="Failed to update report status")


@router.delete("/{report_id}")
async def delete_report(
    report_id: int,
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """Delete a report."""
    try:
        service = ReportService(db)
        await service.delete_report(
            report_id=report_id,
            tenant_schema=current_user.get('tenant_schema')
        )
        
        return JSONResponse(
            status_code=200,
            content={"message": "Report deleted successfully"}
        )
    
    except Exception as e:
        logger.error(f"Error deleting report: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete report")


@router.post("/{report_id}/export")
async def export_report_endpoint(
    report_id: int,
    export_request: ReportExportRequest,
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """
    Export a report to PDF or DOCX format.
    
    - **format**: Export format ('pdf' or 'docx')
    - **include_header**: Include template header
    - **include_footer**: Include template footer
    - **template_id**: Optional template ID for styling
    """
    try:
        # Get report
        service = ReportService(db)
        report = await service.get_report(
            report_id=report_id,
            tenant_schema=current_user.get('tenant_schema')
        )
        
        # Get template config if provided
        template_config = None
        if export_request.template_id or report.template_id:
            template_id = export_request.template_id or report.template_id
            
            # Fetch template from database
            query = f"""
                SELECT header_content, footer_content, styles
                FROM {current_user.get('tenant_schema')}.report_templates
                WHERE id = %s
            """
            template_result = await db.execute_query(query, (template_id,), fetch_one=True)
            
            if template_result:
                import json
                template_config = {
                    'header_content': json.loads(template_result['header_content']) if template_result.get('header_content') else None,
                    'footer_content': json.loads(template_result['footer_content']) if template_result.get('footer_content') else None,
                    'styles': json.loads(template_result['styles']) if template_result.get('styles') else None
                }
                
                # Remove header/footer if not requested
                if not export_request.include_header:
                    template_config['header_content'] = None
                if not export_request.include_footer:
                    template_config['footer_content'] = None
        
        # Export report
        exported_file = export_report(
            report_data=report.report_content,
            report_type=report.report_type,
            export_format=export_request.format,
            template_config=template_config
        )
        
        # Determine content type and filename
        if export_request.format == 'pdf':
            content_type = 'application/pdf'
            filename = f"report_{report_id}.pdf"
        else:
            content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            filename = f"report_{report_id}.docx"
        
        return Response(
            content=exported_file,
            media_type=content_type,
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error exporting report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to export report: {str(e)}")
