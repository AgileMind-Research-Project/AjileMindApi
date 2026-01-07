"""
Agile Project Delay Analysis Service

Implements sprint-based delay calculation algorithm for Agile projects.
Compares planned sprint schedule vs actual completion to forecast project delays.

Algorithm Steps:
1. Calculate project duration
2. Calculate planned total sprints (using project sprint_size)
3. Calculate expected sprints by current date
4. Count actual completed sprints
5. Calculate sprint delay (expected vs actual)
6. Convert sprint delay to days
7. Calculate developer availability factor (from leave hours)
8. Adjust delay using availability
9. Calculate delay percentage
10. Determine delay risk level

Formula:
- Planned Total Sprints = (end_date - start_date) / sprint_size
- Expected Sprints by Now = (current_date - start_date) / sprint_size
- Sprint Delay = Expected Sprints by Now - Completed Sprints
- Delay Days = Sprint Delay × sprint_size × (1 / availability_ratio)
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal
import logging

from app.db.database import db

logger = logging.getLogger(__name__)


class DelayCalculationService:
    """Service for calculating project delays using Agile metrics"""
    
    # Risk level thresholds
    RISK_THRESHOLDS = {
        'LOW': 0.10,      # < 10% delay
        'MEDIUM': 0.25,   # < 25% delay
        'HIGH': 0.40,     # < 40% delay
        'CRITICAL': 1.0   # >= 40% delay
    }
    
    # Minimum availability ratio to prevent division errors
    MIN_AVAILABILITY_RATIO = 0.1
    
    def __init__(self, database):
        """
        Initialize delay calculation service
        
        Args:
            database: Database instance for querying project data
        """
        self.db = database
    
    async def calculate_project_delay(
        self, 
        project_id: int, 
        tenant_db: str
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive project delay analysis
        
        Args:
            project_id: ID of the project to analyze
            tenant_db: Tenant database name
            
        Returns:
            Dictionary containing delay analysis results
        """
        try:
            # Fetch project data
            project_data = await self._fetch_project_data(project_id, tenant_db)
            
            if not project_data:
                raise ValueError(f"Project {project_id} not found")
            
            # Fetch sprint data
            sprint_data = await self._fetch_sprint_data(project_id, tenant_db)
            
            if not sprint_data or len(sprint_data) == 0:
                # No sprints yet - return zero delay
                return self._generate_no_sprint_response(project_data)
            
            # Fetch task data for story points
            task_data = await self._fetch_task_data(project_id, tenant_db)
            
            # Calculate delay using the algorithm
            delay_result = self._calculate_delay_algorithm(
                project_data=project_data,
                sprint_data=sprint_data,
                task_data=task_data
            )
            
            return delay_result
            
        except Exception as e:
            logger.error(f"Error calculating delay for project {project_id}: {str(e)}")
            raise
    
    async def _fetch_project_data(self, project_id: int, tenant_db: str) -> Optional[Dict]:
        """Fetch project information from database"""
        query = """
            SELECT 
                project_id,
                project_name,
                `key`,
                start_date,
                end_date,
                sprint_size
            FROM projects
            WHERE project_id = %s
        """
        
        result = await db.execute_query(query, (project_id,), fetch_one=True, schema=tenant_db)
        return dict(result) if result else None
    
    async def _fetch_sprint_data(self, project_id: int, tenant_db: str) -> List[Dict]:
        """Fetch sprint data with leave information"""
        query = """
            SELECT 
                s.sprint_id,
                s.sprint_name,
                s.start_date,
                s.end_date,
                s.sprint_status,
                s.total_estimated_hours,
                s.total_completed_hours,
                COALESCE(SUM(sl.leave_hours), 0) as total_leave_hours
            FROM sprint s
            LEFT JOIN sprint_leave sl ON s.sprint_id = sl.sprint_id
            WHERE s.project_id = %s
            GROUP BY s.sprint_id, s.sprint_name, s.start_date, s.end_date, 
                     s.sprint_status, s.total_estimated_hours, s.total_completed_hours
            ORDER BY s.start_date ASC
        """
        
        results = await db.execute_query(query, (project_id,), fetch_all=True, schema=tenant_db)
        return [dict(row) for row in results] if results else []
    
    async def _fetch_task_data(self, project_id: int, tenant_db: str) -> List[Dict]:
        """Fetch task data for story point calculation"""
        query = """
            SELECT 
                task_id,
                sprint_id,
                task_name,
                status,
                story_points,
                estimated_hours,
                logged_hours
            FROM task
            WHERE project_id = %s
        """
        
        results = await db.execute_query(query, (project_id,), fetch_all=True, schema=tenant_db)
        return [dict(row) for row in results] if results else []
    
    def _generate_no_sprint_response(self, project_data: Dict) -> Dict[str, Any]:
        """Generate response when no sprints exist"""
        current_date = datetime.now().date()
        sprint_size_weeks = project_data.get('sprint_size') or 2
        sprint_size_days = sprint_size_weeks * 7
        project_duration_days = (project_data['end_date'] - project_data['start_date']).days
        return {
            'project_id': project_data['project_id'],
            'project_name': project_data['project_name'],
            'project_key': project_data['key'],
            
            # Dates
            'project_start_date': project_data['start_date'].isoformat(),
            'planned_end_date': project_data['end_date'].isoformat(),
            'current_date': current_date.isoformat(),
            'forecasted_end_date': project_data['end_date'].isoformat(),
            
            # Sprint configuration
            'sprint_size_weeks': sprint_size_weeks,
            'sprint_size_days': sprint_size_days,
            
            # Sprint delay metrics
            'planned_total_sprints': 0.0,
            'expected_sprints_by_now': 0.0,
            'completed_sprints': 0,
            'sprint_delay': 0.0,
            
            # Delay metrics
            'delay_days': 0.0,
            'delay_percentage': 0.0,
            'risk_level': 'LOW',
            
            # Project metrics
            'project_duration_days': project_duration_days,
            'days_elapsed': 0,
            
            # Story points
            'total_story_points': 0,
            'completed_story_points': 0,
            'remaining_story_points': 0,
            'story_point_completion_rate': 0.0,
            
            # Velocity
            'expected_velocity': 0.0,
            'actual_velocity': 0.0,
            'velocity_variance': 0.0,
            
            # Availability
            'total_planned_hours': 0,
            'total_leave_hours': 0,
            'availability_ratio': 1.0,
            
            # Sprint breakdown
            'sprint_breakdown': [],
            'message': 'No sprints found for this project'
        }
    
    def _calculate_delay_algorithm(
        self,
        project_data: Dict,
        sprint_data: List[Dict],
        task_data: List[Dict]
    ) -> Dict[str, Any]:
        """
        Execute the sprint delay calculation algorithm based on planned vs actual sprint completion
        
        Algorithm:
        1. Calculate planned total sprints from project duration and sprint_size
        2. Calculate expected sprints to be completed by current date
        3. Count actual completed sprints
        4. Calculate sprint delay = expected sprints - completed sprints
        5. Convert sprint delay to days
        6. Account for developer availability (leave hours)
        7. Calculate delay percentage and risk level
        
        Args:
            project_data: Project information including sprint_size
            sprint_data: List of sprints with leave data
            task_data: List of tasks with story points
            
        Returns:
            Comprehensive delay analysis
        """
        
        # Extract dates
        start_date = project_data['start_date']
        end_date = project_data['end_date']
        current_date = datetime.now().date()
        
        # Get sprint size from project (in weeks)
        sprint_size_weeks = project_data.get('sprint_size') or 2  # Default to 2 weeks
        sprint_size_days = sprint_size_weeks * 7
        
        # STEP 1: Calculate Project Duration
        project_duration_days = (end_date - start_date).days
        
        # STEP 2: Calculate Planned Total Sprints
        # Formula: (end_date - start_date) / sprint_size
        if sprint_size_days > 0:
            planned_total_sprints = project_duration_days / sprint_size_days
        else:
            planned_total_sprints = 0
        
        # STEP 3: Calculate Expected Sprints by Current Date
        # Formula: (current_date - start_date) / sprint_size
        days_elapsed = max(0, (current_date - start_date).days)
        
        if sprint_size_days > 0:
            expected_sprints_by_now = days_elapsed / sprint_size_days
        else:
            expected_sprints_by_now = 0
        
        # Ensure we don't expect more sprints than planned
        expected_sprints_by_now = min(expected_sprints_by_now, planned_total_sprints)
        
        # STEP 4: Count Actual Completed Sprints
        completed_sprints = len([
            s for s in sprint_data 
            if s['sprint_status'] in ['Completed', 'Closed']
        ])
        
        # STEP 5: Calculate Sprint Delay
        # Delay = Expected sprints by now - Actual completed sprints
        sprint_delay = expected_sprints_by_now - completed_sprints
        
        # Only consider positive delays
        if sprint_delay < 0:
            sprint_delay = 0
        
        # STEP 6: Convert Sprint Delay to Days
        delay_days_raw = sprint_delay * sprint_size_days
        
        # STEP 7: Calculate Developer Availability Factor
        # Aggregate sprint-wise leave hours and planned hours
        total_leave_hours = sum([sprint.get('total_leave_hours', 0) or 0 for sprint in sprint_data])
        total_planned_hours = sum([sprint.get('total_estimated_hours', 0) or 0 for sprint in sprint_data])
        
        if total_planned_hours > 0:
            availability_ratio = 1 - (total_leave_hours / total_planned_hours)
        else:
            availability_ratio = 1.0
        
        # Clamp availability ratio to minimum threshold
        if availability_ratio < self.MIN_AVAILABILITY_RATIO:
            availability_ratio = self.MIN_AVAILABILITY_RATIO
        
        # STEP 8: Adjust Delay Using Availability
        # If availability is low, delay increases
        adjusted_delay_days = delay_days_raw / availability_ratio
        
        # STEP 9: Calculate Delay Percentage
        if project_duration_days > 0:
            delay_percentage = adjusted_delay_days / project_duration_days
        else:
            delay_percentage = 0.0
        
        # Clamp to 100%
        if delay_percentage > 1.0:
            delay_percentage = 1.0
        
        # STEP 10: Determine Delay Risk Level
        risk_level = self._determine_risk_level(delay_percentage)
        
        # Calculate forecasted end date
        forecasted_end_date = end_date + timedelta(days=int(adjusted_delay_days))
        
        # Calculate story points for metrics
        total_story_points = sum([task.get('story_points', 0) or 0 for task in task_data])
        completed_story_points = sum([
            task.get('story_points', 0) or 0 
            for task in task_data 
            if task['status'] == 'Completed'
        ])
        remaining_story_points = total_story_points - completed_story_points
        
        # Calculate story point completion rate
        if total_story_points > 0:
            story_point_completion_rate = completed_story_points / total_story_points
        else:
            story_point_completion_rate = 0.0
        
        # Calculate velocities
        if planned_total_sprints > 0:
            expected_velocity = total_story_points / planned_total_sprints
        else:
            expected_velocity = 0.0
        
        if completed_sprints > 0:
            actual_velocity = completed_story_points / completed_sprints
        else:
            actual_velocity = 0.0
        
        # Generate sprint breakdown
        sprint_breakdown = self._generate_sprint_breakdown(sprint_data, task_data)
        
        # Return comprehensive results
        return {
            'project_id': project_data['project_id'],
            'project_name': project_data['project_name'],
            'project_key': project_data['key'],
            
            # Dates
            'project_start_date': start_date.isoformat(),
            'planned_end_date': end_date.isoformat(),
            'current_date': current_date.isoformat(),
            'forecasted_end_date': forecasted_end_date.isoformat(),
            
            # Delay metrics (primary calculation)
            'sprint_size_weeks': sprint_size_weeks,
            'sprint_size_days': sprint_size_days,
            'planned_total_sprints': round(planned_total_sprints, 2),
            'expected_sprints_by_now': round(expected_sprints_by_now, 2),
            'completed_sprints': completed_sprints,
            'sprint_delay': round(sprint_delay, 2),
            'delay_days': round(adjusted_delay_days, 2),
            'delay_percentage': round(delay_percentage * 100, 2),  # Convert to percentage
            'risk_level': risk_level,
            
            # Project metrics
            'project_duration_days': project_duration_days,
            'days_elapsed': days_elapsed,
            
            # Story points
            'total_story_points': total_story_points,
            'completed_story_points': completed_story_points,
            'remaining_story_points': remaining_story_points,
            'story_point_completion_rate': round(story_point_completion_rate * 100, 2),
            
            # Velocity
            'expected_velocity': round(expected_velocity, 2),
            'actual_velocity': round(actual_velocity, 2),
            'velocity_variance': round(actual_velocity - expected_velocity, 2),
            
            # Availability
            'total_planned_hours': total_planned_hours,
            'total_leave_hours': total_leave_hours,
            'availability_ratio': round(availability_ratio, 4),
            
            # Sprint breakdown
            'sprint_breakdown': sprint_breakdown
        }
    
    def _determine_risk_level(self, delay_percentage: float) -> str:
        """
        Determine risk level based on delay percentage
        
        Args:
            delay_percentage: Delay as percentage (0.0 to 1.0)
            
        Returns:
            Risk level: LOW, MEDIUM, HIGH, or CRITICAL
        """
        if delay_percentage < self.RISK_THRESHOLDS['LOW']:
            return 'LOW'
        elif delay_percentage < self.RISK_THRESHOLDS['MEDIUM']:
            return 'MEDIUM'
        elif delay_percentage < self.RISK_THRESHOLDS['HIGH']:
            return 'HIGH'
        else:
            return 'CRITICAL'
    
    def _generate_sprint_breakdown(
        self, 
        sprint_data: List[Dict], 
        task_data: List[Dict]
    ) -> List[Dict]:
        """
        Generate sprint-by-sprint breakdown showing contribution to delay
        
        Args:
            sprint_data: List of sprint information
            task_data: List of task information
            
        Returns:
            List of sprint breakdown dictionaries
        """
        breakdown = []
        
        for sprint in sprint_data:
            sprint_id = sprint['sprint_id']
            
            # Calculate story points for this sprint
            sprint_tasks = [t for t in task_data if t.get('sprint_id') == sprint_id]
            planned_story_points = sum([t.get('story_points', 0) or 0 for t in sprint_tasks])
            completed_story_points = sum([
                t.get('story_points', 0) or 0 
                for t in sprint_tasks 
                if t['status'] == 'Completed'
            ])
            
            # Calculate velocity for this sprint
            if planned_story_points > 0:
                sprint_velocity = completed_story_points
                completion_rate = (completed_story_points / planned_story_points) * 100
            else:
                sprint_velocity = 0
                completion_rate = 0.0
            
            # Calculate availability impact
            total_hours = sprint.get('total_estimated_hours', 0) or 0
            leave_hours = sprint.get('total_leave_hours', 0) or 0
            
            if total_hours > 0:
                availability = ((total_hours - leave_hours) / total_hours) * 100
            else:
                availability = 100.0
            
            breakdown.append({
                'sprint_id': sprint_id,
                'sprint_name': sprint['sprint_name'],
                'start_date': sprint['start_date'].isoformat(),
                'end_date': sprint['end_date'].isoformat(),
                'status': sprint['sprint_status'],
                'planned_story_points': planned_story_points,
                'completed_story_points': completed_story_points,
                'completion_rate': round(completion_rate, 2),
                'velocity': sprint_velocity,
                'total_hours': total_hours,
                'leave_hours': leave_hours,
                'availability': round(availability, 2)
            })
        
        return breakdown
