"""
Template Schemas

Pydantic models for report templates.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Any, Optional, List
from app.schemas.report import ReportType


class TemplateSection(BaseModel):
    """Template section structure"""
    title: str
    type: str = Field(..., pattern="^(paragraph|bullet_list|numbered_list|table|heading)$")
    content: Optional[str] = None
    order: int = 0


class TemplateHeaderFooter(BaseModel):
    """Template header/footer structure"""
    text: Optional[str] = None
    image_url: Optional[str] = None
    alignment: str = Field(default="center", pattern="^(left|center|right)$")
    font_size: int = Field(default=12, ge=8, le=72)
    font_family: str = "Arial"
    color: str = "#000000"


class TemplateStyles(BaseModel):
    """Template styling options"""
    font_family: str = "Arial"
    font_size: int = Field(default=12, ge=8, le=72)
    line_height: float = Field(default=1.5, ge=1.0, le=3.0)
    margins: Dict[str, int] = Field(default={"top": 72, "bottom": 72, "left": 72, "right": 72})
    heading_color: str = "#000000"
    text_color: str = "#333333"


class TemplateCreate(BaseModel):
    """Schema for creating a template"""
    template_name: str = Field(..., min_length=1, max_length=255)
    report_type: ReportType
    header_content: Optional[TemplateHeaderFooter] = None
    footer_content: Optional[TemplateHeaderFooter] = None
    sections: List[TemplateSection]
    styles: Optional[TemplateStyles] = None
    is_default: bool = False


class TemplateUpdate(BaseModel):
    """Schema for updating a template"""
    template_name: Optional[str] = Field(None, min_length=1, max_length=255)
    header_content: Optional[TemplateHeaderFooter] = None
    footer_content: Optional[TemplateHeaderFooter] = None
    sections: Optional[List[TemplateSection]] = None
    styles: Optional[TemplateStyles] = None
    is_default: Optional[bool] = None


class TemplateResponse(BaseModel):
    """Schema for template response"""
    id: int
    template_name: str
    report_type: ReportType
    header_content: Optional[Dict[str, Any]] = None
    footer_content: Optional[Dict[str, Any]] = None
    sections: List[Dict[str, Any]]
    styles: Optional[Dict[str, Any]] = None
    is_default: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TemplateListItem(BaseModel):
    """Schema for template list item"""
    id: int
    template_name: str
    report_type: ReportType
    is_default: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TemplateListResponse(BaseModel):
    """Schema for template list response"""
    templates: List[TemplateListItem]
    total: int
