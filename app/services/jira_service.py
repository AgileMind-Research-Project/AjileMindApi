"""
Jira Integration Service

Business logic for Jira Cloud integration.
"""

import aiohttp
import base64
import json
from dotenv import load_dotenv

# Load environment variables explicitly
load_dotenv()
import os
import requests
from typing import Optional, Dict, Any, List
from datetime import date
from fastapi import HTTPException, status
from app.db.database import Database
from app.core.logger import logger
from app.utils.jwt import create_secret, get_secret


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
                secret_name = f"tenant_{tenant_name}_jira_api_token_{jira_url.replace('https://','').replace('/','_')}"
                
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
                print(result,'jira credentials result')
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
            
            # Get API token from secret manager
            secret_name = f"tenant_{tenant_name}_jira_api_token_{jira_url.replace('https://','').replace('/','_')}"
            secret_result = get_secret(secret_name)
            
            if not secret_result.get("success"):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve Jira API token from secure storage"
                )
            
            api_token = secret_result.get("secret_value")
            
            auth_str = f"{email}:{api_token}"
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
        labels: Optional[List[str]] = None,
        parent_key: Optional[str] = None
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
            parent_key: Parent issue key (for subtasks)
        
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
            
            # Get API token from secret manager
            secret_name = f"tenant_{tenant_name}_jira_api_token_{jira_url.replace('https://','').replace('/','_')}"
            secret_result = get_secret(secret_name)
            
            if not secret_result.get("success"):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve Jira API token from secure storage"
                )
            
            api_token = secret_result.get("secret_value")
            
            auth_str = f"{email}:{api_token}"
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
                
            if parent_key:
                issue_data["fields"]["parent"] = {"key": parent_key}
            
            # Handle Assignee
            if assignee_email:
                account_id = await self._get_account_id(jira_url, email, api_token, assignee_email)
                if account_id:
                    issue_data["fields"]["assignee"] = {"id": account_id}
            
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
    
    async def update_issue(
        self,
        tenant_name: str,
        issue_key: str,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[str] = None,
        assignee_email: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> bool:
        """
        Update a Jira issue.
        
        Args:
            tenant_name: Tenant domain name
            issue_key: Jira issue key (e.g., TEAM-123)
            summary: New summary
            description: New description
            priority: New priority
            assignee_email: New assignee email
            labels: New labels
            
        Returns:
            True if successful
        """
        credentials = await self.get_credentials(tenant_name)
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Jira integration not configured."
            )
        
        try:
            jira_url = credentials["jira_url"]
            email = credentials["email"]
            
            # Get API token
            secret_name = f"tenant_{tenant_name}_jira_api_token_{jira_url.replace('https://','').replace('/','_')}"
            secret_result = get_secret(secret_name)
            
            if not secret_result.get("success"):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve Jira API token"
                )
            
            api_token = secret_result.get("secret_value")
            
            auth_str = f"{email}:{api_token}"
            auth_bytes = auth_str.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                "Authorization": f"Basic {auth_b64}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            
            fields = {}
            
            if summary:
                fields["summary"] = summary
                
            if description:
                fields["description"] = {
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
                fields["priority"] = {"name": priority}
                
            if labels:
                fields["labels"] = labels
            
            # Handle Assignee
            if assignee_email is not None:
                if assignee_email:
                    account_id = await self._get_account_id(jira_url, email, api_token, assignee_email)
                    if account_id:
                        fields["assignee"] = {"id": account_id}
                else:
                    # Unassign if empty string passed? Or handle differently.
                    # For now, if empty string, maybe explicitly unassign or ignore.
                    # Jira API uses null for unassign usually, or -1.
                    # Let's assume valid email or None.
                    pass

            if not fields:
                return True # Nothing to update
                
            async with aiohttp.ClientSession() as session:
                async with session.put(
                    f"{jira_url}/rest/api/3/issue/{issue_key}",
                    headers=headers,
                    json={"fields": fields},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 204:
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to update Jira issue {issue_key}: {error_text}")
                        # Don't raise here, just return False so sync doesn't completely fail?
                        # Or raise to propagate error.
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Failed to update Jira issue: {error_text}"
                        )
                        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating Jira issue: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update issue: {str(e)}"
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
    
    async def _get_account_id(
        self,
        jira_url: str,
        email: str,
        api_token: str,
        target_email: str = None
    ) -> Optional[str]:
        """
        Get Jira account ID.
        If target_email is None, gets ID for authenticated user.
        If target_email is provided, searches for that user.
        """
        try:
            auth_str = f"{email}:{api_token}"
            auth_bytes = auth_str.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                "Authorization": f"Basic {auth_b64}",
                "Accept": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                if target_email:
                    # Search for user by email
                    async with session.get(
                        f"{jira_url}/rest/api/3/user/search",
                        headers=headers,
                        params={"query": target_email},
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 200:
                            users = await response.json()
                            if users and len(users) > 0:
                                # Return first match
                                return users[0].get("accountId")
                else:
                    # Get current user
                    async with session.get(
                        f"{jira_url}/rest/api/3/myself",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 200:
                            user_data = await response.json()
                            return user_data.get("accountId")
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting account ID: {str(e)}")
            return None
    
    async def create_project(
        self,
        tenant_name: str,
        project_name: str,
        key: str,
        project_type: str = "software",
        template: str = "com.pyxis.greenhopper.jira:gh-scrum-template",
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new project in Jira Cloud.
        
        Args:
            tenant_name: Tenant database name
            project_name: Project name
            key: Project key (2-10 uppercase letters)
            project_type: Project type (software, business, service_desk)
            template: Project template key
            description: Project description
        
        Returns:
            Created project data with id, key, and name
            
        Raises:
            HTTPException: If credentials not found or project creation fails
        """
        # Get Jira credentials
        credentials = await self.get_credentials(tenant_name)
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Jira integration not configured. Please connect Jira first."
            )
        
        jira_url = credentials["jira_url"]
        email = credentials["email"]
        
        # Get API token from secret manager
        secret_name = f"tenant_{tenant_name}_jira_api_token_{jira_url.replace('https://','').replace('/','_')}"
        secret_result = get_secret(secret_name)
        
        if not secret_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve Jira API token from secure storage"
            )
        
        api_token = secret_result.get("secret_value")
        
        try:
            # Get account ID for project lead
            account_id = await self._get_account_id(jira_url, email, api_token)
            
            if not account_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get Jira account ID"
                )
            
            # Prepare project creation payload
            payload = {
                "key": key.upper(),
                "name": project_name,
                "projectTypeKey": project_type,
                "projectTemplateKey": template,
                "leadAccountId": account_id
            }
            
            if description:
                payload["description"] = description
            
            # Create authorization header
            auth_str = f"{email}:{api_token}"
            auth_bytes = auth_str.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                "Authorization": f"Basic {auth_b64}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            
            # Create project using REST API
            response = requests.post(
                f"{jira_url}/rest/api/3/project",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                project_data = response.json()
                project_key = project_data.get("key")
                logger.info(f"Project created in Jira: {project_key} - {project_data.get('name')}")

                # Fetch the board ID created automatically for this project
                board_id = await self.get_board_id(
                    jira_url=jira_url,
                    email=email,
                    api_token=api_token,
                    project_key=project_key
                )
                if board_id:
                    logger.info(f"Fetched board ID {board_id} for project {project_key}")
                else:
                    logger.warning(f"Could not fetch board ID for project {project_key}. It will be stored as NULL.")

                return {
                    "project_id": int(project_data.get("id")),
                    "key": project_key,
                    "name": project_data.get("name"),
                    "self": project_data.get("self"),
                    "board_id": board_id,
                    "jira_url": f"{jira_url}/projects/{project_key}"
                }
            else:
                error_data = response.json()
                errors = error_data.get("errors", {})
                error_messages = error_data.get("errorMessages", [])
                
                # Handle specific errors
                if "projectName" in errors:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Project name already exists: {errors['projectName']}"
                    )
                elif "projectKey" in errors:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Project key already exists: {errors['projectKey']}"
                    )
                elif error_messages:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Jira error: {'; '.join(error_messages)}"
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Failed to create project in Jira: {response.text}"
                    )
                    
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating Jira project: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create project: {str(e)}"
            )

    async def get_board_id(
        self,
        jira_url: str,
        email: str,
        api_token: str,
        project_key: str,
        max_retries: int = 4,
        retry_wait_seconds: float = 3.0
    ) -> Optional[int]:
        """
        Fetch the Jira Agile board ID for a given project key.

        Jira provisions the board asynchronously after project creation, so this
        method retries up to `max_retries` times with `retry_wait_seconds` delay
        between attempts to give Jira time to finish board setup.

        Calls:
            GET /rest/agile/1.0/board?projectKeyOrId={key}

        Args:
            jira_url:            Base Jira Cloud URL
            email:               Jira account email
            api_token:           Jira API token
            project_key:         Project key (e.g. "MYPROJ")
            max_retries:         How many times to try before giving up (default 4)
            retry_wait_seconds:  Seconds to wait between retries (default 3)

        Returns:
            The integer board ID, or None if not found after all retries.
        """
        import asyncio

        auth_str = f"{email}:{api_token}"
        auth_b64 = base64.b64encode(auth_str.encode("ascii")).decode("ascii")
        headers = {
            "Authorization": f"Basic {auth_b64}",
            "Accept": "application/json"
        }

        for attempt in range(1, max_retries + 1):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{jira_url}/rest/agile/1.0/board",
                        headers=headers,
                        params={"projectKeyOrId": project_key},
                        timeout=aiohttp.ClientTimeout(total=15)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            values = data.get("values", [])
                            if values:
                                board_id = values[0].get("id")
                                logger.info(
                                    f"Board found for project {project_key} "
                                    f"on attempt {attempt}: board_id={board_id}"
                                )
                                return int(board_id) if board_id is not None else None
                            else:
                                # Board not provisioned yet — Jira is still setting up
                                logger.warning(
                                    f"Board not ready yet for project {project_key} "
                                    f"(attempt {attempt}/{max_retries}). "
                                    f"Waiting {retry_wait_seconds}s before retry..."
                                )
                        else:
                            body = await resp.text()
                            logger.warning(
                                f"Board lookup HTTP {resp.status} for project {project_key} "
                                f"(attempt {attempt}/{max_retries}): {body}"
                            )
            except Exception as exc:
                logger.error(
                    f"Error fetching board for project {project_key} "
                    f"(attempt {attempt}/{max_retries}): {exc}"
                )

            # Wait before next attempt (skip wait on last attempt)
            if attempt < max_retries:
                await asyncio.sleep(retry_wait_seconds)

        logger.error(
            f"Board for project {project_key} not found after {max_retries} attempts."
        )
        return None

    async def get_jira_sprints_by_board(
        self,
        jira_url: str,
        email: str,
        api_token: str,
        board_id: int,
        state: str = "future,active,closed",
        start_at: int = 0,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Fetch all sprints for a given Jira board (reusable).

        Equivalent to the JIRA library call:
            sprints = jira.sprints(board_id, state="future,active,closed", startAt=0, maxResults=50)
            for sprint in sprints:
                print(f"ID: {sprint.id} | Name: {sprint.name} | State: {sprint.state}")

        Calls:
            GET /rest/agile/1.0/board/{boardId}/sprint
                ?state=future,active,closed&startAt=0&maxResults=50

        Args:
            jira_url:    Base Jira Cloud URL (e.g. https://yourcompany.atlassian.net)
            email:       Authenticated Jira account email
            api_token:   Jira API token
            board_id:    The Jira board ID to fetch sprints for
            state:       Comma-separated sprint states to include
                         (future | active | closed)
            start_at:    Pagination offset (default 0)
            max_results: Max sprints to return per page (default 50)

        Returns:
            List of sprint dicts, each containing:
                id    – Jira sprint ID  (int)
                name  – Sprint name     (str)
                state – Sprint state    (str: "active" | "future" | "closed")
                startDate, endDate, completeDate (str | None)
            Returns [] on error or if board has no sprints.
        """
        try:
            auth_str = f"{email}:{api_token}"
            auth_b64 = base64.b64encode(auth_str.encode("ascii")).decode("ascii")

            headers = {
                "Authorization": f"Basic {auth_b64}",
                "Accept": "application/json"
            }

            params = {
                "state": state,
                "startAt": start_at,
                "maxResults": max_results
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{jira_url}/rest/agile/1.0/board/{board_id}/sprint",
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        raw_sprints = data.get("values", [])
                        sprints = [
                            {
                                "id":           s.get("id"),
                                "name":         s.get("name"),
                                "state":        s.get("state"),
                                "startDate":    s.get("startDate"),
                                "endDate":      s.get("endDate"),
                                "completeDate": s.get("completeDate")
                            }
                            for s in raw_sprints
                        ]
                        logger.info(
                            f"Fetched {len(sprints)} sprint(s) for board {board_id} "
                            f"(state={state})"
                        )
                        return sprints
                    else:
                        body = await resp.text()
                        logger.warning(
                            f"Agile sprint lookup returned HTTP {resp.status} "
                            f"for board {board_id}: {body}"
                        )
                        return []

        except Exception as exc:
            logger.error(f"Error fetching sprints for board {board_id}: {exc}")
            return []

    async def add_issues_to_sprint(
        self,
        tenant_name: str,
        sprint_id: int,
        issue_keys: List[str]
    ) -> bool:
        """
        Add Jira issue keys to a sprint.

        Calls:
            POST /rest/agile/1.0/sprint/{sprint_id}/issue
            Body: { "issues": ["TAM-1", "TAM-2", ...] }

        Args:
            tenant_name: Tenant schema name (to look up credentials)
            sprint_id:   Jira sprint ID
            issue_keys:  List of Jira issue keys (e.g. ["TAM-195", "TAM-196"])

        Returns:
            True if all issues were added (HTTP 204), False otherwise.
        """
        if not issue_keys:
            return True  # nothing to add

        credentials = await self.get_credentials(tenant_name)
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Jira integration not configured."
            )

        jira_url = credentials["jira_url"]
        email = credentials["email"]
        secret_name = (
            f"tenant_{tenant_name}_jira_api_token_"
            f"{jira_url.replace('https://','').replace('/','_')}"
        )
        secret_result = get_secret(secret_name)
        if not secret_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve Jira API token from secure storage"
            )
        api_token = secret_result.get("secret_value")

        auth_b64 = base64.b64encode(f"{email}:{api_token}".encode("ascii")).decode("ascii")
        headers = {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{jira_url}/rest/agile/1.0/sprint/{sprint_id}/issue",
                    headers=headers,
                    json={"issues": issue_keys},
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status == 204:
                        logger.info(
                            f"Added {len(issue_keys)} issue(s) to Jira sprint {sprint_id}: "
                            f"{issue_keys}"
                        )
                        return True
                    else:
                        body = await resp.text()
                        logger.error(
                            f"Failed to add issues to sprint {sprint_id} "
                            f"(HTTP {resp.status}): {body}"
                        )
                        return False
        except Exception as exc:
            logger.error(f"Error adding issues to sprint {sprint_id}: {exc}")
            return False

    async def start_jira_sprint(
        self,
        tenant_name: str,
        sprint_id: int,
        sprint_name: str,
        board_id: int,
        start_date: str,
        end_date: str
    ) -> bool:
        """
        Activate (start) a Jira sprint via the Agile REST API.

        Calls:
            PUT /rest/agile/1.0/sprint/{sprint_id}
            Body: { id, name, state: "active", startDate, endDate, originBoardId }

        Args:
            tenant_name: Tenant schema name (to look up credentials)
            sprint_id:   Jira sprint ID
            sprint_name: Sprint display name (e.g. "Sprint 1")
            board_id:    Jira board ID (originBoardId)
            start_date:  ISO string  e.g. "2026-03-06T09:00:00.000+0000"
            end_date:    ISO string  e.g. "2026-03-20T18:00:00.000+0000"

        Returns:
            True if sprint was started (HTTP 200), False otherwise.
        """
        credentials = await self.get_credentials(tenant_name)
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Jira integration not configured."
            )

        jira_url = credentials["jira_url"]
        email = credentials["email"]
        secret_name = (
            f"tenant_{tenant_name}_jira_api_token_"
            f"{jira_url.replace('https://','').replace('/','_')}"
        )
        secret_result = get_secret(secret_name)
        if not secret_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve Jira API token from secure storage"
            )
        api_token = secret_result.get("secret_value")

        auth_b64 = base64.b64encode(f"{email}:{api_token}".encode("ascii")).decode("ascii")
        headers = {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {
            "id": sprint_id,
            "name": sprint_name,
            "state": "active",
            "startDate": start_date,
            "endDate": end_date,
            "originBoardId": board_id,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.put(
                    f"{jira_url}/rest/agile/1.0/sprint/{sprint_id}",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status == 200:
                        logger.info(
                            f"Jira sprint {sprint_id} started: "
                            f"{start_date} → {end_date} (board {board_id})"
                        )
                        return True
                    else:
                        body = await resp.text()
                        logger.error(
                            f"Failed to start Jira sprint {sprint_id} "
                            f"(HTTP {resp.status}): {body}"
                        )
                        return False
        except Exception as exc:
            logger.error(f"Error starting Jira sprint {sprint_id}: {exc}")
            return False

    async def get_jira_sprints_by_board(
        self,
        jira_url: str,
        email: str,
        api_token: str,
        board_id: int,
        state: str = "future,active"
    ) -> List[Dict[str, Any]]:
        """
        Fetch sprints for a specific board from Jira Agile API.
        
        Args:
            state: Filter by state (comma-separated: e.g. "future,active,closed")
        """
        auth_b64 = base64.b64encode(f"{email}:{api_token}".encode("ascii")).decode("ascii")
        headers = {
            "Authorization": f"Basic {auth_b64}",
            "Accept": "application/json",
        }
        params = {"state": state}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{jira_url}/rest/agile/1.0/board/{board_id}/sprint",
                headers=headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("values", [])
                else:
                    body = await resp.text()
                    logger.error(f"Failed to fetch Jira sprints for board {board_id} (HTTP {resp.status}): {body}")
                    return []

    async def create_jira_sprint(
        self,
        tenant_name: str,
        board_id: int,
        sprint_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new sprint in Jira Cloud for a specific board.
        
        Args:
            tenant_name: Tenant name to resolve credentials
            board_id: The Jira board ID the sprint belongs to
            sprint_name: Name of the new sprint (e.g. "Sprint 1")
            
        Returns:
            The created sprint object (dict with id, name, self, etc.) or None if failed.
        """
        credentials = await self.get_credentials(tenant_name)
        if not credentials:
            return None

        jira_url = credentials["jira_url"]
        email = credentials["email"]
        secret_name = f"tenant_{tenant_name}_jira_api_token_{jira_url.replace('https://','').replace('/','_')}"
        secret_result = get_secret(secret_name)
        
        if not secret_result.get("success"):
            return None
            
        api_token = secret_result.get("secret_value")
        auth_b64 = base64.b64encode(f"{email}:{api_token}".encode("ascii")).decode("ascii")
        headers = {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        payload = {
            "name": sprint_name,
            "originBoardId": board_id
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{jira_url}/rest/agile/1.0/sprint",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status in [200, 201]:
                        data = await resp.json()
                        logger.info(f"Created new Jira sprint '{sprint_name}' (ID: {data.get('id')})")
                        return data
                    else:
                        body = await resp.text()
                        logger.error(f"Failed to create Jira sprint (HTTP {resp.status}): {body}")
                        return None
        except Exception as e:
            logger.error(f"Error creating Jira sprint: {str(e)}")
            return None

    async def get_issue_status(self, tenant_name: str, issue_key: str) -> Dict[str, Any]:
        """
        Get current status of a Jira issue.
        """
        credentials = await self.get_credentials(tenant_name)
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Jira integration not configured."
            )
        
        jira_url = credentials["jira_url"]
        email = credentials["email"]
        secret_name = f"tenant_{tenant_name}_jira_api_token_{jira_url.replace('https://','').replace('/','_')}"
        secret_result = get_secret(secret_name)
        
        if not secret_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve Jira API token"
            )
        
        # Strip and uppercase the issue key
        issue_key = issue_key.strip().upper()
        jira_url = jira_url.rstrip('/')
        api_token = secret_result.get("secret_value", "").strip()
        
        auth_b64 = base64.b64encode(f"{email}:{api_token}".encode("ascii")).decode("ascii")
        
        headers = {
            "Authorization": f"Basic {auth_b64}",
            "Accept": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{jira_url}/rest/api/3/issue/{issue_key}",
                headers=headers,
                params={"fields": "status,summary,resolution"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    fields = data.get("fields", {})
                    status_data = fields.get("status", {})
                    return {
                        "issue_key": issue_key,
                        "status": status_data.get("name"),
                        "status_category": status_data.get("statusCategory", {}).get("name"),
                        "summary": fields.get("summary"),
                        "is_resolved": fields.get("resolution") is not None
                    }
                elif response.status == 404:
                    return {
                        "issue_key": issue_key,
                        "status": "Local",
                        "status_category": "Unknown",
                        "summary": "Issue not found in Jira",
                        "is_resolved": False
                    }
                else:
                    error_text = await response.text()
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Failed to get Jira issue status: {error_text}"
                    )

    async def transition_issue_to_status(self, tenant_name: str, issue_key: str, target_status: str) -> Dict[str, Any]:
        """
        Transition a Jira issue to a new status.
        """
        credentials = await self.get_credentials(tenant_name)
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Jira integration not configured."
            )
        
        jira_url = credentials["jira_url"]
        email = credentials["email"]
        secret_name = f"tenant_{tenant_name}_jira_api_token_{jira_url.replace('https://','').replace('/','_')}"
        secret_result = get_secret(secret_name)
        
        if not secret_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve Jira API token"
            )
        
        api_token = secret_result.get("secret_value")
        auth_b64 = base64.b64encode(f"{email}:{api_token}".encode("ascii")).decode("ascii")
        
        headers = {
            "Authorization": f"Basic {auth_b64}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            # 1. Get available transitions
            async with session.get(
                f"{jira_url}/rest/api/3/issue/{issue_key}/transitions",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as trans_resp:
                if trans_resp.status != 200:
                    error_text = await trans_resp.text()
                    raise HTTPException(
                        status_code=trans_resp.status,
                        detail=f"Failed to fetch available transitions: {error_text}"
                    )
                
                transitions_data = await trans_resp.json()
                transitions = transitions_data.get("transitions", [])
                
                # Find matching transition
                transition_id = None
                for t in transitions:
                    if t.get("name").lower() == target_status.lower() or t.get("to", {}).get("name").lower() == target_status.lower():
                        transition_id = t.get("id")
                        break
                
                if not transition_id:
                    available_statuses = [t.get("name") for t in transitions]
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Status '{target_status}' not available for transition. Available: {', '.join(available_statuses)}"
                    )
                
                # 2. Perform transition
                async with session.post(
                    f"{jira_url}/rest/api/3/issue/{issue_key}/transitions",
                    headers=headers,
                    json={"transition": {"id": transition_id}},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as post_resp:
                    if post_resp.status == 204:
                        return {
                            "issue_key": issue_key,
                            "new_status": target_status,
                            "success": True
                        }
                    else:
                        error_text = await post_resp.text()
                        raise HTTPException(
                            status_code=post_resp.status,
                            detail=f"Failed to transition issue: {error_text}"
                        )

    # -------------------------------------------------------------------------
    # Issue Type Management
    # -------------------------------------------------------------------------

    async def create_issue_type(
        self,
        tenant_name: str,
        name: str,
        description: str = "",
        issue_type: str = "standard",   # "standard" | "subtask"
        hierarchy_level: int = 0        # 0=Story/Task level, -1=Subtask, 1=Epic
    ) -> Dict[str, Any]:
        """
        Create a new issue type in Jira Cloud.

        Calls:
            POST /rest/api/3/issuetype
            Body: { name, description, type, hierarchyLevel }

        Args:
            tenant_name:     Tenant schema name (to look up credentials)
            name:            Issue type name  (e.g. "Bug", "Feature Request")
            description:     Short description shown in Jira UI
            issue_type:      "standard" (default) or "subtask"
            hierarchy_level: 0 = standard task level (default)
                             1 = Epic level
                            -1 = Subtask level

        Returns:
            Dict with id, name, description, subtask, hierarchyLevel, iconUrl

        Raises:
            HTTPException 400 if a type with that name already exists,
            HTTPException 500 on credential or network errors.
        """
        credentials = await self.get_credentials(tenant_name)
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Jira integration not configured. Please connect Jira first."
            )

        jira_url = credentials["jira_url"]
        email    = credentials["email"]

        secret_name = (
            f"tenant_{tenant_name}_jira_api_token_"
            f"{jira_url.replace('https://','').replace('/','_')}"
        )
        secret_result = get_secret(secret_name)
        if not secret_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve Jira API token from secure storage"
            )
        api_token = secret_result.get("secret_value")

        auth_b64 = base64.b64encode(f"{email}:{api_token}".encode("ascii")).decode("ascii")
        headers = {
            "Authorization": f"Basic {auth_b64}",
            "Accept":        "application/json",
            "Content-Type":  "application/json",
        }

        payload = {
            "name":           name,
            "description":    description,
            "type":           issue_type,          # "standard" | "subtask"
            "hierarchyLevel": hierarchy_level,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{jira_url}/rest/api/3/issuetype",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    body = await resp.json()
                    if resp.status in [200, 201]:
                        logger.info(f"Created Jira issue type '{name}' (id={body.get('id')})")
                        return {
                            "id":             body.get("id"),
                            "name":           body.get("name"),
                            "description":    body.get("description"),
                            "subtask":        body.get("subtask"),
                            "hierarchyLevel": body.get("hierarchyLevel"),
                            "iconUrl":        body.get("iconUrl"),
                        }
                    else:
                        errors = body.get("errorMessages", []) or [str(body)]
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Failed to create issue type '{name}': {'; '.join(errors)}"
                        )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Error creating Jira issue type '{name}': {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create issue type: {exc}"
            )

    # -------------------------------------------------------------------------
    # Custom Field Management
    # -------------------------------------------------------------------------

    # Severity numeric weights used by Backlog_prioritize.py
    SEVERITY_WEIGHT_MAP: Dict[str, int] = {
        "blocker":  5,
        "critical": 4,
        "major":    3,
        "minor":    2,
        "trivial":  1,
    }

    async def create_severity_custom_field(
        self,
        tenant_name: str,
        field_name: str = "Severity",
        field_description: str = "Issue severity: blocker > critical > major > minor > trivial"
    ) -> Dict[str, Any]:
        """
        Create a 'Severity' Select List (single choice) custom field in Jira Cloud
        with options: Blocker(5), Critical(4), Major(3), Minor(2), Trivial(1).

        Workflow
        --------
        1. POST /rest/api/3/field              → creates the custom field
        2. GET  /rest/api/3/field/{id}/context → fetches its default context id
        3. POST /rest/api/3/field/{id}/context/{ctxId}/option
                                               → adds all five severity options

        Args:
            tenant_name:       Tenant schema name (to look up credentials)
            field_name:        Display name for the custom field (default "Severity")
            field_description: Help text shown in Jira UI

        Returns:
            Dict with:
                field_id   – e.g. "customfield_10165"
                field_name – display name
                context_id – default context id
                options    – list of created option dicts {id, value, disabled}

        Raises:
            HTTPException on credential errors or Jira API failures.
        """
        credentials = await self.get_credentials(tenant_name)
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Jira integration not configured. Please connect Jira first."
            )

        jira_url = credentials["jira_url"]
        email    = credentials["email"]

        secret_name = (
            f"tenant_{tenant_name}_jira_api_token_"
            f"{jira_url.replace('https://','').replace('/','_')}"
        )
        secret_result = get_secret(secret_name)
        if not secret_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve Jira API token from secure storage"
            )
        api_token = secret_result.get("secret_value")

        auth_b64 = base64.b64encode(f"{email}:{api_token}".encode("ascii")).decode("ascii")
        headers = {
            "Authorization": f"Basic {auth_b64}",
            "Accept":        "application/json",
            "Content-Type":  "application/json",
        }

        try:
            async with aiohttp.ClientSession() as session:

                # ----------------------------------------------------------
                # Step 1: Create the custom field (Select List – single choice)
                # ----------------------------------------------------------
                field_payload = {
                    "name":        field_name,
                    "description": field_description,
                    "type":        "com.atlassian.jira.plugin.system.customfieldtypes:select",
                    "searcherKey": "com.atlassian.jira.plugin.system.customfieldtypes:multiselectsearcher",
                }

                async with session.post(
                    f"{jira_url}/rest/api/3/field",
                    headers=headers,
                    json=field_payload,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    body = await resp.json()
                    if resp.status not in [200, 201]:
                        errors = body.get("errorMessages", []) or [str(body)]
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Failed to create custom field: {'; '.join(errors)}"
                        )
                    field_id   = body.get("id")    # e.g. "customfield_10165"
                    field_name = body.get("name")
                    logger.info(f"Created custom field '{field_name}' → {field_id}")

                # ----------------------------------------------------------
                # Step 2: Get the default context id for this field
                # ----------------------------------------------------------
                async with session.get(
                    f"{jira_url}/rest/api/3/field/{field_id}/context",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    ctx_body = await resp.json()
                    if resp.status != 200:
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to fetch field context: {ctx_body}"
                        )
                    contexts   = ctx_body.get("values", [])
                    context_id = contexts[0].get("id") if contexts else None
                    if not context_id:
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="No context found for the newly created field."
                        )
                    logger.info(f"Field context id for '{field_id}': {context_id}")

                # ----------------------------------------------------------
                # Step 3: Add severity options (ordered by weight descending)
                # ----------------------------------------------------------
                options_payload = {
                    "options": [
                        {"value": label.capitalize(), "disabled": False}
                        for label in ["blocker", "critical", "major", "minor", "trivial"]
                    ]
                }

                async with session.post(
                    f"{jira_url}/rest/api/3/field/{field_id}/context/{context_id}/option",
                    headers=headers,
                    json=options_payload,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    opt_body = await resp.json()
                    if resp.status not in [200, 201]:
                        errors = opt_body.get("errorMessages", []) or [str(opt_body)]
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Failed to create field options: {'; '.join(errors)}"
                        )
                    created_options = opt_body.get("options", [])
                    logger.info(
                        f"Created {len(created_options)} options for field '{field_id}'"
                    )

            return {
                "field_id":    field_id,
                "field_name":  field_name,
                "context_id":  context_id,
                "options":     created_options,
                # Convenience: weight map for use in Backlog_prioritize.py
                "weight_map":  self.SEVERITY_WEIGHT_MAP,
            }

        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Error creating severity custom field: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create custom field: {exc}"
            )
