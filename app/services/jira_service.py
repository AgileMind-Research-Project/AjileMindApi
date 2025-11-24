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
            WHERE tenant_name = %s
        """
        existing = await self.db.execute_query(
            check_query,
            (tenant_name,),
            fetch_one=True
        )
        
        if existing:
            # Update existing credentials
            update_query = """
                UPDATE jira_integrations
                SET jira_url = %s, email = %s, api_token = %s, 
                    is_active = 1, updated_at = NOW()
                WHERE tenant_name = %s
            """
            await self.db.execute_query(
                update_query,
                (jira_url, email, api_token, tenant_name),
                commit=True
            )
            logger.info(f"Updated Jira credentials for tenant {tenant_name}")
        else:
            # Insert new credentials
            insert_query = """
                INSERT INTO jira_integrations 
                (tenant_name, jira_url, email, api_token, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, 1, NOW(), NOW())
            """
            await self.db.execute_query(
                insert_query,
                (tenant_name, jira_url, email, api_token),
                commit=True
            )
            logger.info(f"Saved Jira credentials for tenant {tenant_name}")
        
        return {
            "jira_url": jira_url,
            "email": email,
            "is_active": True
        }
    
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
    
    async def get_credentials(self, tenant_name: str) -> Optional[Dict[str, Any]]:
        """Get Jira credentials for a tenant"""
        query = """
            SELECT jira_url, email, api_token, is_active
            FROM jira_integrations
            WHERE tenant_name = %s AND is_active = 1
        """
        credentials = await self.db.execute_query(
            query,
            (tenant_name,),
            fetch_one=True
        )
        
        return credentials
    
    async def create_issue(
        self,
        tenant_name: str,
        project_key: str,
        summary: str,
        description: Optional[str] = None,
        issue_type: str = "Task",
        priority: str = "Medium",
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
        # Get credentials
        creds = await self.get_credentials(tenant_name)
        
        if not creds:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Jira integration not configured. Please connect Jira first."
            )
        
        # Prepare auth
        auth_str = f"{creds['email']}:{creds['api_token']}"
        auth_b64 = base64.b64encode(auth_str.encode('ascii')).decode('ascii')
        
        headers = {
            "Authorization": f"Basic {auth_b64}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        # Build issue payload
        issue_data = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "issuetype": {"name": issue_type},
                "priority": {"name": priority}
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
        
        if assignee_email:
            issue_data["fields"]["assignee"] = {"emailAddress": assignee_email}
        
        if labels:
            issue_data["fields"]["labels"] = labels
        
        # Create issue in Jira
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{creds['jira_url']}/rest/api/3/issue",
                    headers=headers,
                    json=issue_data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 201:
                        result = await response.json()
                        logger.info(f"Created Jira issue {result['key']} for tenant {tenant_name}")
                        
                        return {
                            "issue_key": result["key"],
                            "issue_id": result["id"],
                            "self": result["self"],
                            "jira_url": f"{creds['jira_url']}/browse/{result['key']}"
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Jira API error: {error_text}")
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Failed to create Jira issue: {error_text}"
                        )
        except aiohttp.ClientError as e:
            logger.error(f"Error creating Jira issue: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to connect to Jira: {str(e)}"
            )
    
    async def get_projects(self, tenant_name: str) -> List[Dict[str, Any]]:
        """Get list of Jira projects"""
        creds = await self.get_credentials(tenant_name)
        
        if not creds:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Jira integration not configured"
            )
        
        auth_str = f"{creds['email']}:{creds['api_token']}"
        auth_b64 = base64.b64encode(auth_str.encode('ascii')).decode('ascii')
        
        headers = {
            "Authorization": f"Basic {auth_b64}",
            "Accept": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{creds['jira_url']}/rest/api/3/project",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        projects = await response.json()
                        return [
                            {
                                "id": p["id"],
                                "key": p["key"],
                                "name": p["name"],
                                "project_type": p.get("projectTypeKey", ""),
                                "avatar_url": p.get("avatarUrls", {}).get("48x48", "")
                            }
                            for p in projects
                        ]
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Failed to fetch Jira projects"
                        )
        except Exception as e:
            logger.error(f"Error fetching Jira projects: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
