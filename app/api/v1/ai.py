"""
AI API Endpoints

Endpoints for:
- Parsing transcripts using Ollama
- Syncing parsed data to Jira/Backlog/Leaves
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body
from app.db.database import get_db as get_database
from app.services.ai_service import AIService
from app.services.leave_service import LeaveService
from app.services.backlog_service import BacklogService
from app.services.jira_service import JiraService
from app.services.meeting_service import get_meeting_service
from app.db.database import Database
from pydantic import BaseModel
from app.core.logger import logger

router = APIRouter()

# --- Request Schemas ---

class TaskItem(BaseModel):
    summary: str
    description: Optional[str] = None
    assignee: Optional[str] = None
    estimate: Optional[str] = None
    type: str = "Task"
    priority: str = "Medium"

class LeaveItem(BaseModel):
    developer_name: str
    leave_date: str
    type: str
    hours: int

class SprintInfo(BaseModel):
    name: str
    goal: Optional[str] = None
    start_date: str
    end_date: str

class SyncDataRequest(BaseModel):
    transcript_id: Optional[int] = None
    tasks: List[TaskItem] = []
    leaves: List[LeaveItem] = []
    project_id: int
    sprint_id: Optional[int] = None
    new_sprint: Optional[SprintInfo] = None

# --- Endpoints ---

from app.utils.jwt import get_current_user_from_token

# ... (imports)

@router.post("/parse_transcript/{transcript_id}", response_model=Dict[str, Any])
async def parse_transcript(
    transcript_id: int,
    db: Database = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user_from_token)
):
    """
    Parse a transcript from the database using AI.
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
             # Fallback if no tenant in token, though unlikely if auth passed
             # Check if there's a global config or default to a known DB like 'sliit' based on user history? 
             # Or raise error.
             raise HTTPException(status_code=400, detail="Tenant not found in token")

        query = "SELECT transcript_content FROM transcripts WHERE id = %s"
        result = await db.execute_query(query, (transcript_id,), fetch_one=True, schema=tenant_name)
        
        if not result:
            raise HTTPException(status_code=404, detail="Transcript not found")
        
        content = result['transcript_content']
        
        ai_service = AIService()
        # if not ai_service.check_ollama_status():
        #      raise HTTPException(status_code=503, detail="Ollama service is not reachable")
             
        parsed_data = await ai_service.parse_meeting_transcript(content)
        
        return {
            "success": True,
            "data": parsed_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error parsing transcript {transcript_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync_processed_data", response_model=Dict[str, Any])
async def sync_processed_data(
    request: SyncDataRequest,
    db: Database = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user_from_token)
):
    """
    Sync confirmed data to Backlog, Jira, and Leaves.
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
             raise HTTPException(status_code=400, detail="Tenant not found in token")

        results = {
            "tasks_created": 0,
            "leaves_added": 0,
            "sprint_created": False,
            "errors": []
        }
        
        backlog_service = BacklogService(db)
        jira_service = JiraService(db)
        leave_service = LeaveService(db)
        
        # 1. Handle Sprint Creation if requested
        active_sprint_id = request.sprint_id
        
        if request.new_sprint and request.project_id:
            try:
                # Need project key for board lookup if not passed directly, but let's key off ID if we have it or fetch details
                project_query = "SELECT `key`, project_name FROM projects WHERE project_id = %s"
                p_data = await db.execute_query(project_query, (request.project_id,), fetch_one=True, schema=tenant_name)
                
                if p_data:
                    # 1a. Find Board
                    board_id = await jira_service.get_board_for_project(tenant_name, p_data['key'])
                    
                    if board_id:
                        # 1b. Create Sprint in Jira
                        jira_sprint = await jira_service.create_sprint(
                            tenant_name=tenant_name,
                            board_id=board_id,
                            name=request.new_sprint.name,
                            start_date=request.new_sprint.start_date,
                            end_date=request.new_sprint.end_date,
                            goal=request.new_sprint.goal or ""
                        )
                        
                        # 1c. Create Sprint in Local DB
                        # Assuming 'sprints' table exists: id, project_id, sprint_name, start_date, end_date, goal, status, jira_sprint_id
                        sprint_insert = """
                            INSERT INTO sprints (
                                project_id, sprint_name, start_date, end_date, goal, status, jira_sprint_id
                            ) VALUES (%s, %s, %s, %s, %s, 'ACTIVE', %s)
                        """
                        # We need the last inserted ID. execute_query typically returns it if commit=True for INSERT?
                        # Or we fetch it back.
                        # Database.execute_query returns lastrowid for INSERTs usually if implemented. 
                        # Assuming it returns dictionary or similar.
                        # For now, let's assume we can query it back by jira_sprint_id.
                        
                        jira_id = jira_sprint.get('id')
                        
                        await db.execute_query(
                            sprint_insert,
                            (
                                request.project_id, 
                                request.new_sprint.name, 
                                request.new_sprint.start_date, 
                                request.new_sprint.end_date, 
                                request.new_sprint.goal, 
                                jira_id
                            ),
                            commit=True, 
                            schema=tenant_name
                        )
                        
                        # Fetch the local ID
                        local_sprint = await db.execute_query(
                            "SELECT sprint_id FROM sprints WHERE jira_sprint_id = %s", 
                            (jira_id,), 
                            fetch_one=True, 
                            schema=tenant_name
                        )
                        
                        if local_sprint:
                            active_sprint_id = local_sprint['sprint_id']
                            results["sprint_created"] = True
                            
                    else:
                        results["errors"].append("Could not find a Scrum Board for this project in Jira.")
                else:
                    results["errors"].append("Project not found locally.")
                    
            except Exception as e:
                results["errors"].append(f"Failed to create sprint: {str(e)}")

        # 2. Process Tasks
        project_query = "SELECT `key` FROM projects WHERE project_id = %s"
        project_data = await db.execute_query(project_query, (request.project_id,), fetch_one=True, schema=tenant_name)
        
        if not project_data:
             raise HTTPException(status_code=404, detail="Project not found")
             
        project_key = project_data['key']
        
        for task in request.tasks:
            try:
                # Create in Jira
                jira_issue = await jira_service.create_issue(
                    tenant_name=tenant_name,
                    project_key=project_key,
                    summary=task.summary,
                    description=task.description,
                    issue_type=task.type,
                    priority=task.priority,
                    assignee_email=task.assignee
                )
                
                # Assign to Sprint if active_sprint_id is set (and valid Jira Sprint ID exists)
                # Note: create_issue doesn't support sprint assignment directly easily unless field is known.
                # Easier to move it to sprint if we have the backlog service or update issue.
                # For now, simplistic approach: just create. Assignment to sprint usually requires 'customfield_XXX' for Sprint.
                # Skipping strict Sprint assignment in Jira for this MVP step unless user asks.
                # But we SHOULD link it in Local DB.
                
                # Check for existing
                
                query_backlog = """
                    INSERT INTO project_backlog (
                        id, project_id, summary, description, issue_type, status, priority, assignee, is_jira, sprint_id
                    ) VALUES (%s, %s, %s, %s, %s, 'todo', %s, %s, 1, %s)
                """
                await db.execute_query(
                    query_backlog,
                    (
                        jira_issue['issue_key'], 
                        request.project_id, 
                        task.summary, 
                        task.description, 
                        task.type, 
                        task.priority, 
                        task.assignee,
                        active_sprint_id # Link to the new or selected sprint locally
                    ),
                    commit=True,
                    schema=tenant_name
                )
                
                results["tasks_created"] += 1
                
            except Exception as e:
                results["errors"].append(f"Failed to create task '{task.summary}': {str(e)}")
        
        # 3. Process Leaves
        if active_sprint_id:
            for leave in request.leaves:
                try:
                    await leave_service.add_sprint_leave(
                        tenant_name=tenant_name,
                        sprint_id=active_sprint_id,
                        project_id=request.project_id,
                        developer_name=leave.developer_name,
                        leave_date=leave.leave_date,
                        leave_hours=leave.hours,
                        leave_type=leave.type
                    )
                    results["leaves_added"] += 1
                except Exception as e:
                    results["errors"].append(f"Failed to add leave for '{leave.developer_name}': {str(e)}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error syncing data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
