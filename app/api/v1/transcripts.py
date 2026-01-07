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
    TranscriptListResponse, TranscriptFilterParams, TranscriptCategory
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
        
        # Create transcript
        transcript_data = TranscriptCreate(
            title=title,
            category=category_enum,
            transcript_content=transcript_content,
            transcript_date=parsed_date,
            tags=tags_list,
            file_name=file_name
        )
        
        service = TranscriptService(db)
        result = await service.create_transcript(
            transcript_data=transcript_data,
            tenant_schema=current_user.get('tenant_schema'),
            uploaded_by=current_user.get('user_id')
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
        
        # Create filter params
        filters = TranscriptFilterParams(
            category=category_enum,
            date_from=date_from_parsed,
            date_to=date_to_parsed,
            search=search,
            page=page,
            page_size=page_size
        )
        
        service = TranscriptService(db)
        result = await service.list_transcripts(
            tenant_schema=current_user.get('tenant_schema'),
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
            tenant_schema=current_user.get('tenant_schema')
        )
        
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
            transcript_id=transcript_id,
            transcript_data=transcript_data,
            tenant_schema=current_user.get('tenant_schema')
        )
        
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
            transcript_id=transcript_id,
            tenant_schema=current_user.get('tenant_schema')
        )
        
        return JSONResponse(
            status_code=200,
            content={"message": "Transcript deleted successfully"}
        )
    
    except Exception as e:
        logger.error(f"Error deleting transcript: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete transcript")
