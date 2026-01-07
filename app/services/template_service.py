"""
Report Template Service
Handles CRUD operations for report templates
"""
import json
from typing import List, Dict, Any, Optional
from app.db.database import Database
from app.schemas.template import (
    TemplateCreate,
    TemplateUpdate,
    TemplateResponse
)
import logging

logger = logging.getLogger("agile_mind")


class TemplateService:
    """Service for managing report templates"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def create_template(
        self,
        template_data: TemplateCreate,
        tenant_schema: str,
        created_by: Optional[int] = None
    ) -> TemplateResponse:
        """Create a new report template"""
        try:
            # Convert Pydantic models to JSON strings
            header_json = json.dumps(template_data.header_content) if template_data.header_content else None
            footer_json = json.dumps(template_data.footer_content) if template_data.footer_content else None
            sections_json = json.dumps(template_data.sections)
            styles_json = json.dumps(template_data.styles) if template_data.styles else None
            
            query = f"""
                INSERT INTO {tenant_schema}.report_templates 
                (template_name, report_type, header_content, footer_content, 
                 sections, styles, is_default, created_by, tenant_schema)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            params = (
                template_data.template_name,
                template_data.report_type,
                header_json,
                footer_json,
                sections_json,
                styles_json,
                template_data.is_default,
                created_by,
                tenant_schema
            )
            
            result = await self.db.execute_query(query, params, fetch_one=False)
            template_id = result
            
            logger.info(f"Created template {template_id} in schema {tenant_schema}")
            
            # Fetch and return the created template
            return await self.get_template(template_id, tenant_schema)
        
        except Exception as e:
            logger.error(f"Error creating template: {e}")
            raise
    
    async def get_template(
        self,
        template_id: int,
        tenant_schema: str
    ) -> TemplateResponse:
        """Get a template by ID"""
        try:
            query = f"""
                SELECT id, template_name, report_type, header_content, 
                       footer_content, sections, styles, is_default, 
                       created_by, tenant_schema, created_at, updated_at
                FROM {tenant_schema}.report_templates
                WHERE id = %s
            """
            
            result = await self.db.execute_query(query, (template_id,), fetch_one=True)
            
            if not result:
                raise ValueError(f"Template with ID {template_id} not found")
            
            # Parse JSON fields
            # Parse JSON fields and handle format
            sections_raw = json.loads(result['sections'])
            sections_list = sections_raw['sections'] if isinstance(sections_raw, dict) and 'sections' in sections_raw else sections_raw

            return TemplateResponse(
                id=result['id'],
                template_name=result['template_name'],
                report_type=result['report_type'],
                header_content=json.loads(result['header_content']) if result.get('header_content') else None,
                footer_content=json.loads(result['footer_content']) if result.get('footer_content') else None,
                sections=sections_list,
                styles=json.loads(result['styles']) if result.get('styles') else None,
                is_default=result['is_default'],
                created_by=result.get('created_by'),
                tenant_schema=result['tenant_schema'],
                created_at=result['created_at'],
                updated_at=result['updated_at']
            )
        
        except Exception as e:
            logger.error(f"Error fetching template: {e}")
            raise
    
    async def list_templates(
        self,
        tenant_schema: str,
        report_type: Optional[str] = None,
        is_default: Optional[bool] = None
    ) -> List[TemplateResponse]:
        """List all templates with optional filters"""
        try:
            query = f"""
                SELECT id, template_name, report_type, header_content, 
                       footer_content, sections, styles, is_default, 
                       created_by, tenant_schema, created_at, updated_at
                FROM {tenant_schema}.report_templates
                WHERE 1=1
            """
            params = []
            
            if report_type:
                query += " AND report_type = %s"
                params.append(report_type)
            
            if is_default is not None:
                query += " AND is_default = %s"
                params.append(is_default)
            
            query += " ORDER BY is_default DESC, created_at DESC"
            
            results = await self.db.execute_query(query, tuple(params), fetch_all=True)
            
            templates = []
            for row in results or []:
                # Handle potentially wrapped sections
                sections_raw = json.loads(row['sections'])
                sections_list = sections_raw['sections'] if isinstance(sections_raw, dict) and 'sections' in sections_raw else sections_raw

                templates.append(TemplateResponse(
                    id=row['id'],
                    template_name=row['template_name'],
                    report_type=row['report_type'],
                    header_content=json.loads(row['header_content']) if row.get('header_content') else None,
                    footer_content=json.loads(row['footer_content']) if row.get('footer_content') else None,
                    sections=sections_list,
                    styles=json.loads(row['styles']) if row.get('styles') else None,
                    is_default=row['is_default'],
                    created_by=row.get('created_by'),
                    tenant_schema=row['tenant_schema'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                ))
            
            return templates
        
        except Exception as e:
            logger.error(f"Error listing templates: {e}")
            raise
    
    async def update_template(
        self,
        template_id: int,
        template_data: TemplateUpdate,
        tenant_schema: str
    ) -> TemplateResponse:
        """Update a template"""
        try:
            # Build dynamic update query
            update_fields = []
            params = []
            
            if template_data.template_name is not None:
                update_fields.append("template_name = %s")
                params.append(template_data.template_name)
            
            if template_data.report_type is not None:
                update_fields.append("report_type = %s")
                params.append(template_data.report_type)
            
            if template_data.header_content is not None:
                update_fields.append("header_content = %s")
                params.append(json.dumps(template_data.header_content))
            
            if template_data.footer_content is not None:
                update_fields.append("footer_content = %s")
                params.append(json.dumps(template_data.footer_content))
            
            if template_data.sections is not None:
                update_fields.append("sections = %s")
                params.append(json.dumps(template_data.sections))
            
            if template_data.styles is not None:
                update_fields.append("styles = %s")
                params.append(json.dumps(template_data.styles))
            
            if template_data.is_default is not None:
                update_fields.append("is_default = %s")
                params.append(template_data.is_default)
            
            if not update_fields:
                raise ValueError("No fields to update")
            
            params.append(template_id)
            
            query = f"""
                UPDATE {tenant_schema}.report_templates
                SET {', '.join(update_fields)}
                WHERE id = %s
            """
            
            await self.db.execute_query(query, tuple(params), fetch_one=False)
            
            logger.info(f"Updated template {template_id} in schema {tenant_schema}")
            
            # Fetch and return the updated template
            return await self.get_template(template_id, tenant_schema)
        
        except Exception as e:
            logger.error(f"Error updating template: {e}")
            raise
    
    async def delete_template(
        self,
        template_id: int,
        tenant_schema: str
    ) -> None:
        """Delete a template"""
        try:
            # Check if template exists
            await self.get_template(template_id, tenant_schema)
            
            query = f"""
                DELETE FROM {tenant_schema}.report_templates
                WHERE id = %s
            """
            
            await self.db.execute_query(query, (template_id,), fetch_one=False)
            
            logger.info(f"Deleted template {template_id} from schema {tenant_schema}")
        
        except Exception as e:
            logger.error(f"Error deleting template: {e}")
            raise
