"""
Backlog Service

Business logic for backlog management including file processing and Jira integration.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import io
import json
from fastapi import UploadFile, HTTPException, status
from app.db.repositories.backlog_repository import BacklogRepository
from app.db.repositories.project_repository import ProjectRepository
from app.services.jira_backlog_service import JiraBacklogService
from app.services.jira_service import JiraService
from app.schemas.backlog_schemas import (
    BacklogItemCreate,
    BacklogItemFromFile,
    BacklogItemResponse,
    BulkUploadResponse,
    SubtaskCreateRequest
)
from app.db.database import Database
from app.core.logger import logger


class BacklogService:
    """Service for backlog operations"""
    
    def __init__(self, db: Database):
        self.db = db
        self.backlog_repo = BacklogRepository(db)
        self.project_repo = ProjectRepository(db)
    
    async def parse_excel_file(
        self,
        file: UploadFile
    ) -> List[BacklogItemFromFile]:
        """
        Parse Excel or CSV file to extract backlog items.
        
        Args:
            file: Uploaded Excel/CSV file
        
        Returns:
            List of backlog items
        """
        try:
            # Read file content
            contents = await file.read()
            
            # Determine file type and parse
            if file.filename.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(contents))
            elif file.filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(io.BytesIO(contents))
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File must be Excel (.xlsx, .xls) or CSV (.csv)"
                )
            
            # Validate required columns
            required_columns = ['summary', 'issue_type']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required columns: {', '.join(missing_columns)}"
                )
            
            # Parse rows into BacklogItemFromFile objects
            items = []
            for index, row in df.iterrows():
                try:
                    item = BacklogItemFromFile(
                        summary=str(row['summary']),
                        description=str(row.get('description', '')) if pd.notna(row.get('description')) else None,
                        issue_type=str(row['issue_type']).strip().lower(),
                        priority=str(row.get('priority', '')).strip().lower() if pd.notna(row.get('priority')) else None,
                        assignee=str(row.get('assignee', '')) if pd.notna(row.get('assignee')) else None,
                        tags=str(row.get('tags', '')) if pd.notna(row.get('tags')) else None,
                        severity=str(row.get('severity', '')) if pd.notna(row.get('severity')) else None,
                        sprint_id=int(row['sprint_id']) if pd.notna(row.get('sprint_id')) else None
                    )
                    items.append(item)
                except Exception as e:
                    logger.warning(f"Skipping row {index + 2}: {str(e)}")
                    continue
            
            logger.info(f"Parsed {len(items)} items from file {file.filename}")
            return items
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error parsing file: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error parsing file: {str(e)}"
            )
    
    async def create_backlog_from_file(
        self,
        tenant_name: str,
        project_id: int,
        project_key: str,
        file: UploadFile,
        jira_url: str,
        jira_email: str,
        jira_api_token: str
    ) -> BulkUploadResponse:
        """
        Process uploaded file, create items in Jira, and store in database.
        
        Args:
            tenant_name: Tenant database name
            project_id: Project ID
            project_key: Jira project key
            file: Uploaded file
            jira_url: Jira instance URL
            jira_email: Jira email
            jira_api_token: Jira API token
        
        Returns:
            Bulk upload response with results
        """
        try:
            # Parse file
            file_items = await self.parse_excel_file(file)
            
            if not file_items:
                return BulkUploadResponse(
                    success=False,
                    message="No valid items found in file",
                    items_processed=0,
                    items_created=0,
                    errors=["File contains no valid backlog items"]
                )
            
            # Convert to BacklogItemCreate objects
            backlog_items = []
            validation_errors = []
            
            for idx, item in enumerate(file_items):
                try:
                    backlog_item = item.to_create_request(project_id)
                    backlog_items.append(backlog_item)
                except Exception as e:
                    validation_errors.append(f"Row {idx + 2}: {str(e)}")
            
            if not backlog_items:
                return BulkUploadResponse(
                    success=False,
                    message="No valid items after validation",
                    items_processed=len(file_items),
                    items_created=0,
                    errors=validation_errors
                )
            
            # Create Jira service
            jira_service = JiraBacklogService(jira_url, jira_email, jira_api_token)
            
            # Create issues in Jira
            jira_result = jira_service.bulk_create_issues(project_key, backlog_items)
            
            # Store successfully created items in database
            jira_issues_created = []
            db_errors = []
            
            for jira_issue in jira_result["created"]:
                issue_key = jira_issue["issue_key"]
                
                # Find corresponding backlog item
                backlog_item = next(
                    (item for item in backlog_items if item.summary == jira_issue["summary"]),
                    None
                )
                
                if not backlog_item:
                    continue
                
                try:
                    await self.backlog_repo.create_backlog_item(
                        tenant_name=tenant_name,
                        item_id=issue_key,
                        project_id=project_id,
                        summary=backlog_item.summary,
                        description=backlog_item.description,
                        issue_type=backlog_item.issue_type.value,
                        status="todo",  # Default status for new items
                        priority=backlog_item.priority.value if backlog_item.priority else None,
                        assignee=backlog_item.assignee,
                        tags=backlog_item.tags,
                        severity=backlog_item.severity,
                        sprint_id=backlog_item.sprint_id
                    )
                    jira_issues_created.append(issue_key)
                except Exception as e:
                    db_errors.append(f"Failed to store {issue_key}: {str(e)}")
            
            # Combine all errors
            all_errors = validation_errors + jira_result["errors"] + db_errors
            
            return BulkUploadResponse(
                success=len(jira_issues_created) > 0,
                message=f"Created {len(jira_issues_created)} backlog items",
                items_processed=len(file_items),
                items_created=len(jira_issues_created),
                jira_issues_created=jira_issues_created,
                errors=all_errors if all_errors else None
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in create_backlog_from_file: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process file: {str(e)}"
            )
    
    async def list_backlog(
        self,
        tenant_name: str,
        project_id: int
    ) -> List[BacklogItemResponse]:
        """List all backlog items for a project"""
        try:
            items = await self.backlog_repo.list_backlog_by_project(tenant_name, project_id)
            return [BacklogItemResponse(**item) for item in items]
        except Exception as e:
            logger.error(f"Error listing backlog: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list backlog items: {str(e)}"
            )

    async def list_sprint_backlog(
        self,
        tenant_name: str,
        sprint_id: int
    ) -> List[BacklogItemResponse]:
        """List all backlog items for a sprint"""
        try:
            items = await self.backlog_repo.list_backlog_by_sprint(tenant_name, sprint_id)
            return [BacklogItemResponse(**item) for item in items]
        except Exception as e:
            logger.error(f"Error listing sprint backlog: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list sprint backlog items: {str(e)}"
            )

    async def create_subtask(
        self,
        tenant_name: str,
        request: SubtaskCreateRequest
    ) -> BacklogItemResponse:
        """Create a new subtask with sequential ID logic"""
        try:
            parent_id = request.parent_item_id
            
            # 1. Get parent task (verify existence and get subtasks)
            parent_data = await self.backlog_repo.get_task_with_subtasks(tenant_name, parent_id)
            if not parent_data or not parent_data.get('parent'):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Parent item {parent_id} not found"
                )
            
            project_id = parent_data['parent']['project_id']
            
            # 2. Generate new ID
            subtasks = parent_data.get('subtasks', [])
            max_suffix = 0
            
            for sub in subtasks:
                try:
                    # Parse ID dynamically (splits by '-')
                    parts = sub['id'].split('-')
                    if parts and parts[-1].isdigit():
                        suffix = int(parts[-1])
                        if suffix > max_suffix:
                            max_suffix = suffix
                except Exception:
                    pass
            
            new_suffix = max_suffix + 1
            new_item_id = f"{parent_id}-SUB-{new_suffix}"
            
            # 3. Create Subtask 

            await self.backlog_repo.create_backlog_item(
                tenant_name=tenant_name,
                item_id=new_item_id,
                project_id=project_id, # Inherit project
                summary=request.summary,
                description=request.description,
                issue_type='sub_task', # Force issue type
                priority=request.priority.value if request.priority else None,
                assignee=request.assignee,
                tags=request.tags,
                severity=request.severity,
                status='todo',
                parent_task_id=parent_id
            )
            
            
            # Fetch and return created item
            created_item = await self.backlog_repo.get_backlog_item(tenant_name, new_item_id)
            return BacklogItemResponse(**created_item)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating subtask: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create subtask: {str(e)}"
            )

    async def sync_priority_items_to_jira(
        self,
        tenant_name: str,
        project_id: int,
        project_key: str,
        jira_service: JiraService
    ) -> Dict[str, Any]:
        """
        Sync prioritized items to Jira (create and link).
        
        Process:
        1. Fetch all prioritized items (parents).
        2. Create them in Jira if not already consistent.
        3. Rename local items to match Jira keys.
        4. Fetch and sync subtasks for these items.
        """
        try:
            # 1. Fetch prioritized parents
            query = """
                SELECT 
                    pb.id, pb.summary, pb.description, pb.issue_type,
                    pb.priority, pb.assignee, pb.tags, pb.is_jira,
                    pbp.rank
                FROM project_backlog_priority pbp
                JOIN project_backlog pb ON pbp.backlog_id = pb.id
                WHERE pbp.project_id = %s
            """
            
            parents_query = """
                SELECT
                    id, summary, description, issue_type, priority, assignee, tags, is_jira
                FROM project_backlog
                WHERE project_id = %s
                AND priority IS NOT NULL
            """
            
            parents = await self.db.execute_query(
                parents_query,
                (project_id,),
                fetch_all=True,
                schema=tenant_name
            )
            
            created_parents = []
            synced_count = 0
            
            if parents:
                for parent in parents:
                    parent_id = parent['id']
                    
                    try:
                        priority_name = parent.get('priority').capitalize() if parent.get('priority') else None
                        
                        if parent.get('is_jira'):
                            # UPDATE existing Jira issue
                            await jira_service.update_issue(
                                tenant_name=tenant_name,
                                issue_key=parent_id, # ID is already Jira key
                                priority=priority_name,
                                assignee_email=parent.get('assignee')
                            )
                            created_parents.append(parent_id) 
                            synced_count += 1
                            
                        else:
                            # CREATE new Jira issue
                            jira_issue = await jira_service.create_issue(
                                tenant_name=tenant_name,
                                project_key=project_key,
                                summary=parent['summary'],
                                description=parent.get('description'),
                                issue_type=parent['issue_type'] or 'Task',
                                priority=priority_name,
                                assignee_email=parent.get('assignee'),
                                labels=json.loads(parent['tags']) if parent.get('tags') else None
                            )
                            
                            new_jira_key = jira_issue['issue_key']
                            
                            # Rename local item
                            if parent_id != new_jira_key:
                                await self.backlog_repo.rename_backlog_item(tenant_name, parent_id, new_jira_key)
                                # Mark as is_jira
                                await self.backlog_repo.update_task_jira_info(tenant_name, new_jira_key, new_jira_key)
                                
                            created_parents.append(new_jira_key)
                            synced_count += 1
                            
                    except Exception as e:
                        logger.error(f"Failed to sync parent {parent_id}: {str(e)}")
                        # Continue with other items
            
            # 3. Process Subtasks
            # Fetch subtasks for all processed parents
            if created_parents:
                placeholders = ', '.join(['%s'] * len(created_parents))
                subtasks_query = f"""
                    SELECT 
                        id, parent_task_id, summary, description, issue_type,
                        priority, assignee, tags, is_jira
                    FROM project_backlog
                    WHERE parent_task_id IN ({placeholders})
                """
                
                subtasks = await self.db.execute_query(
                    subtasks_query,
                    tuple(created_parents),
                    fetch_all=True,
                    schema=tenant_name
                )
                
                if subtasks:
                    for sub in subtasks:
                        sub_id = sub['id']
                        parent_key = sub['parent_task_id']
                        
                        try:
                            priority_name = sub.get('priority').capitalize() if sub.get('priority') else None
                            
                            if sub.get('is_jira'):
                                # UPDATE existing subtask
                                await jira_service.update_issue(
                                    tenant_name=tenant_name,
                                    issue_key=sub_id,
                                    priority=priority_name,
                                    assignee_email=sub.get('assignee')
                                )
                                synced_count += 1
                            else:
                                # CREATE new subtask
                                jira_sub = await jira_service.create_issue(
                                    tenant_name=tenant_name,
                                    project_key=project_key,
                                    summary=sub['summary'],
                                    description=sub.get('description'),
                                    issue_type='Sub-task', # Force Subtask type
                                    priority=priority_name,
                                    assignee_email=sub.get('assignee'),
                                    labels=json.loads(sub['tags']) if sub.get('tags') else None,
                                    parent_key=parent_key
                                )
                                
                                new_sub_key = jira_sub['issue_key']
                                
                                if sub_id != new_sub_key:
                                    await self.backlog_repo.rename_backlog_item(tenant_name, sub_id, new_sub_key)
                                    await self.backlog_repo.update_task_jira_info(tenant_name, new_sub_key, new_sub_key)
                                    
                                synced_count += 1
                            
                        except Exception as e:
                            logger.error(f"Failed to sync subtask {sub_id}: {str(e)}")
            
            # Update next sprint date if items were synced
            if synced_count > 0:
                await self.project_repo.update_next_sprint_date(tenant_name, project_id)
            
            return {
                "synced_count": synced_count,
                "parents_processed": len(created_parents)
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error syncing to Jira: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to sync to Jira: {str(e)}"
            )

    async def list_user_tasks(
        self,
        tenant_name: str,
        email: str
    ) -> List[Dict[str, Any]]:
        """List tasks assigned to user"""
        return await self.backlog_repo.list_user_tasks(tenant_name, email)
