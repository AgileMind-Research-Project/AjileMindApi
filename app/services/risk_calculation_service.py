"""
Risk Calculation Service

Calculates project risk scores based on selected parameters and weights.
"""

from typing import Dict, List, Any, Optional
from datetime import date, datetime
import aiomysql
import copy
from app.db.database import db
from app.core.logger import logger
from fastapi import HTTPException


class RiskCalculationService:
    """Service for calculating project risk scores"""

    # Bug priority weights
    CRITICAL_BUG_WEIGHT = 3
    HIGH_BUG_WEIGHT = 2
    MEDIUM_BUG_WEIGHT = 1.5
    LOW_BUG_WEIGHT = 1

    async def calculate_project_risk(self, tenant_name: str, project_id: int) -> Dict[str, Any]:
        """
        Calculate total risk score for a project.
        
        Args:
            tenant_name: Tenant database name
            project_id: Project ID to calculate risk for
            
        Returns:
            Dictionary containing total risk score, breakdown, and metadata
        """
        try:
            # Step 1: Fetch risk parameters configuration
            params_config = await self._get_risk_parameters(tenant_name, project_id)
            if not params_config:
                raise HTTPException(
                    status_code=404,
                    detail=f"Risk parameters not found for project {project_id}. Please configure risk parameters first."
                )

            # Step 2: Fetch all project data
            tasks_list = await self._get_all_tasks(tenant_name, project_id)
            sprints_list = await self._get_all_sprints(tenant_name, project_id)
            leaves_list = await self._get_all_leaves(tenant_name, project_id)
            blockers_list = await self._get_all_blockers(tenant_name, project_id)
            project_budget = await self._get_project_budget(tenant_name, project_id)

            # Step 3: Calculate base metrics
            metrics = self._calculate_base_metrics(tasks_list, sprints_list, leaves_list, blockers_list)
            metrics['project_budget_limit'] = project_budget

            # Step 3.5: Calculate available developers (low workload)
            available_developers_data = self._calculate_available_developers(
                tasks_list, sprints_list, leaves_list, project_id
            )
            metrics['available_developers_data'] = available_developers_data


            # Step 4-5: Calculate individual and total risk scores
            risk_result = self._calculate_risk_from_metrics(metrics, params_config)
            breakdown = risk_result['breakdown']
            total_risk_score = risk_result['total_risk_score']
            total_weight = risk_result['total_weight']

            # Calculate contribution for each parameter
            for item in breakdown:
                if item['enabled'] and total_weight > 0:
                    item['contribution'] = round(item['weighted_value'] / total_weight, 4)

            # Step 6: Determine risk level
            risk_level = self._determine_risk_level(total_risk_score)
            
            # Calculate risk percentage (0-100)
            risk_percentage = round(total_risk_score * 100, 2)

            return {
                'project_id': project_id,
                'total_risk_score': round(total_risk_score, 4),
                'risk_percentage': risk_percentage,
                'risk_level': risk_level,
                'total_weight': total_weight,
                'breakdown': breakdown,
                'metadata': {
                    'total_tasks': metrics['total_tasks'],
                    'uncompleted_tasks': metrics['uncompleted_tasks'],
                    'completed_tasks': metrics['completed_tasks'],
                    'blocked_tasks': metrics['blocked_tasks'],
                    # Task breakdown (task_type = 'Task')
                    'todo_tasks': metrics['todo_tasks_only'],
                    'inprogress_tasks': metrics['inprogress_tasks_only'],
                    'completed_tasks_only': metrics['completed_tasks_only'],
                    'overdue_tasks': metrics['overdue_tasks'],
                    'max_overdue_days': metrics['max_overdue_days'],
                    # Task risk percentages (for insights)
                    'todo_tasks_risk': metrics['todo_tasks_risk'],
                    'inprogress_tasks_risk': metrics['inprogress_tasks_risk'],
                    'overdue_tasks_risk': metrics['overdue_tasks_risk'],
                    # Bug breakdown
                    # Bug breakdown
                    'total_bugs': metrics['total_bugs'],
                    'critical_bugs': metrics['critical_bugs'],
                    'high_bugs': metrics['high_bugs'],
                    'medium_bugs': metrics['medium_bugs'],
                    'low_bugs': metrics['low_bugs'],
                    'high_priority_bugs': metrics['critical_bugs'] + metrics['high_bugs'],
                    'medium_priority_bugs': metrics['medium_bugs'],
                    'low_priority_bugs': metrics['low_bugs'],
                    'weighted_bug_score': metrics['weighted_bug_score'],
                    'max_bug_score': metrics['max_bug_score'],
                    # Bug status breakdown
                    'todo_bugs': metrics['todo_bugs'],
                    'inprogress_bugs': metrics['inprogress_bugs'],
                    'completed_bugs': metrics['completed_bugs'],
                    # Bug risk percentages (for insights)
                    'todo_bugs_risk': metrics['todo_bugs_risk'],
                    'inprogress_bugs_risk': metrics['inprogress_bugs_risk'],
                    'completed_bugs_risk': 0,
                    'high_priority_bugs_risk': metrics['high_priority_bugs_risk'],
                    # Blocker breakdown
                    'total_blockers': metrics['total_blockers'],
                    'open_blockers': metrics['open_blockers'],
                    'inprogress_blockers': metrics['inprogress_blockers'],
                    'resolved_blockers': metrics['resolved_blockers'],
                    # Blocker severity breakdown (unresolved only)
                    'critical_blockers': metrics['critical_blockers'],
                    'high_blockers': metrics['high_blockers'],
                    'medium_blockers': metrics['medium_blockers'],
                    'low_blockers': metrics['low_blockers'],
                    'weighted_blocker_score': metrics['weighted_blocker_score'],
                    'max_blocker_score': metrics['max_blocker_score'],
                    # Blocker risk percentages (for insights)
                    'open_blockers_risk': metrics['open_blockers_risk'],
                    'inprogress_blockers_risk': metrics['inprogress_blockers_risk'],
                    'resolved_blockers_risk': metrics['resolved_blockers_risk'],
                    'critical_blockers_risk': metrics['critical_blockers_risk'],
                    'high_blockers_risk': metrics['high_blockers_risk'],
                    'medium_blockers_risk': metrics['medium_blockers_risk'],
                    'low_blockers_risk': metrics['low_blockers_risk'],
                    # Developer breakdown (task_type='Task' only)
                    'developer_breakdown': metrics['developer_breakdown'],
                    'tasks_with_dependencies': metrics['tasks_with_dependencies'],
                    # Timeline conflict insights
                    'timeline_conflicts': metrics.get('timeline_conflicts', []),
                    # Developer availability insights
                    'developer_availability_breakdown': metrics.get('developer_availability_breakdown', []),
                    # Task progress insights
                    'sprint_progress_breakdown': metrics.get('sprint_progress_breakdown', []),
                    'avg_completion_rate': metrics.get('avg_completion_rate', 1.0),
                    # Sprint completion level insights
                    'sprint_completion_breakdown': metrics.get('sprint_completion_breakdown', {}),
                    # Sprint metrics
                    'completed_sprints': metrics['completed_sprints'],
                    'total_sprints': metrics['total_sprints'],
                    'total_leave_hours': metrics['total_leave_hours'],
                    'total_sprint_hours': metrics['total_sprint_hours'],
                    # Project Budget metrics
                    'project_budget_limit': metrics.get('project_budget_limit', 0),
                    'total_logged_hours': metrics.get('total_logged_hours', 0),
                    # Available developers (low workload)
                    'available_developers_data': metrics.get('available_developers_data', {})
                },
                'calculated_at': datetime.now().isoformat()
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error calculating risk for project {project_id}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to calculate risk: {str(e)}"
            )

    async def _get_risk_parameters(self, tenant_name: str, project_id: int) -> Optional[Dict[str, Any]]:
        """Fetch risk parameters configuration for project from tenant database"""
        query = "SELECT * FROM tbl_risk_parameters_selection WHERE project_id = %s"
        
        result = await db.execute_query(
            query, 
            (project_id,), 
            fetch_one=True, 
            schema=tenant_name
        )
        return dict(result) if result else None

    async def _get_all_tasks(self, tenant_name: str, project_id: int) -> List[Dict[str, Any]]:
        """Fetch tasks (from active/closed sprints) and all bugs from project_backlog."""
        query = """
            -- Tasks: only from Active or Closed sprints
            SELECT pb.id AS task_id, pb.project_id, pb.sprint_id, pb.parent_task_id, pb.summary AS task_name,
                   pb.issue_type AS task_type, pb.priority, pb.status, pb.estimated_hours, pb.logged_hours,
                   pb.start_date, pb.end_date, pb.actual_start_date, pb.actual_end_date,
                   pb.assignee, pb.description, pb.story_points
            FROM project_backlog pb
            JOIN sprint s ON pb.sprint_id = s.sprint_id
            WHERE pb.project_id = %s
              AND LOWER(pb.issue_type) = 'task'
              AND s.sprint_status = 'Active'

            UNION ALL

            -- Bugs: all bugs for the project regardless of sprint assignment
            SELECT pb.id AS task_id, pb.project_id, pb.sprint_id, pb.parent_task_id, pb.summary AS task_name,
                   pb.issue_type AS task_type, pb.priority, pb.status, pb.estimated_hours, pb.logged_hours,
                   pb.start_date, pb.end_date, pb.actual_start_date, pb.actual_end_date,
                   pb.assignee, pb.description, pb.story_points
            FROM project_backlog pb
            WHERE pb.project_id = %s
              AND LOWER(pb.issue_type) = 'bug'
        """

        result = await db.execute_query(
            query,
            (project_id, project_id),
            fetch_all=True,
            schema=tenant_name
        )
        return [dict(row) for row in result] if result else []

    async def _get_project_budget(self, tenant_name: str, project_id: int) -> float:
        """Fetch project budget from projects table."""
        query = "SELECT budget FROM projects WHERE project_id = %s"
        result = await db.execute_query(query, (project_id,), fetch_one=True, schema=tenant_name)
        if result and result.get('budget'):
            return float(result['budget'])
        return 0.0

    async def _get_all_sprints(self, tenant_name: str, project_id: int) -> List[Dict[str, Any]]:
        """Fetch all sprints for the project from tenant database"""
        query = """
            SELECT sprint_id, project_id, sprint_name, sprint_status,
                   total_estimated_hours, total_completed_hours,
                   start_date, end_date
            FROM sprint
            WHERE project_id = %s AND sprint_status IN ('Active', 'Closed', 'Future')
        """
        
        result = await db.execute_query(
            query, 
            (project_id,), 
            fetch_all=True, 
            schema=tenant_name
        )
        return [dict(row) for row in result] if result else []

    async def _get_all_leaves(self, tenant_name: str, project_id: int) -> List[Dict[str, Any]]:
        """Fetch all sprint leaves for the project from tenant database"""
        query = """
            SELECT leave_id, sprint_id, project_id, developer_name,
                   leave_date, leave_hours, leave_type
            FROM sprint_leave
            WHERE project_id = %s
        """
        
        result = await db.execute_query(
            query, 
            (project_id,), 
            fetch_all=True, 
            schema=tenant_name
        )
        return [dict(row) for row in result] if result else []

    async def _get_all_blockers(self, tenant_name: str, project_id: int) -> List[Dict[str, Any]]:
        """Fetch all blockers for the project from tenant database"""
        query = """
            SELECT blocker_id, project_id, sprint_id, task_id,
                   blocker_title, blocker_type, severity, status,
                   reported_date, resolved_date
            FROM tbl_blocker
            WHERE project_id = %s
        """
        
        result = await db.execute_query(
            query, 
            (project_id,), 
            fetch_all=True, 
            schema=tenant_name
        )
        return [dict(row) for row in result] if result else []

    def _calculate_base_metrics(
        self,
        tasks_list: List[Dict[str, Any]],
        sprints_list: List[Dict[str, Any]],
        leaves_list: List[Dict[str, Any]],
        blockers_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate all base metrics from fetched data"""
        from datetime import date as date_type
        
        metrics = {
            'total_tasks': 0,
            'todo_tasks': 0,
            'inprogress_tasks': 0,
            'completed_tasks': 0,
            'blocked_tasks': 0,
            'uncompleted_tasks': 0,
            'tasks_with_dependencies': 0,
            # Task-only metrics (task_type = 'Task')
            'todo_tasks_only': 0,
            'inprogress_tasks_only': 0,
            'completed_tasks_only': 0,
            'overdue_tasks': 0,
            'max_overdue_days': 0,  # Track maximum days overdue
            # Bug metrics
            'total_bugs': 0,
            'critical_bugs': 0,
            'high_bugs': 0,
            'medium_bugs': 0,
            'low_bugs': 0,
            'weighted_bug_score': 0,
            'max_bug_score': 0,
            # Bug status metrics
            'todo_bugs': 0,
            'inprogress_bugs': 0,
            'completed_bugs': 0,
            # Blocker metrics (from tbl_blocker table)
            'total_blockers': 0,
            'open_blockers': 0,
            'inprogress_blockers': 0,
            'resolved_blockers': 0,
            'critical_blockers': 0,
            'high_blockers': 0,
            'medium_blockers': 0,
            'low_blockers': 0,
            'weighted_blocker_score': 0,
            'max_blocker_score': 0,
            # Sprint metrics
            'total_sprints': 0,
            'completed_sprints': 0,
            'total_sprint_hours': 0,
            'total_leave_hours': 0,
            'avg_completion_rate': 0.0,
            # Budget metrics
            'total_logged_hours': 0,
            'total_estimated_hours': 0
        }

        today = date_type.today()
        
        # Task metrics
        metrics['total_tasks'] = len(tasks_list)
        
        # Debug: Log first few tasks to see actual values
        if tasks_list:
            logger.info(f"🔍 DEBUG: Processing {len(tasks_list)} total items")
            for i, task in enumerate(tasks_list[:3]):  # Log first 3 tasks
                logger.info(f"  Task {i+1}: type='{task.get('task_type')}', status='{task.get('status')}', priority='{task.get('priority')}'")
        
        for task in tasks_list:
            status = (task.get('status') or '').strip()
            task_type = (task.get('task_type') or '').strip()
            priority = (task.get('priority') or '').strip()
            parent_task_id = task.get('parent_task_id')
            end_date = task.get('end_date')

            # Convert end_date string to date object if needed
            if isinstance(end_date, str):
                try:
                    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                except:
                    end_date = None

            # Normalize for case-insensitive comparison
            status_lower = status.lower()
            task_type_lower = task_type.lower()

            # Count by status (ALL items including bugs)
            if status_lower == 'todo':
                metrics['todo_tasks'] += 1
            elif status_lower == 'inprogress':
                metrics['inprogress_tasks'] += 1
            elif status_lower == 'done':
                metrics['completed_tasks'] += 1
            elif status_lower == 'blocked':
                metrics['blocked_tasks'] += 1

            # Count ONLY tasks (task_type = 'Task', excluding bugs)
            if task_type_lower == 'task':
                if status_lower == 'todo':
                    metrics['todo_tasks_only'] += 1
                    # Check if overdue
                    if end_date and end_date < today:
                        metrics['overdue_tasks'] += 1
                        days_overdue = (today - end_date).days
                        metrics['max_overdue_days'] = max(metrics['max_overdue_days'], days_overdue)
                elif status_lower == 'inprogress':
                    metrics['inprogress_tasks_only'] += 1
                    logger.info(f"✅ Found In Progress Task: {task.get('task_name', 'Unknown')}")
                    # Check if overdue
                    if end_date and end_date < today:
                        metrics['overdue_tasks'] += 1
                        days_overdue = (today - end_date).days
                        metrics['max_overdue_days'] = max(metrics['max_overdue_days'], days_overdue)
                elif status_lower == 'done':
                    metrics['completed_tasks_only'] += 1

            # Count dependencies
            if parent_task_id is not None:
                metrics['tasks_with_dependencies'] += 1

            # Bug metrics (case-insensitive, only count task_type='Bug')
            if task_type_lower == 'bug':
                metrics['total_bugs'] += 1
                priority_lower = priority.lower()
                if priority_lower == 'critical':
                    metrics['critical_bugs'] += 1
                elif priority_lower == 'high':
                    metrics['high_bugs'] += 1
                elif priority_lower == 'medium':
                    metrics['medium_bugs'] += 1
                elif priority_lower == 'low':
                    metrics['low_bugs'] += 1
                
                if status_lower == 'todo':
                    metrics['todo_bugs'] += 1
                elif status_lower == 'inprogress':
                    metrics['inprogress_bugs'] += 1
                elif status_lower == 'done':
                    metrics['completed_bugs'] += 1

            # Sum hours for budget risk
            metrics['total_logged_hours'] += (task.get('logged_hours') or 0)
            metrics['total_estimated_hours'] += (task.get('estimated_hours') or 0)

        metrics['uncompleted_tasks'] = metrics['todo_tasks'] + metrics['inprogress_tasks']

        # Calculate individual task risk percentages (for insights only)
        total_tasks_only = metrics['todo_tasks_only'] + metrics['inprogress_tasks_only'] + metrics['completed_tasks_only']
        
        if total_tasks_only > 0:
            # To-Do Risk: Based on proportion of uncompleted tasks that are not started
            metrics['todo_tasks_risk'] = round((metrics['todo_tasks_only'] / total_tasks_only) * 100, 2)
            
            # In-Progress Risk: Lower than to-do since work has begun (50% weight)
            metrics['inprogress_tasks_risk'] = round((metrics['inprogress_tasks_only'] / total_tasks_only) * 50, 2)
            
            # Overdue Risk: Highest risk - based on count and severity
            if metrics['overdue_tasks'] > 0:
                base_overdue_risk = (metrics['overdue_tasks'] / total_tasks_only) * 100
                # Add penalty for how overdue they are
                overdue_penalty = min(metrics['max_overdue_days'] * 3, 30)  # Up to 30% extra
                metrics['overdue_tasks_risk'] = round(min(base_overdue_risk + overdue_penalty, 100), 2)
            else:
                metrics['overdue_tasks_risk'] = 0.0
        else:
            metrics['todo_tasks_risk'] = 0.0
            metrics['inprogress_tasks_risk'] = 0.0
            metrics['overdue_tasks_risk'] = 0.0

        # Calculate individual bug risk percentages (for insights only)
        # Risk is based on UNCOMPLETED bugs only (To-Do and In-Progress)
        # Percentages sum to 100% for uncompleted bugs
        uncompleted_bugs = metrics['todo_bugs'] + metrics['inprogress_bugs']
        
        if uncompleted_bugs > 0:
            # To-Do Bugs Risk: Percentage of uncompleted bugs not started
            metrics['todo_bugs_risk'] = round((metrics['todo_bugs'] / uncompleted_bugs) * 100, 2)
            
            # In-Progress Bugs Risk: Percentage of uncompleted bugs in progress
            metrics['inprogress_bugs_risk'] = round((metrics['inprogress_bugs'] / uncompleted_bugs) * 100, 2)
        else:
            metrics['todo_bugs_risk'] = 0.0
            metrics['inprogress_bugs_risk'] = 0.0
        
        # High Priority Bugs Risk: Based on critical and high priority bugs out of total bugs
        if metrics['total_bugs'] > 0:
            high_priority_bug_count = metrics['critical_bugs'] + metrics['high_bugs']
            metrics['high_priority_bugs_risk'] = round((high_priority_bug_count / metrics['total_bugs']) * 100, 2)
        else:
            metrics['high_priority_bugs_risk'] = 0.0

        # Bug score calculation - weighted by priority
        metrics['weighted_bug_score'] = (
            (metrics['critical_bugs'] * self.CRITICAL_BUG_WEIGHT) +
            (metrics['high_bugs'] * self.HIGH_BUG_WEIGHT) +
            (metrics['medium_bugs'] * self.MEDIUM_BUG_WEIGHT) +
            (metrics['low_bugs'] * self.LOW_BUG_WEIGHT)
        )
        metrics['max_bug_score'] = (
            metrics['total_bugs'] * self.CRITICAL_BUG_WEIGHT
            if metrics['total_bugs'] > 0 else 1
        )

        # Sprint metrics
        metrics['total_sprints'] = len(sprints_list)
        completion_rates = []
        total_estimated = 0
        
        # Sprint breakdown for task progress insights
        sprint_progress_breakdown = []
        
        # Get today's date for comparison
        from datetime import date as date_type
        today = date_type.today()

        for sprint in sprints_list:
            sprint_status = (sprint.get('sprint_status') or '').strip()
            sprint_name = sprint.get('sprint_name') or f"Sprint {sprint.get('sprint_id', '?')}"
            estimated_hours = sprint.get('total_estimated_hours') or 0
            completed_hours = sprint.get('total_completed_hours') or 0
            start_date = sprint.get('start_date')

            if sprint_status == 'Closed':
                metrics['completed_sprints'] += 1

            if estimated_hours and estimated_hours > 0:
                total_estimated += estimated_hours
                rate = completed_hours / estimated_hours if estimated_hours > 0 else 0.0
                
                # Parse start date
                sprint_start_date = None
                if start_date:
                    if isinstance(start_date, str):
                        try:
                            sprint_start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                        except:
                            pass
                    elif hasattr(start_date, 'date'):
                        sprint_start_date = start_date.date() if callable(start_date.date) else start_date
                    else:
                        sprint_start_date = start_date
                
                # Determine if sprint should be counted in average
                should_count = False
                is_overdue = False
                
                if sprint_start_date:
                    if sprint_start_date <= today:
                        # Sprint start date has passed - should have started by now
                        should_count = True
                        
                        # Check if sprint never started (OVERDUE!)
                        if sprint_status.lower() == 'future':
                            is_overdue = True  # Sprint is overdue - count as 0% risk!
                        # else: Sprint is "In Progress" or "Completed" - count actual rate
                    # else: Future sprint (start_date > today) - don't count in average
                else:
                    # No start date available - count only if sprint has started
                    if sprint_status.lower() != 'future':
                        should_count = True
                
                if should_count:
                    completion_rates.append(rate)
                
                # Calculate overdue risk value
                overdue_risk_value = 0.0
                days_overdue = 0
                
                if is_overdue and sprint_start_date:
                    # Calculate how many days overdue
                    days_overdue = (today - sprint_start_date).days
                    
                    # Calculate risk: base 50% + 5% per day overdue (capped at 100%)
                    overdue_risk_value = min(50 + (days_overdue * 5), 100)
                
                # Add to sprint breakdown (include overdue flag and risk)
                completion_percentage = round(rate * 100, 1)
                sprint_progress_breakdown.append({
                    'sprint_name': sprint_name,
                    'sprint_status': sprint_status,
                    'estimated_hours': estimated_hours,
                    'completed_hours': completed_hours,
                    'completion_percentage': completion_percentage,
                    'is_overdue': is_overdue,
                    'days_overdue': days_overdue,
                    'overdue_risk_value': round(overdue_risk_value, 1)
                })

        metrics['total_sprint_hours'] = total_estimated if total_estimated > 0 else 0
        metrics['sprint_progress_breakdown'] = sprint_progress_breakdown

        # Sprint completion status breakdown
        sprint_completion_breakdown = {
            'completed': 0,
            'in_progress': 0,
            'to_do': 0,
            'completed_percentage': 0.0,
            'in_progress_percentage': 0.0,
            'to_do_percentage': 0.0,
            'completed_risk': 0.0,
            'in_progress_risk': 0.0,
            'to_do_risk': 0.0
        }
        
        # Track completion rates for each category
        in_progress_rates = []
        to_do_rates = []
        
        if metrics['total_sprints'] > 0:
            for sprint in sprints_list:
                status = (sprint.get('sprint_status') or '').strip().lower()
                estimated_hours = sprint.get('total_estimated_hours') or 0
                completed_hours = sprint.get('total_completed_hours') or 0
                
                if status == 'closed':
                    sprint_completion_breakdown['completed'] += 1
                elif status == 'active':
                    sprint_completion_breakdown['in_progress'] += 1
                    # Track actual completion rate for in-progress sprints
                    if estimated_hours > 0:
                        rate = completed_hours / estimated_hours
                        in_progress_rates.append(rate)
                else:
                    sprint_completion_breakdown['to_do'] += 1
                    # To-do sprints have 0 completion
                    to_do_rates.append(0.0)
            
            # Calculate percentages
            total = metrics['total_sprints']
            sprint_completion_breakdown['completed_percentage'] = round((sprint_completion_breakdown['completed'] / total) * 100, 1)
            sprint_completion_breakdown['in_progress_percentage'] = round((sprint_completion_breakdown['in_progress'] / total) * 100, 1)
            sprint_completion_breakdown['to_do_percentage'] = round((sprint_completion_breakdown['to_do'] / total) * 100, 1)
            
            # Calculate risk for each category
            # Completed sprints: 0% risk (they're done!)
            sprint_completion_breakdown['completed_risk'] = 0.0
            
            # In Progress sprints: Risk = 1 - avg_completion_rate
            if in_progress_rates:
                avg_in_progress = sum(in_progress_rates) / len(in_progress_rates)
                sprint_completion_breakdown['in_progress_risk'] = round((1 - avg_in_progress) * 100, 1)
            elif sprint_completion_breakdown['in_progress'] > 0:
                # If no hours data, assume 50% risk for in-progress
                sprint_completion_breakdown['in_progress_risk'] = 50.0
            
            # To Do sprints: 100% risk (not started)
            if sprint_completion_breakdown['to_do'] > 0:
                sprint_completion_breakdown['to_do_risk'] = 100.0
        
        metrics['sprint_completion_breakdown'] = sprint_completion_breakdown

        # Calculate average completion rate
        if completion_rates:
            metrics['avg_completion_rate'] = sum(completion_rates) / len(completion_rates)
        elif metrics['total_tasks'] > 0:
            # Fallback to task completion rate
            metrics['avg_completion_rate'] = metrics['completed_tasks'] / metrics['total_tasks']
        else:
            metrics['avg_completion_rate'] = 1.0  # Perfect if no data


        # Leave metrics - Developer-wise breakdown
        developer_leaves = {}
        for leave in leaves_list:
            leave_hours = leave.get('leave_hours') or 0
            developer_name = (leave.get('developer_name') or '').strip()
            
            if not developer_name or developer_name.lower() in ['null', 'none', '']:
                developer_name = 'Unassigned'
            
            if developer_name not in developer_leaves:
                developer_leaves[developer_name] = {
                    'total_leave_hours': 0,
                    'leave_count': 0
                }
            
            developer_leaves[developer_name]['total_leave_hours'] += leave_hours
            developer_leaves[developer_name]['leave_count'] += 1
            metrics['total_leave_hours'] += leave_hours
        
        # Calculate risk percentage for each developer
        developer_availability_breakdown = []
        if metrics['total_leave_hours'] > 0:
            for dev_name, dev_data in developer_leaves.items():
                # Calculate each developer's share of total leave (sums to 100%)
                risk_percentage = round((dev_data['total_leave_hours'] / metrics['total_leave_hours']) * 100, 1)
                developer_availability_breakdown.append({
                    'developer_name': dev_name,
                    'leave_hours': dev_data['total_leave_hours'],
                    'leave_count': dev_data['leave_count'],
                    'risk_percentage': risk_percentage
                })
            
            # Sort by risk percentage (highest first)
            developer_availability_breakdown.sort(key=lambda x: x['risk_percentage'], reverse=True)
        
        metrics['developer_availability_breakdown'] = developer_availability_breakdown

        # Blocker metrics (from tbl_blocker table)
        # Blocker severity weights (same as bug weights for consistency)
        CRITICAL_BLOCKER_WEIGHT = 3
        HIGH_BLOCKER_WEIGHT = 2
        MEDIUM_BLOCKER_WEIGHT = 1.5
        LOW_BLOCKER_WEIGHT = 1
        
        metrics['total_blockers'] = len(blockers_list)
        
        for blocker in blockers_list:
            severity = (blocker.get('severity') or '').strip()
            status = (blocker.get('status') or '').strip()
            
            # Normalize for case-insensitive comparison
            severity_lower = severity.lower()
            status_lower = status.lower()
            
            # Count by status
            if status_lower == 'open':
                metrics['open_blockers'] += 1
            elif status_lower == 'in progress':
                metrics['inprogress_blockers'] += 1
            elif status_lower == 'resolved':
                metrics['resolved_blockers'] += 1
            
            # Count by severity (only for open and in-progress blockers)
            if status_lower in ['open', 'in progress']:
                if severity_lower == 'critical':
                    metrics['critical_blockers'] += 1
                elif severity_lower == 'high':
                    metrics['high_blockers'] += 1
                elif severity_lower == 'medium':
                    metrics['medium_blockers'] += 1
                elif severity_lower == 'low':
                    metrics['low_blockers'] += 1
        
        # Calculate weighted blocker score (only unresolved blockers contribute to risk)
        metrics['weighted_blocker_score'] = (
            (metrics['critical_blockers'] * CRITICAL_BLOCKER_WEIGHT) +
            (metrics['high_blockers'] * HIGH_BLOCKER_WEIGHT) +
            (metrics['medium_blockers'] * MEDIUM_BLOCKER_WEIGHT) +
            (metrics['low_blockers'] * LOW_BLOCKER_WEIGHT)
        )
        
        # Calculate max possible blocker score (if all unresolved blockers were critical)
        unresolved_blockers = metrics['open_blockers'] + metrics['inprogress_blockers']
        metrics['max_blocker_score'] = (
            unresolved_blockers * CRITICAL_BLOCKER_WEIGHT
            if unresolved_blockers > 0 else 1
        )

        # Calculate individual blocker risk percentages (for insights display)
        # Status Breakdown - based on unresolved blockers (same method as bugs)
        if unresolved_blockers > 0:
            # Open Blockers Risk: Percentage of unresolved blockers not started
            metrics['open_blockers_risk'] = round((metrics['open_blockers'] / unresolved_blockers) * 100, 2)
            
            # In Progress Blockers Risk: Percentage of unresolved blockers being worked on
            metrics['inprogress_blockers_risk'] = round((metrics['inprogress_blockers'] / unresolved_blockers) * 100, 2)
        else:
            metrics['open_blockers_risk'] = 0.0
            metrics['inprogress_blockers_risk'] = 0.0
        
        # Resolved blockers always have 0% risk
        metrics['resolved_blockers_risk'] = 0.0
        
        # Severity Breakdown - based on total blockers
        if metrics['total_blockers'] > 0:
            metrics['critical_blockers_risk'] = round((metrics['critical_blockers'] / metrics['total_blockers']) * 100, 2)
            metrics['high_blockers_risk'] = round((metrics['high_blockers'] / metrics['total_blockers']) * 100, 2)
            metrics['medium_blockers_risk'] = round((metrics['medium_blockers'] / metrics['total_blockers']) * 100, 2)
            metrics['low_blockers_risk'] = round((metrics['low_blockers'] / metrics['total_blockers']) * 100, 2)
        else:
            metrics['critical_blockers_risk'] = 0.0
            metrics['high_blockers_risk'] = 0.0
            metrics['medium_blockers_risk'] = 0.0
            metrics['low_blockers_risk'] = 0.0


        # Developer-wise Task Breakdown (for Uncompleted Tasks insights)
        # ONLY count items where task_type = 'Task' (exclude Bugs)
        developer_tasks = {}
        unassigned_count = 0
        
        logger.info("🔍 DEBUG: Starting developer breakdown analysis...")
        
        for task in tasks_list:
            task_type = (task.get('task_type') or '').strip().lower()
            
            # ONLY process items with task_type = 'Task'
            if task_type != 'task':
                continue
            
            assignee = (task.get('assignee') or '').strip()
            status = (task.get('status') or '').strip().lower()
            
            logger.info(f"  📝 Task: type='{task_type}', assignee='{assignee}', status='{status}'")
            
            if not assignee or assignee.lower() in ['null', 'none', '']:
                logger.info(f"    ❌ Marking as unassigned (empty or null)")
                unassigned_count += 1
                continue
            
            logger.info(f"    ✅ Assigned to: {assignee}")
            
            if assignee not in developer_tasks:
                developer_tasks[assignee] = {
                    'total_tasks': 0,
                    'todo': 0,
                    'inprogress': 0,
                    'completed': 0,
                    'uncompleted': 0
                }
            
            developer_tasks[assignee]['total_tasks'] += 1
            
            if status == 'to do':
                developer_tasks[assignee]['todo'] += 1
                developer_tasks[assignee]['uncompleted'] += 1
            elif status == 'in progress':
                developer_tasks[assignee]['inprogress'] += 1
                developer_tasks[assignee]['uncompleted'] += 1
            elif status == 'completed':
                developer_tasks[assignee]['completed'] += 1
        
        # Calculate developer metrics and risks
        total_developers = len(developer_tasks)
        if total_developers > 0:
            total_project_tasks = metrics['todo_tasks_only'] + metrics['inprogress_tasks_only'] + metrics['completed_tasks_only']
            developer_breakdown = []
            
            for dev_name, dev_data in developer_tasks.items():
                workload_percentage = round((dev_data['total_tasks'] / total_project_tasks) * 100, 1) if total_project_tasks > 0 else 0
                dev_completion_rate = (dev_data['completed'] / dev_data['total_tasks'] * 100) if dev_data['total_tasks'] > 0 else 0
                dev_risk = round(100 - dev_completion_rate, 1)
                is_overloaded = workload_percentage > 20
                
                developer_breakdown.append({
                    'name': dev_name,
                    'total_tasks': dev_data['total_tasks'],
                    'todo': dev_data['todo'],
                    'inprogress': dev_data['inprogress'],
                    'completed': dev_data['completed'],
                    'uncompleted': dev_data['uncompleted'],
                    'workload_percentage': workload_percentage,
                    'risk_percentage': dev_risk,
                    'is_overloaded': is_overloaded
                })
            
            developer_breakdown.sort(key=lambda x: x['total_tasks'], reverse=True)
            avg_tasks_per_dev = round(total_project_tasks / total_developers, 1)
            
            metrics['developer_breakdown'] = {
                'total_developers': total_developers,
                'average_tasks_per_developer': avg_tasks_per_dev,
                'unassigned_tasks': unassigned_count,
                'developers': developer_breakdown
            }
        else:
            metrics['developer_breakdown'] = {
                'total_developers': 0,
                'average_tasks_per_developer': 0,
                'unassigned_tasks': unassigned_count,
                'developers': []
            }

        # Debug: Log final task counts
        logger.info(f"📊 TASK METRICS:")
        logger.info(f"  - To-Do Tasks (Task type only): {metrics['todo_tasks_only']}")
        logger.info(f"  - In-Progress Tasks (Task type only): {metrics['inprogress_tasks_only']}")
        logger.info(f"  - Completed Tasks (Task type only): {metrics['completed_tasks_only']}")
        logger.info(f"  - Overdue Tasks: {metrics['overdue_tasks']}")
        logger.info(f"  - Total Bugs: {metrics['total_bugs']}")
        logger.info(f"  - Total Blockers: {metrics['total_blockers']} (Open: {metrics['open_blockers']}, In Progress: {metrics['inprogress_blockers']}, Resolved: {metrics['resolved_blockers']})")

        return metrics

    def _calculate_uncompleted_tasks_risk(self, metrics: Dict[str, Any]) -> float:
        """Calculate uncompleted tasks risk score"""
        if metrics['total_tasks'] == 0:
            return 0.0
        risk = metrics['uncompleted_tasks'] / metrics['total_tasks']
        return max(0.0, min(1.0, risk))

    def _calculate_detected_bugs_risk(self, metrics: Dict[str, Any]) -> float:
        """Calculate detected bugs risk score"""
        max_score = metrics.get('max_bug_score', 0)
        if max_score == 0:
            return 0.0
        risk = metrics.get('weighted_bug_score', 0) / max_score
        return max(0.0, min(1.0, risk))

    def _calculate_blockers_count_risk(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate blockers count risk score using tbl_blocker table data.
        Uses weighted severity scores for more accurate risk assessment.
        """
        max_score = metrics.get('max_blocker_score', 0)
        if max_score == 0:
            return 0.0
        risk = metrics.get('weighted_blocker_score', 0) / max_score
        return max(0.0, min(1.0, risk))

    def _calculate_developer_workload_risk(self, metrics: Dict[str, Any]) -> float:
        """Calculate developer workload risk score"""
        if metrics['total_tasks'] == 0:
            return 0.0
        risk = metrics['uncompleted_tasks'] / metrics['total_tasks']
        return max(0.0, min(1.0, risk))

    def _calculate_task_dependency_risk(self, metrics: Dict[str, Any]) -> float:
        """Calculate task dependency risk score"""
        if metrics['total_tasks'] == 0:
            return 0.0
        risk = metrics['tasks_with_dependencies'] / metrics['total_tasks']
        return max(0.0, min(1.0, risk))

    def _calculate_timeline_conflict_risk(
        self,
        metrics: Dict[str, Any],
        tasks_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate timeline conflict risk score and return detailed conflict information.
        
        Returns:
            {
                'risk_score': float,  # 0.0 to 1.0
                'conflicts': [
                    {
                        'developer_name': str,
                        'task1_id': int,
                        'task1_name': str,
                        'task2_id': int,
                        'task2_name': str,
                        'overlap_start': str,  # ISO date
                        'overlap_end': str,    # ISO date
                        'risk_level': str      # 'LOW', 'MEDIUM', 'HIGH'
                    },
                    ...
                ]
            }
        """
        from datetime import date as date_type
        
        conflict_details = []
        
        if not tasks_list or len(tasks_list) == 0:
            return {'risk_score': 0.0, 'conflicts': []}
        
        total_conflicts = 0
        total_checkable_tasks = 0
        
        # 1. Check for overlapping tasks per developer
        developer_tasks = {}
        tasks_by_id = {}  # Helper to look up task details
        
        for task in tasks_list:
            status = (task.get('status') or '').strip().lower()
            if status == 'completed':
                continue  # Skip completed tasks
                
            assignee = (task.get('assignee') or '').strip()
            if not assignee or assignee.lower() in ['null', 'none', '']:
                continue
                
            start_date = task.get('start_date') or task.get('actual_start_date')
            end_date = task.get('end_date')
            
            # Convert dates if needed
            if isinstance(start_date, str):
                try:
                    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                except:
                    start_date = None
            if isinstance(end_date, str):
                try:
                    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                except:
                    end_date = None
            
            if not start_date or not end_date:
                continue
                
            task_id = task.get('task_id')
            tasks_by_id[task_id] = {
                'task_id': task_id,
                'task_name': task.get('task_name', 'Unnamed Task'),
                'start': start_date,
                'end': end_date,
                'priority': task.get('priority', 'Medium'),
                'sprint_id': task.get('sprint_id'),
                'assignee': assignee
            }
            
            if assignee not in developer_tasks:
                developer_tasks[assignee] = []
            
            developer_tasks[assignee].append(tasks_by_id[task_id])
            total_checkable_tasks += 1
        
        # Check for overlaps within each developer's tasks
        for dev_name, dev_task_list in developer_tasks.items():
            for i in range(len(dev_task_list)):
                for j in range(i + 1, len(dev_task_list)):
                    task_a = dev_task_list[i]
                    task_b = dev_task_list[j]
                    
                    # Check if date ranges overlap
                    if task_a['start'] <= task_b['end'] and task_b['start'] <= task_a['end']:
                        total_conflicts += 1
                        
                        # Calculate overlap period
                        overlap_start = max(task_a['start'], task_b['start'])
                        overlap_end = min(task_a['end'], task_b['end'])
                        overlap_days = (overlap_end - overlap_start).days + 1
                        
                        # Calculate risk value (0-100%)
                        # Base risk on overlap days (max 14 days = 70%)
                        base_risk = min((overlap_days / 14.0) * 70, 70)
                        
                        # Add priority weight (0-30%)
                        priorities = [task_a['priority'].lower(), task_b['priority'].lower()]
                        priority_weight = 0
                        if 'critical' in priorities:
                            priority_weight = 30
                        elif 'high' in priorities:
                            priority_weight = 20
                        elif 'medium' in priorities:
                            priority_weight = 10
                        
                        risk_value = round(min(base_risk + priority_weight, 100), 1)
                        
                        # Determine risk level based on risk_value
                        if risk_value >= 70:
                            risk_level = 'HIGH'
                        elif risk_value >= 40:
                            risk_level = 'MEDIUM'
                        else:
                            risk_level = 'LOW'
                        
                        conflict_details.append({
                            'developer_name': dev_name,
                            'task1_id': task_a['task_id'],
                            'task1_name': task_a['task_name'],
                            'task1_priority': task_a['priority'],
                            'task2_id': task_b['task_id'],
                            'task2_name': task_b['task_name'],
                            'task2_priority': task_b['priority'],
                            'overlap_start': overlap_start.isoformat(),
                            'overlap_end': overlap_end.isoformat(),
                            'overlap_days': overlap_days,
                            'risk_value': risk_value,
                            'risk_level': risk_level
                        })
        
        # 2. Check for sprint capacity overload
        sprint_tasks = {}
        for task in tasks_list:
            status = (task.get('status') or '').strip().lower()
            if status == 'completed':
                continue
                
            sprint_id = task.get('sprint_id')
            if not sprint_id:
                continue
                
            if sprint_id not in sprint_tasks:
                sprint_tasks[sprint_id] = {
                    'task_count': 0,
                    'story_points': 0
                }
            
            sprint_tasks[sprint_id]['task_count'] += 1
            story_points = task.get('story_points', 0) or 0
            sprint_tasks[sprint_id]['story_points'] += story_points
        
        # Flag sprints with excessive work (>15 tasks or >40 story points)
        for sprint_id, sprint_data in sprint_tasks.items():
            if sprint_data['task_count'] > 15 or sprint_data['story_points'] > 40:
                total_conflicts += 1
        
        # 3. Check for multiple high-priority tasks starting on same date
        high_priority_starts = {}
        for task in tasks_list:
            status = (task.get('status') or '').strip().lower()
            if status == 'completed':
                continue
                
            priority = (task.get('priority') or '').strip().lower()
            if priority not in ['high', 'critical']:
                continue
                
            start_date = task.get('start_date') or task.get('actual_start_date')
            if isinstance(start_date, str):
                try:
                    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                except:
                    continue
            
            if not start_date:
                continue
                
            date_key = start_date.isoformat()
            if date_key not in high_priority_starts:
                high_priority_starts[date_key] = 0
            high_priority_starts[date_key] += 1
        
        # Flag dates with multiple high-priority tasks starting
        for date_key, count in high_priority_starts.items():
            if count > 2:  # More than 2 high-priority tasks on same day
                total_conflicts += 1
        
        # Calculate risk score
        if total_checkable_tasks == 0:
            risk_score = 0.0
        else:
            # Normalize conflicts relative to number of tasks
            risk_score = total_conflicts / max(total_checkable_tasks, 1)
            risk_score = max(0.0, min(1.0, risk_score))
        
        return {
            'risk_score': risk_score,
            'conflicts': conflict_details
        }


    def _calculate_developer_availability_risk(self, metrics: Dict[str, Any]) -> float:
        """Calculate developer availability risk score"""
        if metrics['total_sprint_hours'] == 0:
            return 0.0
        risk = metrics['total_leave_hours'] / metrics['total_sprint_hours']
        return max(0.0, min(1.0, risk))  # Clamp to 1.0

    def _calculate_task_progress_risk(self, metrics: Dict[str, Any]) -> float:
        """Calculate task progress risk score"""
        risk = 1 - metrics['avg_completion_rate']
        return max(0.0, min(1.0, risk))

    def _calculate_sprint_completion_risk(self, metrics: Dict[str, Any]) -> float:
        """Calculate sprint completion level risk score"""
        if metrics['total_sprints'] == 0:
            return 0.0
        completion_rate = metrics['completed_sprints'] / metrics['total_sprints']
        risk = 1 - completion_rate
        return max(0.0, min(1.0, risk))

    def _calculate_project_budget_risk(self, metrics: Dict[str, Any]) -> float:
        """Calculate project budget risk score based on spending vs budget"""
        budget = metrics.get('project_budget_limit', 0)
        if budget == 0:
            return 0.0
            
        # Assume an average hourly rate for budget calculation if not provided
        # Or just use hours ratio if budget is in hours (but here budget is usually money)
        hourly_rate = 50.0 # Default fallback
        estimated_spend = metrics['total_logged_hours'] * hourly_rate
        
        risk = estimated_spend / budget
        return max(0.0, min(1.0, risk))

    def _calculate_available_developers(
        self,
        tasks_list: List[Dict[str, Any]],
        sprints_list: List[Dict[str, Any]],
        leaves_list: List[Dict[str, Any]],
        project_id: int
    ) -> Dict[str, Any]:
        """
        Calculate available developers (low workload) in active sprints.
        
        Identifies developers with:
        - Utilization below threshold (< 40%)
        - No task assignments (0% utilization)
        
        Returns:
            Dictionary with available developers and sprint capacity info
        """
        from datetime import date as date_type
        
        UTILIZATION_THRESHOLD = 40  # Percentage - developers below this are "available"
        HOURS_PER_WEEK = 40  # Standard work hours per week
        
        # Find active sprints (In Progress)
        active_sprints = [
            sprint for sprint in sprints_list 
            if (sprint.get('sprint_status') or '').strip().lower() == 'active'
        ]
        
        if not active_sprints:
            # No active sprint - return empty result
            return {
                'available_developers': [],
                'threshold_percentage': UTILIZATION_THRESHOLD,
                'total_developers': 0,
                'available_count': 0,
                'has_active_sprint': False,
                'sprint_info': None
            }
        
        # Use the first active sprint (typically there's only one active sprint)
        current_sprint = active_sprints[0]
        sprint_id = current_sprint.get('sprint_id')
        sprint_name = current_sprint.get('sprint_name', f'Sprint {sprint_id}')
        
        # Calculate sprint duration and capacity
        start_date = current_sprint.get('start_date')
        end_date = current_sprint.get('end_date')
        
        # Parse dates
        if isinstance(start_date, str):
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            except:
                start_date = None
        elif hasattr(start_date, 'date'):
            start_date = start_date.date() if callable(start_date.date) else start_date
        
        if isinstance(end_date, str):
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except:
                end_date = None
        elif hasattr(end_date, 'date'):
            end_date = end_date.date() if callable(end_date.date) else end_date
        
        # Calculate sprint capacity per developer
        sprint_capacity_per_dev = HOURS_PER_WEEK * 2  # Default 2 weeks = 80 hours
        if start_date and end_date:
            duration_days = (end_date - start_date).days
            sprint_weeks = duration_days / 7
            sprint_capacity_per_dev = HOURS_PER_WEEK * sprint_weeks
        
        # Get tasks for current sprint only
        sprint_tasks = [
            task for task in tasks_list 
            if task.get('sprint_id') == sprint_id
        ]
        
        # Calculate workload per developer
        developer_workload = {}
        all_sprint_developers = set()  # Track all developers in the sprint
        
        for task in sprint_tasks:
            task_type = (task.get('task_type') or '').strip().lower()
            assignee = (task.get('assignee') or '').strip()
            status = (task.get('status') or '').strip().lower()
            
            # Skip unassigned tasks
            if not assignee or assignee.lower() in ['null', 'none', '']:
                continue
            
            all_sprint_developers.add(assignee)
            
            # Initialize developer if not exists
            if assignee not in developer_workload:
                developer_workload[assignee] = {
                    'name': assignee,
                    'total_tasks': 0,
                    'uncompleted_tasks': 0,
                    'completed_tasks': 0,
                    'story_points': 0,
                    'estimated_hours': 0,
                    'logged_hours': 0,
                    'leave_hours': 0
                }
            
            # Count tasks (all types)
            developer_workload[assignee]['total_tasks'] += 1
            
            if status in ['to do', 'in progress', 'in review', 'blocked']:
                developer_workload[assignee]['uncompleted_tasks'] += 1
            elif status == 'completed':
                developer_workload[assignee]['completed_tasks'] += 1
            
            # Sum story points and hours
            story_points = task.get('story_points') or 0
            estimated_hours = task.get('estimated_hours') or 0
            logged_hours = task.get('logged_hours') or 0
            
            developer_workload[assignee]['story_points'] += story_points
            developer_workload[assignee]['estimated_hours'] += estimated_hours
            developer_workload[assignee]['logged_hours'] += logged_hours
        
        # Add leave hours per developer
        for leave in leaves_list:
            if leave.get('sprint_id') != sprint_id:
                continue
            
            developer_name = (leave.get('developer_name') or '').strip()
            leave_hours = leave.get('leave_hours') or 0
            
            if not developer_name or developer_name.lower() in ['null', 'none', '']:
                continue
            
            all_sprint_developers.add(developer_name)
            
            if developer_name not in developer_workload:
                developer_workload[developer_name] = {
                    'name': developer_name,
                    'total_tasks': 0,
                    'uncompleted_tasks': 0,
                    'completed_tasks': 0,
                    'story_points': 0,
                    'estimated_hours': 0,
                    'logged_hours': 0,
                    'leave_hours': 0
                }
            
            developer_workload[developer_name]['leave_hours'] += leave_hours
        
        # Calculate utilization and identify available developers
        available_developers = []
        total_capacity_hours = 0
        used_capacity_hours = 0
        
        for dev_name, dev_data in developer_workload.items():
            # Calculate available capacity (after leave)
            available_capacity = sprint_capacity_per_dev - dev_data['leave_hours']
            
            # Calculate utilization based on estimated hours
            if available_capacity > 0:
                utilization_percentage = round((dev_data['estimated_hours'] / available_capacity) * 100, 1)
            else:
                utilization_percentage = 100.0  # All time is leave
            
            # Calculate remaining capacity
            remaining_capacity_hours = max(0, available_capacity - dev_data['estimated_hours'])
            
            # Track total capacity
            total_capacity_hours += available_capacity
            used_capacity_hours += dev_data['estimated_hours']
            
            # Identify if developer is available (below threshold or unassigned)
            # IMPORTANT: Don't mark as available if they have uncompleted tasks, even if no estimated hours
            has_uncompleted_work = dev_data['uncompleted_tasks'] > 0
            
            if utilization_percentage < UTILIZATION_THRESHOLD and not has_uncompleted_work:
                # Determine capacity status
                if utilization_percentage == 0:
                    capacity_status = 'Completely Available'
                elif utilization_percentage < 20:
                    capacity_status = 'Mostly Available'
                else:
                    capacity_status = 'Partially Available'
                
                available_developers.append({
                    'name': dev_name,
                    'utilization_percentage': utilization_percentage,
                    'capacity_status': capacity_status,
                    'total_tasks': dev_data['total_tasks'],
                    'uncompleted_tasks': dev_data['uncompleted_tasks'],
                    'completed_tasks': dev_data['completed_tasks'],
                    'story_points': dev_data['story_points'],
                    'estimated_hours': dev_data['estimated_hours'],
                    'remaining_capacity_hours': round(remaining_capacity_hours, 1),
                    'total_capacity_hours': round(available_capacity, 1),
                    'leave_hours': dev_data['leave_hours']
                })
        
        # Sort by utilization (lowest first - most available)
        available_developers.sort(key=lambda x: x['utilization_percentage'])
        
        # Calculate sprint-level capacity metrics
        sprint_utilization = 0
        if total_capacity_hours > 0:
            sprint_utilization = round((used_capacity_hours / total_capacity_hours) * 100, 1)
        
        return {
            'available_developers': available_developers,
            'threshold_percentage': UTILIZATION_THRESHOLD,
            'total_developers': len(developer_workload),
            'available_count': len(available_developers),
            'has_active_sprint': True,
            'sprint_info': {
                'sprint_id': sprint_id,
                'sprint_name': sprint_name,
                'total_capacity_hours': round(total_capacity_hours, 1),
                'used_capacity_hours': round(used_capacity_hours, 1),
                'available_capacity_hours': round(total_capacity_hours - used_capacity_hours, 1),
                'sprint_utilization_percentage': sprint_utilization
            }
        }

    def _determine_risk_level(self, risk_score: float) -> str:
        """Determine risk level from score"""
        if risk_score < 0.25:
            return "LOW"
        elif risk_score < 0.50:
            return "MEDIUM"
        elif risk_score < 0.75:
            return "HIGH"
        else:
            return "CRITICAL"

    def _calculate_risk_from_metrics(self, metrics: Dict[str, Any], params_config: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates risk breakdown and total score from metrics and configuration"""
        breakdown = []
        total_weight = 0
        weighted_sum = 0.0

        parameters = [
            ('uncompleted_tasks', self._calculate_uncompleted_tasks_risk),
            ('detected_bugs', self._calculate_detected_bugs_risk),
            ('blockers_count', self._calculate_blockers_count_risk),
            ('task_dependency', self._calculate_task_dependency_risk),
            ('timeline_conflict', lambda m: self._calculate_timeline_conflict_risk(m, [])['risk_score']), # Dummy tasks_list for hypothetical
            ('developer_availability', self._calculate_developer_availability_risk),
            ('task_progress', self._calculate_task_progress_risk),
            ('sprint_completion_level', self._calculate_sprint_completion_risk),
            ('project_budget', self._calculate_project_budget_risk)
        ]

        # Use actual timeline conflict risk from metrics if available
        if 'timeline_conflict_score' in metrics:
            parameters[4] = ('timeline_conflict', (lambda m: m['timeline_conflict_score']))
        elif 'timeline_conflicts' in metrics:
             # If we have conflict details, we can use them
             pass

        for param_name, calc_func in parameters:
            enabled = params_config.get(param_name, False)
            weight = params_config.get(f'{param_name}_weight', 0)
            
            if enabled and weight > 0:
                risk_score = calc_func(metrics)
                weighted_value = risk_score * weight
                breakdown.append({
                    'parameter': param_name,
                    'enabled': True,
                    'risk_score': round(risk_score, 4),
                    'weight': weight,
                    'weighted_value': round(weighted_value, 4),
                    'contribution': 0.0
                })
                total_weight += weight
                weighted_sum += weighted_value
            else:
                breakdown.append({
                    'parameter': param_name,
                    'enabled': False,
                    'risk_score': None,
                    'weight': weight,
                    'weighted_value': None,
                    'contribution': None
                })

        total_risk_score = 0.0
        if total_weight > 0:
            total_risk_score = weighted_sum / total_weight
            total_risk_score = max(0.0, min(1.0, total_risk_score))

            for item in breakdown:
                if item['enabled']:
                    item['contribution'] = round(item['weighted_value'] / total_weight, 4)

        return {
            'total_risk_score': total_risk_score,
            'total_weight': total_weight,
            'breakdown': breakdown
        }

    def calculate_hypothetical_impact(
        self, 
        current_metrics: Dict[str, Any], 
        params_config: Dict[str, Any], 
        param_to_improve: str, 
        improvement_amount: float = 1.0
    ) -> float:
        """
        Calculates the potential reduction in total risk score.
        
        Args:
            current_metrics: Current project metrics
            params_config: Risk parameter weights/enabled status
            param_to_improve: The parameter being addressed (e.g., 'detected_bugs')
            improvement_amount: Amount of improvement (e.g., 1.0 for one bug/task)
            
        Returns:
            The potential reduction in risk percentage (0-100)
        """
        # 1. Calculate current total risk
        current_result = self._calculate_risk_from_metrics(current_metrics, params_config)
        current_percentage = current_result['total_risk_score'] * 100
        
        # 2. Clone metrics for hypothetical scenario
        hypothetical_metrics = copy.deepcopy(current_metrics)
        
        # 3. Apply improvement based on type
        if param_to_improve == 'detected_bugs':
            # Reduce bugs starting from highest priority
            if hypothetical_metrics.get('critical_bugs', 0) > 0:
                hypothetical_metrics['critical_bugs'] = max(0, hypothetical_metrics['critical_bugs'] - improvement_amount)
            elif hypothetical_metrics.get('high_bugs', 0) > 0:
                hypothetical_metrics['high_bugs'] = max(0, hypothetical_metrics['high_bugs'] - improvement_amount)
            elif hypothetical_metrics.get('medium_bugs', 0) > 0:
                hypothetical_metrics['medium_bugs'] = max(0, hypothetical_metrics['medium_bugs'] - improvement_amount)
            else:
                hypothetical_metrics['low_bugs'] = max(0, hypothetical_metrics['low_bugs'] - improvement_amount)
            
            # Re-calculate weighted bug score
            hypothetical_metrics['weighted_bug_score'] = (
                (hypothetical_metrics.get('critical_bugs', 0) * self.CRITICAL_BUG_WEIGHT) +
                (hypothetical_metrics.get('high_bugs', 0) * self.HIGH_BUG_WEIGHT) +
                (hypothetical_metrics.get('medium_bugs', 0) * self.MEDIUM_BUG_WEIGHT) +
                (hypothetical_metrics.get('low_bugs', 0) * self.LOW_BUG_WEIGHT)
            )
            
        elif param_to_improve == 'uncompleted_tasks':
            hypothetical_metrics['uncompleted_tasks'] = max(0, hypothetical_metrics.get('uncompleted_tasks', 0) - improvement_amount)
            hypothetical_metrics['completed_tasks'] = hypothetical_metrics.get('completed_tasks', 0) + improvement_amount
            
        elif param_to_improve == 'blockers_count':
            # Use same logic as bugs for priority if available, otherwise just count
            unresolved = hypothetical_metrics.get('open_blockers', 0) + hypothetical_metrics.get('inprogress_blockers', 0)
            if unresolved > 0:
                if hypothetical_metrics.get('critical_blockers', 0) > 0:
                    hypothetical_metrics['critical_blockers'] = max(0, hypothetical_metrics['critical_blockers'] - improvement_amount)
                elif hypothetical_metrics.get('high_blockers', 0) > 0:
                    hypothetical_metrics['high_blockers'] = max(0, hypothetical_metrics['high_blockers'] - improvement_amount)
                
                # Re-calculate weighted blocker score
                hypothetical_metrics['weighted_blocker_score'] = (
                    (hypothetical_metrics.get('critical_blockers', 0) * 3) +
                    (hypothetical_metrics.get('high_blockers', 0) * 2) +
                    (hypothetical_metrics.get('medium_blockers', 0) * 1.5) +
                    (hypothetical_metrics.get('low_blockers', 0) * 1)
                )

        elif param_to_improve == 'task_dependency':
            hypothetical_metrics['tasks_with_dependencies'] = max(0, hypothetical_metrics.get('tasks_with_dependencies', 0) - improvement_amount)

        elif param_to_improve == 'timeline_conflict':
            # Timeline conflict score is 0.0 to 1.0. Reducing it by the improvement amount (clamped)
            # Typically 1.0 improvement here means resolving ALL conflicts
            hypothetical_metrics['timeline_conflict_score'] = max(0.0, hypothetical_metrics.get('timeline_conflict_score', 0.0) - improvement_amount)

        elif param_to_improve == 'developer_availability':
            # Reduce leave hours. improvement_amount 1.0 = 8 hours (1 day)
            hours_per_unit = 8.0 
            hypothetical_metrics['total_leave_hours'] = max(0.0, hypothetical_metrics.get('total_leave_hours', 0.0) - (improvement_amount * hours_per_unit))

        elif param_to_improve == 'task_progress':
            # Improve avg_completion_rate. 1.0 improvement = +10% rate
            rate_improvement = improvement_amount * 0.1
            hypothetical_metrics['avg_completion_rate'] = min(1.0, hypothetical_metrics.get('avg_completion_rate', 0.0) + rate_improvement)

        elif param_to_improve == 'sprint_completion_level':
            # Increase completed sprints
            hypothetical_metrics['completed_sprints'] = hypothetical_metrics.get('completed_sprints', 0) + improvement_amount
            if hypothetical_metrics['completed_sprints'] > hypothetical_metrics.get('total_sprints', 0):
                hypothetical_metrics['total_sprints'] = hypothetical_metrics['completed_sprints']

        elif param_to_improve == 'developer_workload':
            # Developer workload risk in this service uses uncompleted tasks metrics
            hypothetical_metrics['uncompleted_tasks'] = max(0, hypothetical_metrics.get('uncompleted_tasks', 0) - improvement_amount)
            hypothetical_metrics['completed_tasks'] = hypothetical_metrics.get('completed_tasks', 0) + improvement_amount

        elif param_to_improve == 'project_budget':
            # Budget risk improvement: reduce logged hours or increase budget limit
            # Here we simulate reducing spending (logged hours)
            hours_per_unit = 10.0 # Simulate reducing 10 hours for 1 improvement unit
            hypothetical_metrics['total_logged_hours'] = max(0.0, hypothetical_metrics.get('total_logged_hours', 0.0) - (improvement_amount * hours_per_unit))

        # 4. Calculate hypothetical risk
        hypothetical_result = self._calculate_risk_from_metrics(hypothetical_metrics, params_config)
        hypothetical_percentage = hypothetical_result['total_risk_score'] * 100
        
        # 5. Return the delta
        reduction = max(0.0, current_percentage - hypothetical_percentage)
        return round(reduction, 2)
