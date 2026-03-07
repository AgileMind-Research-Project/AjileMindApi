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

@router.get("/daily-standups", response_model=TranscriptListResponse)
async def list_daily_standups(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """
    List daily standup transcripts specifically.
    """
    try:
        filters = TranscriptFilterParams(
            category=TranscriptCategory.DAILY_STANDUP,
            date_from=date.fromisoformat(date_from) if date_from else None,
            date_to=date.fromisoformat(date_to) if date_to else None,
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
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing daily standups: {e}")
        raise HTTPException(status_code=500, detail="Failed to list daily standups")

@router.post("/upload", response_model=TranscriptResponse, status_code=201)
async def upload_transcript(
    file: Optional[UploadFile] = File(None),
    title: str = Form(...),
    category: str = Form(...),
    transcript_date: str = Form(...),
    tags: Optional[str] = Form(None),
    pasted_content: Optional[str] = Form(None),
    project_id: Optional[int] = Form(None),
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """
    Upload a transcript for AI processing.
    """
    try:
        transcript_content = None
        file_name = None
        
        if file:
            file_content = await file.read()
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
        
        tags_list = None
        if tags:
            try:
                tags_list = json.loads(tags)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid tags format (must be JSON array)")
        
        try:
            parsed_date = date.fromisoformat(transcript_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format (use YYYY-MM-DD)")
        
        try:
            category_enum = TranscriptCategory(category)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category. Must be one of: {', '.join([c.value for c in TranscriptCategory])}"
            )
        
        transcript_data = TranscriptCreate(
            title=title,
            category=category_enum,
            transcript_content=transcript_content,
            transcript_date=parsed_date,
            tags=tags_list,
            file_name=file_name,
            project_id=project_id
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
    try:
        category_enum = None
        if category:
            category_enum = TranscriptCategory(category)
            
        filters = TranscriptFilterParams(
            category=category_enum,
            date_from=date.fromisoformat(date_from) if date_from else None,
            date_to=date.fromisoformat(date_to) if date_to else None,
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
    except Exception as e:
        logger.error(f"Error describing transcripts: {e}")
        raise HTTPException(status_code=500, detail="Failed to list transcripts")

@router.get("/{transcript_id}", response_model=TranscriptResponse)
async def get_transcript(
    transcript_id: int,
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    try:
        service = TranscriptService(db)
        return await service.get_transcript(
            transcript_id=transcript_id,
            tenant_schema=current_user.get('tenant_schema')
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting transcript: {e}")
        raise HTTPException(status_code=500, detail="Failed to get transcript")

@router.put("/{transcript_id}", response_model=TranscriptResponse)
async def update_transcript(
    transcript_id: int,
    transcript_data: TranscriptUpdate,
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    try:
        service = TranscriptService(db)
        return await service.update_transcript(
            transcript_id=transcript_id,
            transcript_data=transcript_data,
            tenant_schema=current_user.get('tenant_schema')
        )
    except Exception as e:
        logger.error(f"Error updating transcript: {e}")
        raise HTTPException(status_code=500, detail="Failed to update transcript")

@router.delete("/{transcript_id}")
async def delete_transcript(
    transcript_id: int,
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    try:
        service = TranscriptService(db)
        await service.delete_transcript(
            transcript_id=transcript_id,
            tenant_schema=current_user.get('tenant_schema')
        )
        return JSONResponse(status_code=200, content={"message": "Deleted successfully"})
    except Exception as e:
        logger.error(f"Error deleting transcript: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete transcript")
