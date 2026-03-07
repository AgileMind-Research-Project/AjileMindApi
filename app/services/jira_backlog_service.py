"""
Jira Backlog Service

Service for creating backlog items in Jira using the Atlassian Python API.
Inspired by the AWS Lambda script for Jira integration.
"""

from atlassian import Jira
from typing import Dict, Any, Optional, List
from app.core.logger import logger
from app.schemas.backlog_schemas import BacklogItemCreate


# Jira custom field ID for severity (configure per tenant if needed)
SEVERITY_FIELD_ID = "customfield_10165"


class JiraBacklogService:
    """Service for Jira backlog operations"""
    
    def __init__(self, jira_url: str, email: str, api_token: str):
        """
        Initialize Jira client.
        
        Args:
            jira_url: Jira instance URL
            email: Jira user email
            api_token: Jira API token
        """
        self.jira_client = Jira(
            url=jira_url,
            username=email,
            password=api_token,
            cloud=True
        )
        logger.info(f"Jira client initialized for {jira_url}")
    
    def create_issue(
        self,
        project_key: str,
        backlog_item: BacklogItemCreate
    ) -> Dict[str, Any]:
        """
        Create a single issue in Jira.
        
        Args:
            project_key: Jira project key (e.g., "PROJ")
            backlog_item: Backlog item data
        
        Returns:
            Dictionary with Jira issue key and details
        """
        try:
            # Map our issue types to Jira issue types
            issue_type_mapping = {
                "epic": "Epic",
                "story": "Story",
                "feature": "Story",  # Feature mapped to Story in Jira
                "task": "Task",
                "change": "Task",
                "bug": "Bug",
                "sub_task": "Sub-task"
            }
            
            jira_issue_type = issue_type_mapping.get(
                backlog_item.issue_type.value,
                "Story"
            )
            
            # Build issue fields
            fields = {
                "project": {"key": project_key},
                "summary": backlog_item.summary,
                "description": backlog_item.description or "",
                "issuetype": {"name": jira_issue_type}
            }
            
            # Add priority if specified
            if backlog_item.priority:
                priority_mapping = {
                    "high": "High",
                    "medium": "Medium",
                    "low": "Low"
                }
                fields["priority"] = {
                    "name": priority_mapping.get(backlog_item.priority.value, "Medium")
                }
            
            # Add assignee if specified
            if backlog_item.assignee:
                # Try to assign by email or account ID
                fields["assignee"] = {"emailAddress": backlog_item.assignee}
            
            # Add labels (tags)
            if backlog_item.tags:
                fields["labels"] = backlog_item.tags
            
            # Add severity for bugs (capitalize first letter for Jira)
            if backlog_item.issue_type.value == "bug" and backlog_item.severity:
                # Jira expects severity value in an array format: [{"value": "Critical"}]
                severity_formatted = backlog_item.severity.capitalize()
                fields[SEVERITY_FIELD_ID] = [{"value": severity_formatted}]
            
            logger.info(f"Creating Jira issue: {backlog_item.summary}")
            
            # Create the issue
            issue = self.jira_client.create_issue(fields=fields)
            
            issue_key = issue.get("key")
            logger.info(f"Successfully created Jira issue: {issue_key}")
            
            return {
                "issue_key": issue_key,
                "issue_id": issue.get("id"),
                "self_link": issue.get("self")
            }
            
        except Exception as e:
            logger.error(f"Error creating Jira issue: {str(e)}")
            raise Exception(f"Failed to create Jira issue: {str(e)}")
    
    def create_subtask(
        self,
        project_key: str,
        parent_jira_key: str,
        summary: str,
        description: Optional[str] = None,
        priority: Optional[str] = None,
        assignee: Optional[str] = None,
        tags: Optional[List[str]] = None,
        estimated_hours: int = 0,
        story_points: int = 0
    ) -> Dict[str, Any]:
        """
        Create a Sub-task in Jira linked to a parent task.
        
        Args:
            project_key: Jira project key (e.g., "PROJ")
            parent_jira_key: Parent issue key (e.g., "PROJ-123")
            summary: Subtask summary
            description: Subtask description
            priority: Priority level
            assignee: Assignee email
            tags: List of labels
            estimated_hours: Estimated hours
            story_points: Story points
        
        Returns:
            Dictionary with Jira subtask key and details
        """
        try:
            # Build subtask fields
            fields = {
                "project": {"key": project_key},
                "parent": {"key": parent_jira_key},
                "summary": summary,
                "description": description or "",
                "issuetype": {"name": "Sub-task"}
            }
            
            # Add priority if specified
            if priority:
                priority_mapping = {
                    "high": "High",
                    "medium": "Medium",
                    "low": "Low"
                }
                fields["priority"] = {
                    "name": priority_mapping.get(priority.lower(), "Medium")
                }
            
            # Add assignee if specified
            if assignee:
                fields["assignee"] = {"emailAddress": assignee}
            
            # Add labels (tags)
            if tags:
                fields["labels"] = tags
            
            logger.info(f"Creating Jira Sub-task under {parent_jira_key}: {summary}")
            
            # Create the subtask
            issue = self.jira_client.create_issue(fields=fields)
            
            issue_key = issue.get("key")
            logger.info(f"Successfully created Jira Sub-task: {issue_key}")
            
            return {
                "issue_key": issue_key,
                "issue_id": issue.get("id"),
                "self_link": issue.get("self")
            }
            
        except Exception as e:
            logger.error(f"Error creating Jira Sub-task: {str(e)}")
            raise Exception(f"Failed to create Jira Sub-task: {str(e)}")
    
    def bulk_create_issues(
        self,
        project_key: str,
        backlog_items: List[BacklogItemCreate]
    ) -> Dict[str, Any]:
        """
        Create multiple issues in Jira with progress logging.
        
        Args:
            project_key: Jira project key
            backlog_items: List of backlog items
        
        Returns:
            Dictionary with created issue keys and any errors
        """
        created_issues = []
        errors = []
        total = len(backlog_items)
        
        logger.info(f"Starting bulk creation of {total} Jira issues for project {project_key}")
        
        for idx, item in enumerate(backlog_items, 1):
            try:
                logger.info(f"Processing item {idx}/{total}: {item.summary}")
                result = self.create_issue(project_key, item)
                created_issues.append({
                    "issue_key": result["issue_key"],
                    "summary": item.summary
                })
                logger.info(f"[OK] Created {result['issue_key']} ({idx}/{total})")
            except Exception as e:
                error_msg = f"Failed to create '{item.summary}': {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        logger.info(f"Bulk creation completed: {len(created_issues)}/{total} successful")
        
        return {
            "created": created_issues,
            "errors": errors,
            "total_processed": total,
            "total_created": len(created_issues),
            "total_failed": len(errors)
        }
