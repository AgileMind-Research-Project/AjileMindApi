"""
Jira Integration Service

Business logic for Jira Cloud integration.
"""

import aiohttp
import base64
import json
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status
from app.db.database import Database
from app.core.logger import logger
from app.utils.jwt import create_secret


class JiraService:
    """Service for Jira Cloud integration"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def save_credentials(
        self,
        tenant_name: str,
        jira_url: str,
        email: str,
        api_token: str
    ) -> Dict[str, Any]:
        """
        Save Jira credentials for a tenant.
        
        Args:
            tenant_name: Tenant domain name
            jira_url: Jira Cloud URL
            email: Jira account email
            api_token: Jira API token
        
        Returns:
            Saved credentials data
            
        """
        
        print("Verifying Jira credentials...",jira_url,email,api_token,tenant_name)
        # Verify credentials by testing connection
        is_valid = await self._verify_credentials(jira_url, email, api_token)
    
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Jira credentials. Please check your URL, email, and API token."
            )
        
        # Check if credentials already exist
        check_query = """
            SELECT id FROM jira_integrations
            WHERE jira_url = %s
        """
        existing = await self.db.execute_query(
            check_query,
            (jira_url,),
            fetch_one=True,
            schema=tenant_name
        )
        
        write_key = False
        
        if api_token:
            write_key = True
            
            if not existing:
                # Create a secret for the API token
                secret_name = f"jira_api_token_{tenant_name}_{jira_url.replace('https://','').replace('/','_')}"
                
                # Call sync function to create secret (not async)
                result = create_secret(secret_name, api_token)
                
                if result.get("success"):
                    write_key = True
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to store Jira API token securely: {result['message']}"
                    )
            else:
                return {"success": True, "message": "Jira API token already exists.", "jira_url": jira_url}
        else:
            return {"success": False, "message": "No API token provided."}

        
        
        
        if existing:
            # Update existing credentials
            update_query = """
                UPDATE jira_integrations
                SET  email = %s, api_token = %s,updated_at = NOW()
                WHERE jira_url = %s
            """
            await self.db.execute_query(
                update_query,
                (email, write_key, jira_url),
                commit=True,
                schema=tenant_name
            )
            logger.info(f"Updated Jira credentials for tenant {tenant_name}")
        else:
            # Insert new credentials
            insert_query = """
                INSERT INTO jira_integrations 
                (jira_url, email, api_token)
                VALUES (%s, %s, %s)
            """
            await self.db.execute_query(
                insert_query,
                (jira_url, email, write_key),
                commit=True,
                schema=tenant_name
            )
            logger.info(f"Saved Jira credentials for tenant {tenant_name}")
        
        return {
            "jira_url": jira_url,
            "email": email,
            "is_active": True
        }
    
    async def get_credentials(self, tenant_name: str) -> Optional[Dict[str, Any]]:
        """
        Get Jira credentials for a tenant.
        
        Args:
            tenant_name: Tenant domain name
        
        Returns:
            Credentials data or None if not found
        """
        try:
            query = """
                SELECT jira_url, email, api_token, created_at, updated_at
                FROM jira_integrations
                WHERE api_token = 1
                ORDER BY updated_at DESC
                LIMIT 1
            """
            result = await self.db.execute_query(
                query,
                fetch_one=True,
                schema=tenant_name
            )
            
            if result:
                return {
                    "jira_url": result.get("jira_url"),
                    "email": result.get("email"),
                    "api_token": result.get("api_token"),
                    "is_active": bool(result.get("api_token")),
                    "created_at": result.get("created_at"),
                    "updated_at": result.get("updated_at")
                }
            return None
        except Exception as e:
            logger.error(f"Error getting Jira credentials: {str(e)}")
            return None
    
    async def get_all_integrations(self, tenant_name: str) -> List[Dict[str, Any]]:
        """
        Get all Jira integrations for a tenant.
        
        Args:
            tenant_name: Tenant domain name
        
        Returns:
            List of all Jira integration accounts
        """
        try:
            query = """
                SELECT id, jira_url, email, api_token, created_at, updated_at
                FROM jira_integrations
                ORDER BY updated_at DESC
            """
            results = await self.db.execute_query(
                query,
                fetch_all=True,
                schema=tenant_name
            )
            
            if results:
                return [
                    {
                        "id": row.get("id"),
                        "jira_url": row.get("jira_url"),
                        "email": row.get("email"),
                        "is_active": bool(row.get("api_token")),
                        "created_at": row.get("created_at"),
                        "updated_at": row.get("updated_at")
                    }
                    for row in results
                ]
            return []
        except Exception as e:
            logger.error(f"Error getting all Jira integrations: {str(e)}")
            return []
    
    async def get_projects(self, tenant_name: str) -> List[Dict[str, Any]]:
        """
        Get list of Jira projects.
        
        Args:
            tenant_name: Tenant domain name
        
        Returns:
            List of Jira projects
        """
        credentials = await self.get_credentials(tenant_name)
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Jira integration not configured. Please connect Jira first."
            )
        
        try:
            # Get API token from credentials
            jira_url = credentials["jira_url"]
            email = credentials["email"]
            
            # For now, we'll use a placeholder since API token retrieval needs to be implemented
            # TODO: Implement secure retrieval of API token from secrets manager
            
            auth_str = f"{email}:api_token_placeholder"
            auth_bytes = auth_str.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                "Authorization": f"Basic {auth_b64}",
                "Accept": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{jira_url}/rest/api/3/project",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        projects = await response.json()
                        return [
                            {
                                "id": project.get("id"),
                                "key": project.get("key"),
                                "name": project.get("name"),
                                "projectTypeKey": project.get("projectTypeKey")
                            }
                            for project in projects
                        ]
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Failed to fetch Jira projects. Please check your credentials."
                        )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching Jira projects: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch projects: {str(e)}"
            )
    
    async def create_issue(
        self,
        tenant_name: str,
        project_key: str,
        summary: str,
        description: Optional[str] = None,
        issue_type: str = "Task",
        priority: Optional[str] = "Medium",
        assignee_email: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a Jira issue.
        
        Args:
            tenant_name: Tenant domain name
            project_key: Jira project key
            summary: Issue summary
            description: Issue description
            issue_type: Issue type (Task, Story, Bug, etc.)
            priority: Priority level
            assignee_email: Assignee email
            labels: Issue labels
        
        Returns:
            Created issue data
        """
        credentials = await self.get_credentials(tenant_name)
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Jira integration not configured. Please connect Jira first."
            )
        
        try:
            jira_url = credentials["jira_url"]
            email = credentials["email"]
            
            # TODO: Implement secure retrieval of API token
            auth_str = f"{email}:api_token_placeholder"
            auth_bytes = auth_str.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                "Authorization": f"Basic {auth_b64}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            
            issue_data = {
                "fields": {
                    "project": {"key": project_key},
                    "summary": summary,
                    "issuetype": {"name": issue_type}
                }
            }
            
            if description:
                issue_data["fields"]["description"] = {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description}]
                        }
                    ]
                }
            
            if priority:
                issue_data["fields"]["priority"] = {"name": priority}
            
            if labels:
                issue_data["fields"]["labels"] = labels
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{jira_url}/rest/api/3/issue",
                    headers=headers,
                    json=issue_data,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status in [200, 201]:
                        result = await response.json()
                        return {
                            "issue_key": result.get("key"),
                            "issue_id": result.get("id"),
                            "self": result.get("self")
                        }
                    else:
                        error_text = await response.text()
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Failed to create Jira issue: {error_text}"
                        )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating Jira issue: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create issue: {str(e)}"
            )
    
    async def _verify_credentials(
        self,
        jira_url: str,
        email: str,
        api_token: str
    ) -> bool:
        """Verify Jira credentials by testing API connection"""
        try:
            auth_str = f"{email}:{api_token}"
            auth_bytes = auth_str.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                "Authorization": f"Basic {auth_b64}",
                "Accept": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{jira_url}/rest/api/3/myself",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Error verifying Jira credentials: {str(e)}")
            return False
    
    