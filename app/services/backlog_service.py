"""
Backlog Service

Business logic for backlog management including file processing and Jira integration.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import io
from fastapi import UploadFile, HTTPException, status
from app.db.repositories.backlog_repository import BacklogRepository
from app.services.jira_backlog_service import JiraBacklogService
from app.schemas.backlog_schemas import (
    BacklogItemCreate,
    BacklogItemFromFile,
    BacklogItemResponse,
    BulkUploadResponse
)
from app.db.database import Database
from app.core.logger import logger


class BacklogService:
    """Service for backlog operations"""
    
    def __init__(self, db: Database):
        self.db = db
        self.backlog_repo = BacklogRepository(db)
    
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
                        severity=str(row.get('severity', '')) if pd.notna(row.get('severity')) else None
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
                        severity=backlog_item.severity
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

    async def update_backlog_item(
        self,
        tenant_name: str,
        item_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a backlog item"""
        try:
            return await self.backlog_repo.update_subtask(tenant_name, item_id, updates)
        except Exception as e:
            logger.error(f"Error updating backlog item: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update backlog item: {str(e)}"
            )

    async def merge_backlog_items(
        self,
        tenant_name: str,
        target_id: str,
        source_ids: List[str],
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge multiple items into one: update target and delete sources"""
        try:
            # 1. Update the target item
            updated_item = await self.backlog_repo.update_subtask(tenant_name, target_id, updates)
            
            # 2. Delete source items
            for source_id in source_ids:
                if source_id != target_id: # Prevent accidental self-deletion
                    await self.backlog_repo.delete_backlog_item(tenant_name, source_id)
            
            return updated_item
        except Exception as e:
            logger.error(f"Error merging backlog items: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to merge backlog items: {str(e)}"
            )

    async def delete_backlog_item(
        self,
        tenant_name: str,
        item_id: str
    ) -> bool:
        """Delete a backlog item and reorder siblings if it's a subtask"""
        try:
            logger.info(f"Attempting to delete item: {item_id}")
            # 1. Get the item
            item = await self.backlog_repo.get_backlog_item(tenant_name, item_id)
            if not item:
                logger.warning(f"Item {item_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Backlog item {item_id} not found"
                )

            parent_id = item.get('parent_task_id')
            logger.info(f"Item {item_id} parent: {parent_id}")
            
            # If not a subtask, simple delete
            if not parent_id:
                return await self.backlog_repo.delete_backlog_item(tenant_name, item_id)

            # 2. It is a subtask. Get all siblings to determining reordering.
            parent_data = await self.backlog_repo.get_task_with_subtasks(tenant_name, parent_id)
            if not parent_data:
                 logger.warning(f"Parent {parent_id} data not found, performing simple delete")
                 return await self.backlog_repo.delete_backlog_item(tenant_name, item_id)

            siblings = parent_data.get('subtasks', [])
            logger.info(f"Found {len(siblings)} siblings for parent {parent_id}")
            
            # Sort by ID to ensure consistent ordering matching user expectation
            # We attempt to sort by the numeric suffix if possible to handle "SUB-2" vs "SUB-10" correctly.
            def intelligent_sort_key(item):
                try:
                    # Extract last part of ID after split
                    parts = item['id'].split('-')
                    if parts[-1].isdigit():
                        return int(parts[-1])
                except:
                    pass
                return item['id'].lower()

            siblings.sort(key=intelligent_sort_key)
            
            # Log sibling IDs for debug
            sibling_ids = [s['id'] for s in siblings]
            logger.info(f"Sorted siblings: {sibling_ids}")

            # 3. Find index
            try:
                # Find matching ID using case-insensitive comparison just to be safe
                target_index = next(i for i, s in enumerate(siblings) if s['id'].lower() == item_id.lower())
                logger.info(f"Target index for {item_id}: {target_index}")
            except StopIteration:
                logger.warning(f"Item {item_id} not found in siblings list (checked {len(siblings)} items), performing simple delete")
                return await self.backlog_repo.delete_backlog_item(tenant_name, item_id)

            # Store original IDs for shifting (these are the 'slots' available)
            original_ids = [s['id'] for s in siblings]

            # 4. Delete the item
            deleted = await self.backlog_repo.delete_backlog_item(tenant_name, item_id)
            if not deleted:
                logger.error(f"Failed to delete item {item_id} from DB")
                return False
            
            logger.info(f"Deleted {item_id}, proceeding to shift remaining items")

            # 5. Shift subsequent items
            # Only shift if we deleted something before the end
            if target_index < len(siblings) - 1:
                # We iterate through the remaining siblings that were after the deleted one
                tasks_to_shift = siblings[target_index+1:]
                logger.info(f"Found {len(tasks_to_shift)} items to shift")
                
                for i, task in enumerate(tasks_to_shift):
                    old_id = task['id']
                    # Calculate new ID: it should take the ID of the slot before it
                    # The task was at index `target_index + 1 + i`
                    # We want to move it to `target_index + i`
                    new_id = original_ids[target_index + i] 
                    
                    logger.info(f"Shifting: {old_id} -> {new_id}")
                    
                    if old_id != new_id: 
                        try:
                            await self.backlog_repo.rename_backlog_item(tenant_name, old_id, new_id)
                        except Exception as e:
                            logger.error(f"Failed to rename {old_id} to {new_id}: {str(e)}")
                            # Continue trying to shift others even if one fails? 
                            # Probably best to log and continue to salvage what we can.

            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting backlog item: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete backlog item: {str(e)}"
            )
