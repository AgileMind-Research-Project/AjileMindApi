from typing import List, Dict, Any, Optional
from datetime import datetime, date
import json
from app.schemas.release_note_schemas import (
    CreateReleaseNoteRequest,
    UpdateReleaseNoteRequest,
    GenerateReleaseNoteRequest,
    ReleaseStatus
)
from app.db.database import Database
from app.core.logger import logger

class ReleaseNoteService:
    def __init__(self, db: Database):
        self.db = db
        from app.db.repositories.backlog_repository import BacklogRepository
        self.backlog_repo = BacklogRepository(db)

    async def get_backlog_releases(
        self,
        tenant_name: str,
        project_id: int
    ) -> List[Dict[str, Any]]:
        """Get releases tracked in the backlog for a specific project"""
        return await self.backlog_repo.list_backlog_by_type(tenant_name, project_id, 'release')

    async def get_all_backlog_releases(
        self,
        tenant_name: str
    ) -> List[Dict[str, Any]]:
        """Get all release-type backlog items across all projects"""
        return await self.backlog_repo.list_all_by_type(tenant_name, 'release')

    async def create_release_note(
        self,
        tenant_name: str,
        request: CreateReleaseNoteRequest,
        user_id: str
    ) -> Dict[str, Any]:
        """Create a new release note"""
        try:
            # Convert content to JSON string
            content_json = json.dumps(request.content.dict())
            
            insert_query = f"""
                INSERT INTO `{tenant_name}`.release_notes
                (project_id, version, title, release_date, release_type, start_sprint, end_sprint, content, summary, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            params = (
                request.project_id,
                request.version,
                request.title,
                request.release_date,
                request.release_type.value,
                request.start_sprint,
                request.end_sprint,
                content_json,
                request.summary,
                user_id
            )
            
            result = await self.db.execute_query(insert_query, params, commit=True)
            release_note_id = result.lastrowid
            
            logger.info(f"Created release note ID: {release_note_id} for project {request.project_id}")
            
            return {
                "id": release_note_id,
                "success": True,
                "message": f"Release note v{request.version} created successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to create release note: {e}")
            raise

    async def get_release_notes(
        self,
        tenant_name: str,
        project_id: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """List release notes with optional filters"""
        try:
            offset = (page - 1) * page_size
            
            # Build WHERE clause
            where_clauses = []
            params_list = []
            
            if project_id:
                where_clauses.append("project_id = %s")
                params_list.append(project_id)
            
            if status:
                where_clauses.append("status = %s")
                params_list.append(status)
            
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            
            # Count total
            count_query = f"SELECT COUNT(*) as total FROM `{tenant_name}`.release_notes {where_sql}"
            count_result = await self.db.execute_query(count_query, tuple(params_list), fetch_one=True)
            total = count_result['total'] if count_result else 0
            
            # Fetch records
            query = f"""
                SELECT id, project_id, version, title, release_date, release_type,
                       start_sprint, end_sprint,
                       content, summary, status, created_by, created_at, updated_at,
                       published_at, published_by
                FROM `{tenant_name}`.release_notes
                {where_sql}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            
            params_list.extend([page_size, offset])
            rows = await self.db.execute_query(query, tuple(params_list), fetch_all=True) or []
            
            # Parse JSON content for each row
            for row in rows:
                if row.get('content'):
                    try:
                        row['content'] = json.loads(row['content']) if isinstance(row['content'], str) else row['content']
                    except:
                        row['content'] = {}
            
            return {
                "items": rows,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }
            
        except Exception as e:
            logger.error(f"Error listing release notes: {e}")
            raise

    async def get_release_note_by_id(
        self,
        tenant_name: str,
        release_note_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get a single release note by ID"""
        try:
            query = f"""
                SELECT id, project_id, version, title, release_date, release_type,
                       start_sprint, end_sprint,
                       content, summary, status, created_by, created_at, updated_at,
                       published_at, published_by
                FROM `{tenant_name}`.release_notes
                WHERE id = %s
            """
            
            row = await self.db.execute_query(query, (release_note_id,), fetch_one=True)
            
            if row and row.get('content'):
                try:
                    row['content'] = json.loads(row['content']) if isinstance(row['content'], str) else row['content']
                except:
                    row['content'] = {}
            
            return row
            
        except Exception as e:
            logger.error(f"Error fetching release note {release_note_id}: {e}")
            raise

    async def update_release_note(
        self,
        tenant_name: str,
        release_note_id: int,
        request: UpdateReleaseNoteRequest
    ) -> Dict[str, Any]:
        """Update an existing release note"""
        try:
            # Build update fields dynamically
            update_fields = []
            params = []
            
            if request.version is not None:
                update_fields.append("version = %s")
                params.append(request.version)
            
            if request.title is not None:
                update_fields.append("title = %s")
                params.append(request.title)
            
            if request.release_date is not None:
                update_fields.append("release_date = %s")
                params.append(request.release_date)
            
            if request.release_type is not None:
                update_fields.append("release_type = %s")
                params.append(request.release_type.value)
            
            if request.start_sprint is not None:
                update_fields.append("start_sprint = %s")
                params.append(request.start_sprint)
                
            if request.end_sprint is not None:
                update_fields.append("end_sprint = %s")
                params.append(request.end_sprint)
            
            if request.content is not None:
                update_fields.append("content = %s")
                params.append(json.dumps(request.content.dict()))
            
            if request.summary is not None:
                update_fields.append("summary = %s")
                params.append(request.summary)
            
            if not update_fields:
                return {"success": True, "message": "No fields to update"}
            
            params.append(release_note_id)
            
            update_query = f"""
                UPDATE `{tenant_name}`.release_notes
                SET {', '.join(update_fields)}
                WHERE id = %s
            """
            
            await self.db.execute_query(update_query, tuple(params), commit=True)
            
            logger.info(f"Updated release note ID: {release_note_id}")
            
            return {
                "success": True,
                "message": "Release note updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to update release note {release_note_id}: {e}")
            raise

    async def delete_release_note(
        self,
        tenant_name: str,
        release_note_id: int
    ) -> Dict[str, Any]:
        """Delete a release note"""
        try:
            delete_query = f"""
                DELETE FROM `{tenant_name}`.release_notes
                WHERE id = %s
            """
            
            await self.db.execute_query(delete_query, (release_note_id,), commit=True)
            
            logger.info(f"Deleted release note ID: {release_note_id}")
            
            return {
                "success": True,
                "message": "Release note deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to delete release note {release_note_id}: {e}")
            raise

    async def publish_release_note(
        self,
        tenant_name: str,
        release_note_id: int,
        user_id: str
    ) -> Dict[str, Any]:
        """Publish a draft release note"""
        try:
            update_query = f"""
                UPDATE `{tenant_name}`.release_notes
                SET status = %s, published_at = NOW(), published_by = %s
                WHERE id = %s AND status = %s
            """
            
            result = await self.db.execute_query(
                update_query,
                (ReleaseStatus.PUBLISHED.value, user_id, release_note_id, ReleaseStatus.DRAFT.value),
                commit=True
            )
            
            if result.rowcount == 0:
                return {
                    "success": False,
                    "message": "Release note not found or already published"
                }
            
            logger.info(f"Published release note ID: {release_note_id}")
            
            return {
                "success": True,
                "message": "Release note published successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to publish release note {release_note_id}: {e}")
            raise

    async def generate_release_note_ai(
        self,
        tenant_name: str,
        request: GenerateReleaseNoteRequest
    ) -> Dict[str, Any]:
        """Generate release note content using AI based on project data"""
        try:
            # This is a placeholder - you'll need to integrate with your AI service
            # For now, we'll return a template structure
            
            logger.info(f"Generating AI release note for project {request.project_id}, version {request.version}")
            
            # TODO: Query project tasks, sprints, backlog items
            # TODO: Call AI service to analyze and generate content
            
            # Placeholder response
            generated_content = {
                "features": [
                    "New user authentication system",
                    "Enhanced dashboard with real-time analytics",
                    "Mobile responsive design improvements"
                ],
                "bug_fixes": [
                    "Fixed login timeout issue",
                    "Resolved data sync errors",
                    "Corrected timezone display issues"
                ],
                "improvements": [
                    "40% faster page load times",
                    "Improved error handling and user feedback",
                    "Enhanced accessibility features"
                ],
                "breaking_changes": [],
                "known_issues": []
            }
            
            summary = f"This release includes major improvements to the user interface and performance optimizations."
            
            return {
                "success": True,
                "content": generated_content,
                "summary": summary,
                "message": "Release note content generated successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to generate AI release note: {e}")
            raise
