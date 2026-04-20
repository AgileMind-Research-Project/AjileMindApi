"""
Jira Cloud Integration API Endpoints

Handles Jira integration, issue creation, and synchronization.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from typing import Dict, Any, List

from app.db.database import db, Database
from app.core.logger import logger
from app.utils.jwt import get_current_user_from_token
from app.services.jira_service import JiraService
from app.schemas.jira_schemas import (
    JiraCredentialsRequest,
    JiraCredentialsResponse,
    JiraIssueRequest,
    JiraIssueResponse,
    JiraIssueResponse,
    JiraProjectsResponse,
    JiraTransitionRequest
)


router = APIRouter()


# ============================================
# DEPENDENCIES
# ============================================

async def get_database() -> Database:
    """Dependency to get database instance"""
    return db


async def get_jira_service(database: Database = Depends(get_database)) -> JiraService:
    """Dependency to get Jira service instance"""
    return JiraService(database)


async def verify_admin_access(
    current_user: Dict[str, Any] = Depends(get_current_user_from_token)
) -> Dict[str, Any]:
    """Verify that the user has admin access"""
    # New token payload uses `roles`.
    user_roles = current_user.get("roles") or []
    if isinstance(user_roles, str):
        user_roles = [user_roles]

    if not any(role in ["SUPER_ADMIN", "ADMIN"] for role in user_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user



@router.post(
    "/connect",
    response_model=JiraCredentialsResponse,
    summary="Connect Jira Cloud",
    description="Connect or update Jira Cloud integration for the tenant"
)
async def connect_jira(
    request: JiraCredentialsRequest,
    current_user: Dict[str, Any] = Depends(verify_admin_access),
    jira_service: JiraService = Depends(get_jira_service)
) -> Dict[str, Any]:
    """
    Connect Jira Cloud integration.
    
    Saves Jira credentials and verifies connection.
    Requires Admin or Super Admin access.
    
    **Steps to get Jira API token:**
    1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
    2. Click "Create API token"
    3. Copy the generated token
    
    **Example:**
    ```json
    {
        "jira_url": "https://yourcompany.atlassian.net",
        "email": "your-email@company.com",
        "api_token": "your-api-token-here"
    }
    ```
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        result = await jira_service.save_credentials(
            tenant_name=tenant_name,
            jira_url=str(request.jira_url),
            email=request.email,
            api_token=request.api_token
        )
        
        logger.info(f"Jira connected for tenant {tenant_name} by {current_user['email']}")
        
        return {
            "success": True,
            "message": "Jira Cloud connected successfully",
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting Jira: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect Jira: {str(e)}"
        )


@router.get(
    "/projects",
    response_model=JiraProjectsResponse,
    summary="Get Jira Projects",
    description="Fetch all accessible Jira projects"
)
async def get_jira_projects(
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    jira_service: JiraService = Depends(get_jira_service)
) -> Dict[str, Any]:
    """
    Get list of Jira projects accessible with configured credentials.
    
    Returns project key, name, and type information.
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        projects = await jira_service.get_projects(tenant_name)
        
        return {
            "success": True,
            "message": f"Found {len(projects)} Jira projects",
            "data": projects
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching Jira projects: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch projects: {str(e)}"
        )


@router.post(
    "/issues",
    response_model=JiraIssueResponse,
    summary="Create Jira Issue",
    description="Create a new issue in Jira Cloud"
)
async def create_jira_issue(
    request: JiraIssueRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    jira_service: JiraService = Depends(get_jira_service)
) -> Dict[str, Any]:
    """
    Create a new Jira issue.
    
    **Supported Issue Types:**
    - Task
    - Story
    - Bug
    - Epic
    - Subtask
    
    **Priority Levels:**
    - Highest
    - High
    - Medium
    - Low
    - Lowest
    
    **Example:**
    ```json
    {
        "project_key": "PROJ",
        "summary": "Implement user authentication",
        "description": "Add JWT-based authentication to the API",
        "issue_type": "Task",
        "priority": "High",
        "assignee_email": "developer@company.com",
        "labels": ["backend", "security"]
    }
    ```
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        result = await jira_service.create_issue(
            tenant_name=tenant_name,
            project_key=request.project_key,
            summary=request.summary,
            description=request.description,
            issue_type=request.issue_type,
            priority=request.priority,
            assignee_email=request.assignee_email,
            labels=request.labels
        )
        
        logger.info(
            f"Jira issue {result['issue_key']} created by {current_user['email']}"
        )
        
        return {
            "success": True,
            "message": f"Jira issue {result['issue_key']} created successfully",
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating Jira issue: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create issue: {str(e)}"
        )


