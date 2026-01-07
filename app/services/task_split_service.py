"""
Task Split Service

Business logic for task splitting, subtask management, and Jira integration.
"""

from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status
from app.db.database import Database
from app.db.repositories.backlog_repository import BacklogRepository
from app.services.jira_service import JiraService
from app.core.logger import logger


class TaskSplitService:
    """Service for task split operations"""
    
    def __init__(self, db: Database):
        self.db = db
        self.backlog_repo = BacklogRepository(db)
        self.jira_service = JiraService(db)
    
    async def get_parent_with_subtasks(
        self,
        tenant_name: str,
        parent_id: str
    ) -> Dict[str, Any]:
        """
        Get parent task with all its subtasks.
        
        Args:
            tenant_name: Tenant database name
            parent_id: Parent task ID
        
        Returns:
            Dictionary with parent task and subtasks
        """
        try:
            result = await self.backlog_repo.get_task_with_subtasks(tenant_name, parent_id)
            
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Task with ID {parent_id} not found"
                )
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting parent with subtasks: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get task: {str(e)}"
            )
    
    async def create_subtask(
        self,
        tenant_name: str,
        parent_id: str,
        project_id: int,
        summary: str,
        description: Optional[str] = None,
        priority: Optional[str] = None,
        assignee: Optional[str] = None,
        tags: Optional[List[str]] = None,
        estimated_hours: int = 0,
        story_points: int = 0
    ) -> Dict[str, Any]:
        """
        Create a new subtask locally (not in Jira yet).
        
        Args:
            tenant_name: Tenant database name
            parent_id: Parent task ID
            project_id: Project ID
            summary: Subtask summary
            description: Subtask description
            priority: Priority level
            assignee: Assigned person
            tags: List of tags
            estimated_hours: Estimated hours
            story_points: Story points
        
        Returns:
            Created subtask data
        """
        try:
            # Generate temporary ID
            temp_id = await self.backlog_repo.get_next_temp_id(tenant_name, project_id)
            
            # Create subtask locally
            subtask = await self.backlog_repo.create_subtask_local(
                tenant_name=tenant_name,
                temp_id=temp_id,
                parent_task_id=parent_id,
                project_id=project_id,
                summary=summary,
                description=description,
                priority=priority,
                assignee=assignee,
                tags=tags,
                estimated_hours=estimated_hours,
                story_points=story_points
            )
            
            logger.info(f"Created subtask {temp_id} for parent {parent_id}")
            return subtask
            
        except Exception as e:
            logger.error(f"Error creating subtask: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create subtask: {str(e)}"
            )
    
    async def update_subtask(
        self,
        tenant_name: str,
        subtask_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update subtask details.
        
        Args:
            tenant_name: Tenant database name
            subtask_id: Subtask ID to update
            updates: Dictionary of fields to update
        
        Returns:
            Updated subtask data
        """
        try:
            subtask = await self.backlog_repo.update_subtask(
                tenant_name=tenant_name,
                subtask_id=subtask_id,
                updates=updates
            )
            
            logger.info(f"Updated subtask {subtask_id}")
            return subtask
            
        except Exception as e:
            logger.error(f"Error updating subtask: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update subtask: {str(e)}"
            )
    
    async def delete_subtask(
        self,
        tenant_name: str,
        subtask_id: str
    ) -> bool:
        """
        Delete a subtask.
        
        Args:
            tenant_name: Tenant database name
            subtask_id: Subtask ID to delete
        
        Returns:
            True if successful
        """
        try:
            result = await self.backlog_repo.delete_backlog_item(
                tenant_name=tenant_name,
                item_id=subtask_id
            )
            
            logger.info(f"Deleted subtask {subtask_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error deleting subtask: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete subtask: {str(e)}"
            )
    
    async def merge_subtasks(
        self,
        tenant_name: str,
        subtask_ids: List[str],
        project_id: int,
        parent_id: str
    ) -> Dict[str, Any]:
        """
        Merge multiple subtasks into one.
        
        Args:
            tenant_name: Tenant database name
            subtask_ids: List of subtask IDs to merge
            project_id: Project ID
            parent_id: Parent task ID
        
        Returns:
            Newly created merged subtask
        """
        try:
            if len(subtask_ids) < 2:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="At least 2 subtasks are required for merging"
                )
            
            # Fetch all subtasks to merge
            subtasks = []
            for subtask_id in subtask_ids:
                subtask = await self.backlog_repo.get_backlog_item(tenant_name, subtask_id)
                if not subtask:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Subtask {subtask_id} not found"
                    )
                subtasks.append(subtask)
            
            # Concatenate summaries
            merged_summary = " | ".join([st.get("summary", "") for st in subtasks])
            if len(merged_summary) > 255:
                merged_summary = merged_summary[:252] + "..."
            
            # Concatenate descriptions
            descriptions = [st.get("description", "") for st in subtasks if st.get("description")]
            merged_description = "\n\n---\n\n".join(descriptions) if descriptions else None
            
            # Get highest priority
            priority_order = {"high": 3, "medium": 2, "low": 1}
            priorities = [st.get("priority") for st in subtasks if st.get("priority")]
            merged_priority = max(priorities, key=lambda p: priority_order.get(p, 0)) if priorities else None
            
            # Sum estimated hours and story points
            total_hours = sum([st.get("estimated_hours", 0) for st in subtasks])
            total_points = sum([st.get("story_points", 0) for st in subtasks])
            
            # Collect all tags
            all_tags = []
            for st in subtasks:
                if st.get("tags"):
                    all_tags.extend(st.get("tags"))
            merged_tags = list(set(all_tags)) if all_tags else None
            
            # Use first assignee
            merged_assignee = subtasks[0].get("assignee") if subtasks else None
            
            # Create merged subtask
            merged_subtask = await self.create_subtask(
                tenant_name=tenant_name,
                parent_id=parent_id,
                project_id=project_id,
                summary=merged_summary,
                description=merged_description,
                priority=merged_priority,
                assignee=merged_assignee,
                tags=merged_tags,
                estimated_hours=total_hours,
                story_points=total_points
            )
            
            # Delete original subtasks
            for subtask_id in subtask_ids:
                await self.delete_subtask(tenant_name, subtask_id)
            
            logger.info(f"Merged {len(subtask_ids)} subtasks into {merged_subtask.get('id')}")
            return merged_subtask
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error merging subtasks: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to merge subtasks: {str(e)}"
            )
    
    async def create_all_in_jira(
        self,
        tenant_name: str,
        parent_id: str,
        project_id: int
    ) -> Dict[str, Any]:
        """
        Create all local subtasks in Jira and update database.
        
        Args:
            tenant_name: Tenant database name
            parent_id: Parent task ID
            project_id: Project ID
        
        Returns:
            Results of Jira creation process
        """
        try:
            # Get parent and subtasks
            task_data = await self.backlog_repo.get_task_with_subtasks(tenant_name, parent_id)
            
            if not task_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Parent task {parent_id} not found"
                )
            
            parent = task_data.get("parent")
            subtasks = task_data.get("subtasks", [])
            
            # Filter subtasks that are not yet in Jira
            local_subtasks = [st for st in subtasks if not st.get("is_jira")]
            
            if not local_subtasks:
                return {
                    "success": True,
                    "message": "No local subtasks to create in Jira",
                    "total_subtasks": 0,
                    "created_count": 0,
                    "failed_count": 0,
                    "results": []
                }
            
            # Check if parent has Jira ID
            if not parent.get("is_jira"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parent task must be created in Jira first"
                )
            
            parent_key = parent.get("id")
            results = []
            created_count = 0
            failed_count = 0
            
            # Create each subtask in Jira
            for subtask in local_subtasks:
                temp_id = subtask.get("id")
                
                try:
                    # Create in Jira
                    jira_result = await self.jira_service.create_subtask(
                        tenant_name=tenant_name,
                        parent_key=parent_key,
                        summary=subtask.get("summary"),
                        description=subtask.get("description"),
                        priority=subtask.get("priority"),
                        assignee_email=subtask.get("assignee"),
                        labels=subtask.get("tags"),
                        estimated_hours=subtask.get("estimated_hours"),
                        story_points=subtask.get("story_points")
                    )
                    
                    jira_key = jira_result.get("issue_key")
                    
                    # Update database with Jira key
                    await self.backlog_repo.update_task_jira_info(
                        tenant_name=tenant_name,
                        old_id=temp_id,
                        new_jira_key=jira_key
                    )
                    
                    results.append({
                        "temp_id": temp_id,
                        "jira_key": jira_key,
                        "success": True,
                        "error": None
                    })
                    created_count += 1
                    logger.info(f"Created subtask in Jira: {temp_id} -> {jira_key}")
                    
                except Exception as e:
                    error_msg = str(e)
                    results.append({
                        "temp_id": temp_id,
                        "jira_key": None,
                        "success": False,
                        "error": error_msg
                    })
                    failed_count += 1
                    logger.error(f"Failed to create subtask {temp_id} in Jira: {error_msg}")
            
            success = failed_count == 0
            message = f"Created {created_count} of {len(local_subtasks)} subtasks in Jira"
            if failed_count > 0:
                message += f" ({failed_count} failed)"
            
            return {
                "success": success,
                "message": message,
                "total_subtasks": len(local_subtasks),
                "created_count": created_count,
                "failed_count": failed_count,
                "results": results
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating subtasks in Jira: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create subtasks in Jira: {str(e)}"
            )
