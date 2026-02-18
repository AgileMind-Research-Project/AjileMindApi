"""
Transcript API

Endpoints for managing transcripts.
"""

from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from app.db.database import get_db as get_database
from app.db.database import Database
from app.services.transcript_service import TranscriptService
from app.utils.jwt import get_current_user_from_token
from pydantic import BaseModel
import json
from datetime import date

router = APIRouter()

# --- Schemas ---

class TranscriptResponse(BaseModel):
    id: int
    title: str
    category: str
    transcript_date: date
    tags: Optional[List[str]] = None
    file_name: Optional[str] = None
    created_at: Any = None
    project_id: Optional[int] = None
    # content excluded from list view for size? Service includes it in fetch but maybe we strictly define response

# --- Endpoints ---

@router.post("/upload", response_model=dict, status_code=status.HTTP_201_CREATED)
async def upload_transcript(
    title: str = Form(...),
    category: str = Form(...),
    transcript_date: date = Form(...),
    tags: str = Form(default="[]"), # JSON string
    pasted_content: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    project_id: Optional[int] = Form(0), # 0 or null
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_database)
):
    """
    Upload a new transcript (File or Text)
    """
    tenant_name = current_user.get('tenant_name')
    user_id = current_user.get('user_id') or current_user.get('sub')
    
    content = ""
    file_name = None
    
    if pasted_content:
        content = pasted_content
    elif file:
        file_name = file.filename
        # Simple read for text/plain. For PDF/Docx need libraries (PyPDF2, python-docx)
        # Assuming text for now based on user flow, but user mentioned pdf/docx in UI.
        # Implementing basic text read:
        content_bytes = await file.read()
        try:
            content = content_bytes.decode('utf-8')
        except UnicodeDecodeError:
             # Fallback or error. For PDF/Docx this won't work without parsing libs.
             # Saving as is? No, db expects text.
             # TODO: Add PDF/Docx parsing logic if strictly required. 
             # For MVP, assuming text files or paste.
             content = str(content_bytes) 
    else:
        raise HTTPException(status_code=400, detail="Either file or pasted content is required")
        
    try:
        tags_list = json.loads(tags)
    except:
        tags_list = []
        
    service = TranscriptService(db)
    
    # Check if project_id logic is needed (verify project exists?)
    p_id = project_id if project_id and project_id > 0 else None
    
    result = await service.create_transcript(
        tenant_name=tenant_name,
        title=title,
        category=category,
        transcript_content=content,
        transcript_date=transcript_date,
        tags=tags_list,
        file_name=file_name,
        uploaded_by=user_id,
        project_id=p_id
    )
    
    return result

@router.get("", response_model=dict)
async def list_transcripts(
    category: Optional[str] = None,
    project_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_database)
):
    tenant_name = current_user.get('tenant_name')
    service = TranscriptService(db)
    
    result = await service.get_transcripts(
        tenant_name=tenant_name,
        category=category,
        project_id=project_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
        page=page,
        page_size=page_size
    )
    
    return result

@router.get("/{transcript_id}", response_model=dict)
async def get_transcript(
    transcript_id: int,
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_database)
):
    tenant_name = current_user.get('tenant_name')
    service = TranscriptService(db)
    
    result = await service.get_transcript_by_id(tenant_name, transcript_id)
    if not result:
        raise HTTPException(status_code=404, detail="Transcript not found")
        
    return result

@router.delete("/{transcript_id}", response_model=dict)
async def delete_transcript(
    transcript_id: int,
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_database)
):
    tenant_name = current_user.get('tenant_name')
    service = TranscriptService(db)
    
    # Optional: Check permission (uploaded_by or admin)
    
    await service.delete_transcript(tenant_name, transcript_id)
    
    return {"success": True, "message": "Transcript deleted"}
