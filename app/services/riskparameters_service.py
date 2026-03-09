from app.db.database import db
from app.schemas.riskparameters_schema import RiskParameters
from fastapi import HTTPException
import aiomysql


class RiskParametersService:

    # CREATE
    async def create_parameters(self, tenant_name: str, params: RiskParameters):
        """
        Create risk parameters for a project in the tenant database.
        
        Args:
            tenant_name: Tenant database name
            params: Risk parameters data
            
        Returns:
            Success message
        """
        # Check if parameters already exist for this project
        existing = await self.get_parameters(tenant_name, params.project_id)
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Risk parameters already exist for project {params.project_id}. Use update endpoint instead."
            )

        query = """
            INSERT INTO tbl_risk_parameters_selection (
                project_id,
                uncompleted_tasks, uncompleted_tasks_weight,
                detected_bugs, detected_bugs_weight,
                blockers_count, blockers_count_weight,
                developer_workload, developer_workload_weight,
                task_dependency, task_dependency_weight,
                timeline_conflict, timeline_conflict_weight,
                developer_availability, developer_availability_weight,
                task_progress, task_progress_weight,
                sprint_completion_level, sprint_completion_level_weight,
                project_budget, project_budget_weight
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """

        values = (
            params.project_id,
            params.uncompleted_tasks, params.uncompleted_tasks_weight,
            params.detected_bugs, params.detected_bugs_weight,
            params.blockers_count, params.blockers_count_weight,
            params.developer_workload, params.developer_workload_weight,
            params.task_dependency, params.task_dependency_weight,
            params.timeline_conflict, params.timeline_conflict_weight,
            params.developer_availability, params.developer_availability_weight,
            params.task_progress, params.task_progress_weight,
            params.sprint_completion_level, params.sprint_completion_level_weight,
            params.project_budget, params.project_budget_weight
        )

        # Use tenant database schema
        await db.execute_query(query, values, commit=True, schema=tenant_name)

        return {"message": "Risk parameters saved successfully"}


    # GET BY PROJECT
    async def get_parameters(self, tenant_name: str, project_id: int):
        """
        Get risk parameters for a project from the tenant database.
        
        Args:
            tenant_name: Tenant database name
            project_id: Project ID
            
        Returns:
            Risk parameters dict or None if not found
        """
        query = "SELECT * FROM tbl_risk_parameters_selection WHERE project_id=%s"

        result = await db.execute_query(
            query, 
            (project_id,), 
            fetch_one=True, 
            schema=tenant_name
        )

        if not result:
            return None

        return dict(result)


    # UPDATE
    async def update_parameters(self, tenant_name: str, params: RiskParameters):
        """
        Update risk parameters for a project in the tenant database.
        
        Args:
            tenant_name: Tenant database name
            params: Updated risk parameters data
            
        Returns:
            Success message
        """
        query = """
            UPDATE tbl_risk_parameters_selection SET
                uncompleted_tasks=%s, uncompleted_tasks_weight=%s,
                detected_bugs=%s, detected_bugs_weight=%s,
                blockers_count=%s, blockers_count_weight=%s,
                developer_workload=%s, developer_workload_weight=%s,
                task_dependency=%s, task_dependency_weight=%s,
                timeline_conflict=%s, timeline_conflict_weight=%s,
                developer_availability=%s, developer_availability_weight=%s,
                task_progress=%s, task_progress_weight=%s,
                sprint_completion_level=%s, sprint_completion_level_weight=%s,
                project_budget=%s, project_budget_weight=%s
            WHERE project_id=%s
        """

        values = (
            params.uncompleted_tasks, params.uncompleted_tasks_weight,
            params.detected_bugs, params.detected_bugs_weight,
            params.blockers_count, params.blockers_count_weight,
            params.developer_workload, params.developer_workload_weight,
            params.task_dependency, params.task_dependency_weight,
            params.timeline_conflict, params.timeline_conflict_weight,
            params.developer_availability, params.developer_availability_weight,
            params.task_progress, params.task_progress_weight,
            params.sprint_completion_level, params.sprint_completion_level_weight,
            params.project_budget, params.project_budget_weight,
            params.project_id
        )

        # Use tenant database schema
        await db.execute_query(query, values, commit=True, schema=tenant_name)

        return {"message": "Risk parameters updated successfully"}
