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
    JiraProjectsResponse
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
    if current_user.get("role") not in ["SUPER_ADMIN", "ADMIN"]:
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
    description="Check if Jira is connected for the tenant"
)
async def get_jira_status(
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    jira_service: JiraService = Depends(get_jira_service)
) -> Dict[str, Any]:
    """
    Get Jira integration status for the tenant.
    
    Returns whether Jira is connected and basic configuration info.
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        credentials = await jira_service.get_credentials(tenant_name)
        
        if credentials:
            return {
                "success": True,
                "message": "Jira is connected",
                "data": {
                    "connected": True,
                    "jira_url": credentials["jira_url"],
                    "email": credentials["email"],
                    "is_active": bool(credentials["is_active"])
                }
            }
        else:
            return {
                "success": True,
                "message": "Jira not connected",
                "data": {
                    "connected": False
                }
            }
        
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
        
        query = """
            UPDATE jira_integrations
            SET is_active = 0, updated_at = NOW()
            WHERE tenant_name = %s
        """
        
        await database.execute_query(
            query,
            (tenant_name,),
            commit=True
        )
        
        logger.info(f"Jira disconnected for tenant {tenant_name} by {current_user['email']}")
        
        return {
            "success": True,
            "message": "Jira integration disconnected successfully",
            "data": {
                "connected": False
            }
        }
        
    except Exception as e:
        logger.error(f"Error disconnecting Jira: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect: {str(e)}"
        )
