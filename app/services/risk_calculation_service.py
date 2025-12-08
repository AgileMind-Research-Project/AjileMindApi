"""
Risk Calculation Service

Calculates project risk scores based on selected parameters and weights.
"""

from typing import Dict, List, Any, Optional
from datetime import date, datetime
import aiomysql
from app.db.database import db
from app.core.logger import logger
from fastapi import HTTPException


class RiskCalculationService:
    """Service for calculating project risk scores"""

    # Bug priority weights
    CRITICAL_BUG_WEIGHT = 3
    MEDIUM_BUG_WEIGHT = 2
    LOW_BUG_WEIGHT = 1

    async def calculate_project_risk(self, project_id: int) -> Dict[str, Any]:
        """
        Calculate total risk score for a project.
        
        Args:
            project_id: Project ID to calculate risk for
            
        Returns:
            Dictionary containing total risk score, breakdown, and metadata
        """
        try:
            # Step 1: Fetch risk parameters configuration
            params_config = await self._get_risk_parameters(project_id)
            if not params_config:
                raise HTTPException(
                    status_code=404,
                    detail=f"Risk parameters not found for project {project_id}. Please configure risk parameters first."
                )

            # Step 2: Fetch all project data
            tasks_list = await self._get_all_tasks(project_id)
            sprints_list = await self._get_all_sprints(project_id)
            leaves_list = await self._get_all_leaves(project_id)

            # Step 3: Calculate base metrics
            metrics = self._calculate_base_metrics(tasks_list, sprints_list, leaves_list)

            # Step 4: Calculate individual risk scores
            breakdown = []
            total_weight = 0
            weighted_sum = 0.0

            # Check each parameter and calculate if enabled
            if params_config.get('uncompleted_tasks'):
                risk_score = self._calculate_uncompleted_tasks_risk(metrics)
                weight = params_config.get('uncompleted_tasks_weight', 0)
                if weight > 0:
                    weighted_value = risk_score * weight
                    breakdown.append({
                        'parameter': 'uncompleted_tasks',
                        'enabled': True,
                        'risk_score': round(risk_score, 4),
                        'weight': weight,
                        'weighted_value': round(weighted_value, 4),
                        'contribution': 0.0
                    })
                    total_weight += weight
                    weighted_sum += weighted_value

            if params_config.get('detected_bugs'):
                risk_score = self._calculate_detected_bugs_risk(metrics)
                weight = params_config.get('detected_bugs_weight', 0)
                if weight > 0:
                    weighted_value = risk_score * weight
                    breakdown.append({
                        'parameter': 'detected_bugs',
                        'enabled': True,
                        'risk_score': round(risk_score, 4),
                        'weight': weight,
                        'weighted_value': round(weighted_value, 4),
                        'contribution': 0.0
                    })
                    total_weight += weight
                    weighted_sum += weighted_value

            if params_config.get('blockers_count'):
                risk_score = self._calculate_blockers_count_risk(metrics)
                weight = params_config.get('blockers_count_weight', 0)
                if weight > 0:
                    weighted_value = risk_score * weight
                    breakdown.append({
                        'parameter': 'blockers_count',
                        'enabled': True,
                        'risk_score': round(risk_score, 4),
                        'weight': weight,
                        'weighted_value': round(weighted_value, 4),
                        'contribution': 0.0
                    })
                    total_weight += weight
                    weighted_sum += weighted_value

            if params_config.get('developer_workload'):
                risk_score = self._calculate_developer_workload_risk(metrics)
                weight = params_config.get('developer_workload_weight', 0)
                if weight > 0:
                    weighted_value = risk_score * weight
                    breakdown.append({
                        'parameter': 'developer_workload',
                        'enabled': True,
                        'risk_score': round(risk_score, 4),
                        'weight': weight,
                        'weighted_value': round(weighted_value, 4),
                        'contribution': 0.0
                    })
                    total_weight += weight
                    weighted_sum += weighted_value

            if params_config.get('task_dependency'):
                risk_score = self._calculate_task_dependency_risk(metrics)
                weight = params_config.get('task_dependency_weight', 0)
                if weight > 0:
                    weighted_value = risk_score * weight
                    breakdown.append({
                        'parameter': 'task_dependency',
                        'enabled': True,
                        'risk_score': round(risk_score, 4),
                        'weight': weight,
                        'weighted_value': round(weighted_value, 4),
                        'contribution': 0.0
                    })
                    total_weight += weight
                    weighted_sum += weighted_value

            if params_config.get('timeline_conflict'):
                risk_score = self._calculate_timeline_conflict_risk(metrics, tasks_list)
                weight = params_config.get('timeline_conflict_weight', 0)
                if weight > 0:
                    weighted_value = risk_score * weight
                    breakdown.append({
                        'parameter': 'timeline_conflict',
                        'enabled': True,
                        'risk_score': round(risk_score, 4),
                        'weight': weight,
                        'weighted_value': round(weighted_value, 4),
                        'contribution': 0.0
                    })
                    total_weight += weight
                    weighted_sum += weighted_value

            if params_config.get('developer_availability'):
                risk_score = self._calculate_developer_availability_risk(metrics)
                weight = params_config.get('developer_availability_weight', 0)
                if weight > 0:
                    weighted_value = risk_score * weight
                    breakdown.append({
                        'parameter': 'developer_availability',
                        'enabled': True,
                        'risk_score': round(risk_score, 4),
                        'weight': weight,
                        'weighted_value': round(weighted_value, 4),
                        'contribution': 0.0
                    })
                    total_weight += weight
                    weighted_sum += weighted_value

            if params_config.get('task_progress'):
                risk_score = self._calculate_task_progress_risk(metrics)
                weight = params_config.get('task_progress_weight', 0)
                if weight > 0:
                    weighted_value = risk_score * weight
                    breakdown.append({
                        'parameter': 'task_progress',
                        'enabled': True,
                        'risk_score': round(risk_score, 4),
                        'weight': weight,
                        'weighted_value': round(weighted_value, 4),
                        'contribution': 0.0
                    })
                    total_weight += weight
                    weighted_sum += weighted_value

            if params_config.get('sprint_completion_level'):
                risk_score = self._calculate_sprint_completion_risk(metrics)
                weight = params_config.get('sprint_completion_level_weight', 0)
                if weight > 0:
                    weighted_value = risk_score * weight
                    breakdown.append({
                        'parameter': 'sprint_completion_level',
                        'enabled': True,
                        'risk_score': round(risk_score, 4),
                        'weight': weight,
                        'weighted_value': round(weighted_value, 4),
                        'contribution': 0.0
                    })
                    total_weight += weight
                    weighted_sum += weighted_value

            # Add disabled parameters to breakdown
            all_parameters = [
                'uncompleted_tasks', 'detected_bugs', 'blockers_count',
                'developer_workload', 'task_dependency', 'timeline_conflict',
                'developer_availability', 'task_progress', 'sprint_completion_level'
            ]
            enabled_params = [p['parameter'] for p in breakdown if p['enabled']]
            for param in all_parameters:
                if param not in enabled_params:
                    breakdown.append({
                        'parameter': param,
                        'enabled': False,
                        'risk_score': None,
                        'weight': params_config.get(f'{param}_weight', 0),
                        'weighted_value': None,
                        'contribution': None
                    })

            # Check if any parameters are enabled
            if total_weight == 0:
                raise HTTPException(
                    status_code=400,
                    detail="No risk parameters are enabled or have non-zero weights. Please configure risk parameters."
                )

            # Step 5: Calculate total risk score (normalized weighted average)
            total_risk_score = weighted_sum / total_weight
            total_risk_score = max(0.0, min(1.0, total_risk_score))  # Clamp to 0-1

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
                    'total_bugs': metrics['total_bugs'],
                    'completed_sprints': metrics['completed_sprints'],
                    'total_sprints': metrics['total_sprints'],
                    'total_leave_hours': metrics['total_leave_hours'],
                    'total_sprint_hours': metrics['total_sprint_hours']
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

    async def _get_risk_parameters(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Fetch risk parameters configuration for project"""
        query = "SELECT * FROM tbl_risk_parameters_selection WHERE project_id = %s"
        
        async with db.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, (project_id,))
                result = await cur.fetchone()
                return dict(result) if result else None

    async def _get_all_tasks(self, project_id: int) -> List[Dict[str, Any]]:
        """Fetch all tasks for the project"""
        query = """
            SELECT task_id, project_id, sprint_id, parent_task_id, task_name,
                   task_type, priority, status, estimated_hours, logged_hours,
                   start_date, end_date, actual_start_date, actual_end_date
            FROM task
            WHERE project_id = %s
        """
        
        async with db.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, (project_id,))
                results = await cur.fetchall()
                return [dict(row) for row in results] if results else []

    async def _get_all_sprints(self, project_id: int) -> List[Dict[str, Any]]:
        """Fetch all sprints for the project"""
        query = """
            SELECT sprint_id, project_id, sprint_name, sprint_status,
                   total_estimated_hours, total_completed_hours,
                   start_date, end_date
            FROM sprint
            WHERE project_id = %s
        """
        
        async with db.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, (project_id,))
                results = await cur.fetchall()
                return [dict(row) for row in results] if results else []

    async def _get_all_leaves(self, project_id: int) -> List[Dict[str, Any]]:
        """Fetch all sprint leaves for the project"""
        query = """
            SELECT leave_id, sprint_id, project_id, developer_name,
                   leave_date, leave_hours, leave_type
            FROM sprint_leave
            WHERE project_id = %s
        """
        
        async with db.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, (project_id,))
                results = await cur.fetchall()
                return [dict(row) for row in results] if results else []

    def _calculate_base_metrics(
        self,
        tasks_list: List[Dict[str, Any]],
        sprints_list: List[Dict[str, Any]],
        leaves_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate all base metrics from fetched data"""
        
        metrics = {
            'total_tasks': 0,
            'todo_tasks': 0,
            'inprogress_tasks': 0,
            'completed_tasks': 0,
            'blocked_tasks': 0,
            'uncompleted_tasks': 0,
            'tasks_with_dependencies': 0,
            'total_bugs': 0,
            'critical_bugs': 0,
            'medium_bugs': 0,
            'low_bugs': 0,
            'weighted_bug_score': 0,
            'max_bug_score': 0,
            'total_sprints': 0,
            'completed_sprints': 0,
            'total_sprint_hours': 0,
            'total_leave_hours': 0,
            'avg_completion_rate': 0.0
        }

        # Task metrics
        metrics['total_tasks'] = len(tasks_list)
        
        for task in tasks_list:
            status = (task.get('status') or '').strip()
            task_type = (task.get('task_type') or '').strip()
            priority = (task.get('priority') or '').strip()
            parent_task_id = task.get('parent_task_id')

            # Count by status
            if status == 'To Do':
                metrics['todo_tasks'] += 1
            elif status == 'In Progress':
                metrics['inprogress_tasks'] += 1
            elif status == 'Completed':
                metrics['completed_tasks'] += 1
            elif status == 'Blocked':
                metrics['blocked_tasks'] += 1

            # Count dependencies
            if parent_task_id is not None:
                metrics['tasks_with_dependencies'] += 1

            # Bug metrics
            if task_type == 'Bug':
                metrics['total_bugs'] += 1
                if priority == 'Critical':
                    metrics['critical_bugs'] += 1
                elif priority == 'High':
                    metrics['medium_bugs'] += 1
                elif priority in ['Medium', 'Low']:
                    metrics['low_bugs'] += 1

        metrics['uncompleted_tasks'] = metrics['todo_tasks'] + metrics['inprogress_tasks']

        # Bug score calculation
        metrics['weighted_bug_score'] = (
            (metrics['critical_bugs'] * self.CRITICAL_BUG_WEIGHT) +
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

        for sprint in sprints_list:
            sprint_status = (sprint.get('sprint_status') or '').strip()
            estimated_hours = sprint.get('total_estimated_hours') or 0
            completed_hours = sprint.get('total_completed_hours') or 0

            if sprint_status == 'Completed':
                metrics['completed_sprints'] += 1

            if estimated_hours and estimated_hours > 0:
                total_estimated += estimated_hours
                rate = completed_hours / estimated_hours if estimated_hours > 0 else 0.0
                completion_rates.append(rate)

        metrics['total_sprint_hours'] = total_estimated if total_estimated > 0 else 0

        # Calculate average completion rate
        if completion_rates:
            metrics['avg_completion_rate'] = sum(completion_rates) / len(completion_rates)
        elif metrics['total_tasks'] > 0:
            # Fallback to task completion rate
            metrics['avg_completion_rate'] = metrics['completed_tasks'] / metrics['total_tasks']
        else:
            metrics['avg_completion_rate'] = 1.0  # Perfect if no data

        # Leave metrics
        for leave in leaves_list:
            leave_hours = leave.get('leave_hours') or 0
            metrics['total_leave_hours'] += leave_hours

        return metrics

    def _calculate_uncompleted_tasks_risk(self, metrics: Dict[str, Any]) -> float:
        """Calculate uncompleted tasks risk score"""
        if metrics['total_tasks'] == 0:
            return 0.0
        risk = metrics['uncompleted_tasks'] / metrics['total_tasks']
        return max(0.0, min(1.0, risk))

    def _calculate_detected_bugs_risk(self, metrics: Dict[str, Any]) -> float:
        """Calculate detected bugs risk score"""
        if metrics['max_bug_score'] == 0:
            return 0.0
        risk = metrics['weighted_bug_score'] / metrics['max_bug_score']
        return max(0.0, min(1.0, risk))

    def _calculate_blockers_count_risk(self, metrics: Dict[str, Any]) -> float:
        """Calculate blockers count risk score"""
        if metrics['total_tasks'] == 0:
            return 0.0
        risk = metrics['blocked_tasks'] / metrics['total_tasks']
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
    ) -> float:
        """Calculate timeline conflict risk score"""
        from datetime import date as date_type
        
        if metrics['total_tasks'] == 0:
            return 0.0

        today = date_type.today()
        overdue_count = 0

        for task in tasks_list:
            status = (task.get('status') or '').strip()
            end_date = task.get('end_date')
            actual_end_date = task.get('actual_end_date')

            # Convert date strings to date objects if needed
            if isinstance(end_date, str):
                try:
                    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                except:
                    end_date = None

            if isinstance(actual_end_date, str):
                try:
                    actual_end_date = datetime.strptime(actual_end_date, '%Y-%m-%d').date()
                except:
                    actual_end_date = None

            # Check if task is overdue
            is_overdue = False
            if status != 'Completed':
                if end_date and end_date < today:
                    is_overdue = True
            else:
                if actual_end_date and end_date and actual_end_date > end_date:
                    is_overdue = True

            if is_overdue:
                overdue_count += 1

        risk = overdue_count / metrics['total_tasks']
        return max(0.0, min(1.0, risk))

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

