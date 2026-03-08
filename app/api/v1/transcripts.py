"""
Transcripts API Endpoints

Handles transcript upload, management, and retrieval.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from app.db.database import Database, get_db
from app.utils.jwt import get_current_user_from_token
from app.schemas.transcript import (
    TranscriptCreate, TranscriptUpdate, TranscriptResponse,
    TranscriptListResponse, TranscriptFilterParams, TranscriptCategory,
    ReportGeneratedStatus
)
from app.services.transcript_service import TranscriptService
from app.utils.document_parser import parse_document
from app.core.logger import logger
from typing import Optional, List
from datetime import date
import json

router = APIRouter()


@router.post("/upload", response_model=TranscriptResponse, status_code=201)
async def upload_transcript(
    file: Optional[UploadFile] = File(None),
    title: str = Form(...),
    category: str = Form(...),
    transcript_date: str = Form(...),
    project_id: Optional[int] = Form(None),
    tags: Optional[str] = Form(None),
    pasted_content: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """
    Upload a transcript from file or pasted content.
    
    - **file**: Optional file upload (.txt, .pdf, .docx)
    - **title**: Transcript title
    - **category**: DAILY_STANDUP, SPRINT_MEETING, or RETROSPECTIVE
    - **transcript_date**: Date of the meeting (YYYY-MM-DD)
    - **project_id**: Optional project ID (must be a project assigned to the user)
    - **tags**: Optional JSON array of tags
    - **pasted_content**: Optional pasted text content (used if no file)
    """
    try:
        # Parse transcript content
        transcript_content = None
        file_name = None
        
        if file:
            # Read file content
            file_content = await file.read()
            
            # Parse document
            try:
                transcript_content = parse_document(file_content, file.filename)
                file_name = file.filename
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        elif pasted_content:
            transcript_content = pasted_content
            file_name = None
        
        else:
            raise HTTPException(
                status_code=400,
                detail="Either file or pasted_content must be provided"
            )
        
        # Parse tags
        tags_list = None
        if tags:
            try:
                tags_list = json.loads(tags)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid tags format (must be JSON array)")
        
        # Parse date
        try:
            parsed_date = date.fromisoformat(transcript_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format (use YYYY-MM-DD)")
        
        # Validate category
        try:
            category_enum = TranscriptCategory(category)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category. Must be one of: {', '.join([c.value for c in TranscriptCategory])}"
            )
        
        service = TranscriptService(db)
        result = await service.create_transcript(
            tenant_name=current_user.get('tenant_name') or current_user.get('tenant_schema'),
            title=title,
            category=category_enum.value,
            transcript_content=transcript_content,
            transcript_date=parsed_date,
            tags=tags_list,
            file_name=file_name,
            uploaded_by=current_user.get('user_id'),
            project_id=project_id
        )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading transcript: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload transcript")


@router.get("/", response_model=TranscriptListResponse)
async def list_transcripts(
    category: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    report_generated: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """
    List transcripts with optional filters.
    
    - **category**: Filter by category (DAILY_STANDUP, SPRINT_MEETING, RETROSPECTIVE)
    - **date_from**: Filter by date from (YYYY-MM-DD)
    - **date_to**: Filter by date to (YYYY-MM-DD)
    - **search**: Search in title and content
    - **report_generated**: Filter by report status (pending, done)
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    """
    try:
        # Parse category
        category_enum = None
        if category:
            try:
                category_enum = TranscriptCategory(category)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid category")
        
        # Parse dates
        date_from_parsed = None
        date_to_parsed = None
        
        if date_from:
            try:
                date_from_parsed = date.fromisoformat(date_from)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_from format")
        
        if date_to:
            try:
                date_to_parsed = date.fromisoformat(date_to)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_to format")
        
        # Parse report_generated filter
        report_generated_enum = None
        if report_generated:
            try:
                report_generated_enum = ReportGeneratedStatus(report_generated)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid report_generated status. Use 'pending' or 'done'")
        
        # Create filter params
        filters = TranscriptFilterParams(
            category=category_enum,
            date_from=date_from_parsed,
            date_to=date_to_parsed,
            search=search,
            report_generated=report_generated_enum,
            page=page,
            page_size=page_size
        )
        
        service = TranscriptService(db)
        result = await service.list_transcripts(
            tenant_schema=current_user.get('tenant_name') or current_user.get('tenant_schema'),
            filters=filters
        )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing transcripts: {e}")
        raise HTTPException(status_code=500, detail="Failed to list transcripts")


@router.get("/{transcript_id}", response_model=TranscriptResponse)
async def get_transcript(
    transcript_id: int,
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """Get a specific transcript by ID."""
    try:
        service = TranscriptService(db)
        result = await service.get_transcript(
            transcript_id=transcript_id,
            tenant_schema=current_user.get('tenant_name') or current_user.get('tenant_schema')
        )
        
        if not result:
            raise ValueError("Transcript not found")
        
        return result
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching transcript: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch transcript")


@router.put("/{transcript_id}", response_model=TranscriptResponse)
async def update_transcript(
    transcript_id: int,
    transcript_data: TranscriptUpdate,
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """Update a transcript."""
    try:
        service = TranscriptService(db)
        result = await service.update_transcript(
            tenant_name=current_user.get('tenant_name') or current_user.get('tenant_schema'),
            transcript_id=transcript_id,
            title=transcript_data.title,
            category=transcript_data.category.value if transcript_data.category else None,
            transcript_content=transcript_data.transcript_content,
            transcript_date=transcript_data.transcript_date,
            tags=transcript_data.tags
        )
        
        if not result:
            raise ValueError("Transcript not found")
        
        return result
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating transcript: {e}")
        raise HTTPException(status_code=500, detail="Failed to update transcript")


@router.delete("/{transcript_id}")
async def delete_transcript(
    transcript_id: int,
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """Delete a transcript (also deletes associated reports)."""
    try:
        service = TranscriptService(db)
        await service.delete_transcript(
            tenant_name=current_user.get('tenant_name') or current_user.get('tenant_schema'),
            transcript_id=transcript_id
        )
        
        return JSONResponse(
            status_code=200,
            content={"message": "Transcript deleted successfully"}
        )
    
    except Exception as e:
        logger.error(f"Error deleting transcript: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete transcript")


@router.post("/{transcript_id}/analyze")
async def analyze_transcript(
    transcript_id: int,
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """
    Use AI to extract tasks and leave info from a transcript.
    """
    try:
        service = TranscriptService(db)
        tenant_schema = current_user.get('tenant_name') or current_user.get('tenant_schema')
        
        # Fetch the transcript content
        query = f"SELECT transcript_content FROM {tenant_schema}.transcripts WHERE id = %s"
        result = await db.execute_query(query, (transcript_id,), fetch_one=True, schema=tenant_schema)
        
        if not result or not result.get('transcript_content'):
            raise HTTPException(status_code=404, detail="Transcript not found")
        
        content = result['transcript_content']
        
        from app.services.ai_service import get_ai_service
        ai_service = get_ai_service()
        analysis = await ai_service.analyze_transcript(content)
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing transcript: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze transcript")