@router.get(
    "/status",
    summary="Get Jira Integration Status",
    description="Get all Jira integration accounts for the tenant"
)
async def get_jira_status(
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    jira_service: JiraService = Depends(get_jira_service)
) -> Dict[str, Any]:
    """
    Get all Jira integration accounts for the tenant.
    
    Returns a list of all Jira integrations with their status.
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        integrations = await jira_service.get_all_integrations(tenant_name)
        
        if integrations:
            # Also check if any active integration exists
            has_active = any(integration.get("is_active") for integration in integrations)
            
            return {
                "success": True,
                "message": f"Found {len(integrations)} Jira integration(s)",
                "data": {
                    "connected": has_active,
                    "integrations": integrations,
                    "total": len(integrations)
                }
            }
        else:
            return {
                "success": True,
                "message": "No Jira integrations found",
                "data": {
                    "connected": False,
                    "integrations": [],
                    "total": 0
                }
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking Jira status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check status: {str(e)}"
        )


@router.delete(
    "/disconnect",
    summary="Disconnect Jira",
    description="Disconnect Jira integration for the tenant"
)
async def disconnect_jira(
    current_user: Dict[str, Any] = Depends(verify_admin_access),
    database: Database = Depends(get_database)
) -> Dict[str, Any]:
    """
    Disconnect Jira integration.
    
    Deactivates the Jira connection for the tenant.
    Requires Admin or Super Admin access.
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        # Set api_token to 0 (inactive) for all integrations in this tenant
        query = """
            UPDATE jira_integrations
            SET api_token = 0, updated_at = NOW()
        """
        
        await database.execute_query(
            query,
            commit=True,
            schema=tenant_name
        )
        
        logger.info(f"Jira disconnected for tenant {tenant_name} by {current_user['email']}")
        
        return {
            "success": True,
            "message": "Jira integration disconnected successfully",
            "data": {
                "connected": False
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting Jira: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect: {str(e)}"
        )


@router.get(
    "/issues/{issue_key}/status",
    summary="Get Issue Status",
    description="Get current status of a Jira issue"
)
async def get_issue_status(
    issue_key: str,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    jira_service: JiraService = Depends(get_jira_service)
) -> Dict[str, Any]:
    """
    Get status of a Jira issue.
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        result = await jira_service.get_issue_status(
            tenant_name=tenant_name,
            issue_key=issue_key
        )
        
        return {
            "success": True,
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting issue status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get issue status: {str(e)}"
        )


@router.post(
    "/issues/{issue_key}/transition",
    summary="Transition Issue",
    description="Transition a Jira issue to a new status (e.g. Done)"
)
async def transition_issue(
    issue_key: str,
    request: JiraTransitionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    jira_service: JiraService = Depends(get_jira_service)
) -> Dict[str, Any]:
    """
    Transition a Jira issue.
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        result = await jira_service.transition_issue_to_status(
            tenant_name=tenant_name,
            issue_key=issue_key,
            target_status=request.target_status
        )
        
        return {
            "success": True,
            "message": f"Issue transitioned to {request.target_status}",
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error transitioning issue: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to transition issue: {str(e)}"
        )
