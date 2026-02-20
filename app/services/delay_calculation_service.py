"""
Enhanced Agile Project Delay Analysis Service

Implements velocity-based forecasting with developer availability adjustment.
Provides confidence-based predictions, trend analysis, and delay attribution.

Core Algorithm (14 Steps):
1. Calculate average velocity from completed sprints
2. Estimate remaining sprints needed
3. Forecast total required sprints
4. Calculate sprint delay
5. Convert sprint delay to calendar days
6. Adjust delay using availability ratio
7. Forecast actual end date
8. Calculate delay percentage
9. Classify risk level

Enhanced Features:
✅ 1. Confidence-Based Forecasting (Best/Most Likely/Worst Case)
✅ 2. Velocity Trend Analysis (Acceleration/Deceleration Detection)
✅ 3. Scope Change Detection (Scope Creep Measurement)
✅ 4. Delay Attribution Breakdown (Root Cause Analysis)
✅ 5. Early Warning System (Rule-Based Alerts)

Formula:
- AVG_VELOCITY = Completed Story Points / Completed Sprints
- REMAINING_SPRINTS = Remaining Story Points / AVG_VELOCITY
- FORECASTED_TOTAL_SPRINTS = Completed Sprints + REMAINING_SPRINTS
- SPRINT_DELAY = FORECASTED_TOTAL_SPRINTS - Planned Total Sprints
- ADJUSTED_DELAY_DAYS = (SPRINT_DELAY × Sprint Days) / AVAILABILITY_RATIO
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
    
    # Enhanced Feature Thresholds
    VELOCITY_DROP_THRESHOLD = 0.20  # 20% velocity drop triggers warning
    SCOPE_CHANGE_THRESHOLD = 0.15   # 15% scope increase triggers warning
    LOW_AVAILABILITY_THRESHOLD = 0.70  # <70% availability triggers warning
    LOW_COMPLETION_THRESHOLD = 0.70    # <70% sprint completion triggers warning
    CONSECUTIVE_SPRINTS_FOR_TREND = 2  # Number of consecutive sprints for trend detection
    RECENT_SPRINTS_FOR_CONFIDENCE = 3  # Number of recent sprints for confidence intervals
    
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
        Execute the ENHANCED velocity-based delay calculation algorithm
        
        Core Algorithm (9 Steps):
        1. Calculate average velocity from completed sprints
        2. Estimate remaining sprints needed
        3. Forecast total required sprints
        4. Calculate sprint delay
        5. Convert sprint delay to calendar days
        6. Adjust delay using availability ratio
        7. Forecast actual end date
        8. Calculate delay percentage
        9. Classify risk level
        
        Enhanced Features:
        ✅ 1. Confidence-Based Forecasting (Best/Most Likely/Worst Case)
        ✅ 2. Velocity Trend Analysis (Acceleration/Deceleration Detection)
        ✅ 3. Scope Change Detection (Scope Creep Measurement)
        ✅ 4. Delay Attribution Breakdown (Root Cause Analysis)
        ✅ 5. Early Warning System (Rule-Based Alerts)
        
        Args:
            project_data: Project information including sprint_size
            sprint_data: List of sprints with leave data
            task_data: List of tasks with story points
            
        Returns:
            Comprehensive delay analysis with enhanced metrics
        """
        
        # Extract dates
        start_date = project_data['start_date']
        end_date = project_data['end_date']
        current_date = datetime.now().date()
        
        # Get sprint size from project (in weeks)
        sprint_size_weeks = project_data.get('sprint_size') or 2  # Default to 2 weeks
        sprint_size_days = sprint_size_weeks * 7
        
        # Calculate Project Duration
        project_duration_days = (end_date - start_date).days
        days_elapsed = max(0, (current_date - start_date).days)
        
        # Calculate Planned Total Sprints
        if sprint_size_days > 0:
            planned_total_sprints = project_duration_days / sprint_size_days
        else:
            planned_total_sprints = 0
        
        # Count Completed Sprints
        completed_sprints_list = [
            s for s in sprint_data 
            if s['sprint_status'] in ['Completed', 'Closed']
        ]
        completed_sprints = len(completed_sprints_list)
        
        # Calculate Story Points
        total_story_points = sum([task.get('story_points', 0) or 0 for task in task_data])
        completed_story_points = sum([
            task.get('story_points', 0) or 0 
            for task in task_data 
            if task['status'] == 'Completed'
        ])
        remaining_story_points = total_story_points - completed_story_points
        
        # Story point completion rate
        if total_story_points > 0:
            story_point_completion_rate = completed_story_points / total_story_points
        else:
            story_point_completion_rate = 0.0
        
        # ========================================
        # STEP 1: Calculate Average Velocity
        # ========================================
        if completed_sprints > 0:
            avg_velocity = completed_story_points / completed_sprints
        else:
            avg_velocity = 0.0
        
        # ========================================
        # CRITICAL EDGE CASE: No Completed Sprints
        # ========================================
        # If project has started but no sprints completed, we need special handling
        # This is a red flag - time is passing but no progress is being made
        if completed_sprints == 0 and days_elapsed > 0:
            # Calculate how many sprints SHOULD have been completed by now
            expected_sprints_by_now = days_elapsed / sprint_size_days if sprint_size_days > 0 else 0
            
            # If we're past the first sprint and still nothing completed, this is a problem
            if expected_sprints_by_now >= 1.0:
                # Estimate velocity based on total story points and planned sprints
                # This is our best guess in absence of actual data
                estimated_velocity = total_story_points / planned_total_sprints if planned_total_sprints > 0 else 0
                
                if estimated_velocity > 0:
                    # Calculate delay based on expected progress
                    expected_completed_sp = expected_sprints_by_now * estimated_velocity
                    actual_completed_sp = completed_story_points  # Should be 0 or very low
                    missing_sp = expected_completed_sp - actual_completed_sp
                    
                    # This missing work translates to delay
                    missing_sprints = missing_sp / estimated_velocity if estimated_velocity > 0 else expected_sprints_by_now
                    delay_days_from_no_progress = missing_sprints * sprint_size_days
                    
                    # Calculate delay percentage
                    delay_percentage_no_progress = (delay_days_from_no_progress / project_duration_days) * 100 if project_duration_days > 0 else 0
                    
                    # Classify risk
                    if delay_percentage_no_progress >= 40:
                        risk_level = 'CRITICAL'
                    elif delay_percentage_no_progress >= 25:
                        risk_level = 'HIGH'
                    elif delay_percentage_no_progress >= 10:
                        risk_level = 'MEDIUM'
                    else:
                        risk_level = 'LOW'
                    
                    # Generate sprint breakdown even with no completed sprints
                    sprint_breakdown = self._generate_sprint_breakdown(sprint_data, task_data)
                    
                    # Return early with special message
                    return {
                        'project_id': project_data['project_id'],
                        'project_name': project_data['project_name'],
                        'project_key': project_data['key'],
                        'project_start_date': start_date.isoformat(),
                        'planned_end_date': end_date.isoformat(),
                        'current_date': current_date.isoformat(),
                        'forecasted_end_date': (end_date + timedelta(days=int(delay_days_from_no_progress))).isoformat(),
                        'sprint_size_weeks': sprint_size_weeks,
                        'sprint_size_days': sprint_size_days,
                        'planned_total_sprints': planned_total_sprints,
                        'completed_sprints': 0,
                        'forecasted_remaining_sprints': planned_total_sprints + missing_sprints,
                        'forecasted_total_sprints': planned_total_sprints + missing_sprints,
                        'sprint_delay': missing_sprints,
                        'delay_days': delay_days_from_no_progress,
                        'delay_percentage': delay_percentage_no_progress,
                        'risk_level': risk_level,
                        'project_duration_days': project_duration_days,
                        'days_elapsed': days_elapsed,
                        'total_story_points': total_story_points,
                        'completed_story_points': completed_story_points,
                        'remaining_story_points': remaining_story_points,
                        'story_point_completion_rate': story_point_completion_rate,
                        'expected_velocity': estimated_velocity,
                        'actual_velocity': 0.0,
                        'velocity_variance': -100.0,  # 100% below expected
                        'total_planned_hours': sum([s.get('total_hours', 0) or 0 for s in sprint_data]),
                        'total_leave_hours': sum([s.get('leave_hours', 0) or 0 for s in sprint_data]),
                        'availability_ratio': 1.0,
                        'confidence_forecasts': {
                            'best_case_end_date': end_date.isoformat(),
                            'most_likely_end_date': (end_date + timedelta(days=int(delay_days_from_no_progress))).isoformat(),
                            'worst_case_end_date': (end_date + timedelta(days=int(delay_days_from_no_progress * 1.5))).isoformat(),
                            'best_case_velocity': estimated_velocity,
                            'most_likely_velocity': estimated_velocity * 0.7,
                            'worst_case_velocity': estimated_velocity * 0.5,
                            'confidence_range_days': int(delay_days_from_no_progress * 0.5)
                        },
                        'velocity_trend': {
                            'trend_direction': 'DECELERATING',
                            'trend_value': -estimated_velocity,
                            'recent_avg_velocity': 0.0,
                            'overall_avg_velocity': estimated_velocity,
                            'is_improving': False,
                            'is_declining': True
                        },
                        'scope_analysis': {
                            'original_planned_story_points': total_story_points,
                            'current_total_story_points': total_story_points,
                            'scope_change_story_points': 0.0,
                            'scope_change_ratio': 0.0,
                            'scope_change_percentage': 0.0,
                            'has_scope_creep': False
                        },
                        'delay_attribution': {
                            'velocity_impact_days': delay_days_from_no_progress,
                            'availability_impact_days': 0.0,
                            'scope_impact_days': 0.0,
                            'velocity_impact_percentage': 100.0,
                            'availability_impact_percentage': 0.0,
                            'scope_impact_percentage': 0.0,
                            'primary_cause': 'LOW_VELOCITY'
                        },
                        'early_warnings': [
                            {
                                'type': 'NO_COMPLETED_SPRINTS',
                                'severity': 'CRITICAL',
                                'message': f'Project started {days_elapsed} days ago but has 0 completed sprints. Expected {expected_sprints_by_now:.1f} sprints to be completed by now.',
                                'recommendation': 'URGENT: Investigate why no sprints have been completed. Check team capacity, blockers, and sprint planning process. Consider project restart or immediate intervention.'
                            },
                            {
                                'type': 'ZERO_VELOCITY',
                                'severity': 'CRITICAL',
                                'message': 'Team velocity is 0 - no story points have been completed.',
                                'recommendation': 'Conduct emergency team meeting to identify blockers. Review sprint goals and ensure tasks are properly assigned and achievable.'
                            }
                        ],
                        'sprint_breakdown': sprint_breakdown,  # ✅ Now includes sprint breakdown
                        'message': f'⚠️ WARNING: Project has been running for {days_elapsed} days but has 0 completed sprints. This is a critical issue requiring immediate attention.'
                    }
        
        # ========================================
        # ENHANCEMENT 1: Confidence-Based Forecasting
        # ========================================
        confidence_forecasts = self._calculate_confidence_intervals(
            sprint_data=sprint_data,
            task_data=task_data,
            completed_sprints=completed_sprints,
            remaining_story_points=remaining_story_points,
            sprint_size_days=sprint_size_days,
            end_date=end_date
        )
        
        # ========================================
        # STEP 2-4: Forecast Remaining Sprints and Sprint Delay
        # ========================================
        if avg_velocity > 0:
            forecasted_remaining_sprints = remaining_story_points / avg_velocity
        else:
            forecasted_remaining_sprints = 0
        
        forecasted_total_sprints = completed_sprints + forecasted_remaining_sprints
        sprint_delay = forecasted_total_sprints - planned_total_sprints
        
        # Only consider positive delays
        if sprint_delay < 0:
            sprint_delay = 0
        
        # ========================================
        # STEP 5-6: Convert to Days and Adjust for Availability
        # ========================================
        delay_days_raw = sprint_delay * sprint_size_days
        
        # Calculate Developer Availability Factor
        total_leave_hours = sum([sprint.get('total_leave_hours', 0) or 0 for sprint in sprint_data])
        total_planned_hours = sum([sprint.get('total_estimated_hours', 0) or 0 for sprint in sprint_data])
        
        if total_planned_hours > 0:
            availability_ratio = 1 - (total_leave_hours / total_planned_hours)
        else:
            availability_ratio = 1.0
        
        # Clamp availability ratio to minimum threshold
        if availability_ratio < self.MIN_AVAILABILITY_RATIO:
            availability_ratio = self.MIN_AVAILABILITY_RATIO
        
        # Adjust delay using availability
        adjusted_delay_days = delay_days_raw / availability_ratio
        
        # ========================================
        # STEP 7: Forecast Actual End Date
        # ========================================
        forecasted_end_date = end_date + timedelta(days=int(adjusted_delay_days))
        
        # ========================================
        # STEP 8: Calculate Delay Percentage
        # ========================================
        if project_duration_days > 0:
            delay_percentage = adjusted_delay_days / project_duration_days
        else:
            delay_percentage = 0.0
        
        # Clamp to 100%
        if delay_percentage > 1.0:
            delay_percentage = 1.0
        
        # ========================================
        # STEP 9: Determine Risk Level
        # ========================================
        risk_level = self._determine_risk_level(delay_percentage)
        
        # ========================================
        # ENHANCEMENT 2: Velocity Trend Analysis
        # ========================================
        velocity_trend = self._calculate_velocity_trend(
            sprint_data=sprint_data,
            task_data=task_data,
            avg_velocity=avg_velocity
        )
        
        # ========================================
        # ENHANCEMENT 3: Scope Change Detection
        # ========================================
        scope_analysis = self._calculate_scope_change(
            total_story_points=total_story_points,
            planned_total_sprints=planned_total_sprints,
            avg_velocity=avg_velocity
        )
        
        # ========================================
        # ENHANCEMENT 4: Delay Attribution Breakdown
        # ========================================
        delay_attribution = self._calculate_delay_attribution(
            delay_days_raw=delay_days_raw,
            adjusted_delay_days=adjusted_delay_days,
            avg_velocity=avg_velocity,
            expected_velocity=total_story_points / planned_total_sprints if planned_total_sprints > 0 else 0,
            scope_change_ratio=scope_analysis['scope_change_ratio'],
            availability_ratio=availability_ratio
        )
        
        # ========================================
        # ENHANCEMENT 5: Early Warning System
        # ========================================
        early_warnings = self._generate_early_warnings(
            velocity_trend=velocity_trend,
            scope_change_ratio=scope_analysis['scope_change_ratio'],
            availability_ratio=availability_ratio,
            sprint_data=sprint_data,
            task_data=task_data,
            completed_sprints=completed_sprints
        )
        
        # Calculate expected velocity
        if planned_total_sprints > 0:
            expected_velocity = total_story_points / planned_total_sprints
        else:
            expected_velocity = 0.0
        
        # Generate sprint breakdown
        sprint_breakdown = self._generate_sprint_breakdown(sprint_data, task_data)
        
        # ========================================
        # Return Comprehensive Results
        # ========================================
        return {
            'project_id': project_data['project_id'],
            'project_name': project_data['project_name'],
            'project_key': project_data['key'],
            
            # Dates
            'project_start_date': start_date.isoformat(),
            'planned_end_date': end_date.isoformat(),
            'current_date': current_date.isoformat(),
            'forecasted_end_date': forecasted_end_date.isoformat(),
            
            # Sprint configuration
            'sprint_size_weeks': sprint_size_weeks,
            'sprint_size_days': sprint_size_days,
            
            # Core delay metrics
            'planned_total_sprints': round(planned_total_sprints, 2),
            'completed_sprints': completed_sprints,
            'forecasted_remaining_sprints': round(forecasted_remaining_sprints, 2),
            'forecasted_total_sprints': round(forecasted_total_sprints, 2),
            'sprint_delay': round(sprint_delay, 2),
            'delay_days': round(adjusted_delay_days, 2),
            'delay_percentage': round(delay_percentage * 100, 2),
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
            'actual_velocity': round(avg_velocity, 2),
            'velocity_variance': round(avg_velocity - expected_velocity, 2),
            
            # Availability
            'total_planned_hours': total_planned_hours,
            'total_leave_hours': total_leave_hours,
            'availability_ratio': round(availability_ratio, 4),
            
            # ========================================
            # ENHANCED FEATURES
            # ========================================
            
            # Enhancement 1: Confidence Intervals
            'confidence_forecasts': confidence_forecasts,
            
            # Enhancement 2: Velocity Trend
            'velocity_trend': velocity_trend,
            
            # Enhancement 3: Scope Change
            'scope_analysis': scope_analysis,
            
            # Enhancement 4: Delay Attribution
            'delay_attribution': delay_attribution,
            
            # Enhancement 5: Early Warnings
            'early_warnings': early_warnings,
            
            # Sprint breakdown
            'sprint_breakdown': sprint_breakdown
        }
    
    # ========================================
    # ENHANCEMENT METHODS
    # ========================================
    
    def _calculate_confidence_intervals(
        self,
        sprint_data: List[Dict],
        task_data: List[Dict],
        completed_sprints: int,
        remaining_story_points: int,
        sprint_size_days: int,
        end_date: datetime.date
    ) -> Dict[str, Any]:
        """
        ENHANCEMENT 1: Confidence-Based Forecasting
        
        Calculates best case, most likely, and worst case end dates
        based on velocity variations in recent sprints.
        
        Returns:
            Dictionary with best/most_likely/worst case forecasts
        """
        if completed_sprints < 1:
            return {
                'best_case_end_date': end_date.isoformat(),
                'most_likely_end_date': end_date.isoformat(),
                'worst_case_end_date': end_date.isoformat(),
                'best_case_velocity': 0.0,
                'most_likely_velocity': 0.0,
                'worst_case_velocity': 0.0,
                'confidence_range_days': 0
            }
        
        # Get completed sprints
        completed_sprints_list = [
            s for s in sprint_data 
            if s['sprint_status'] in ['Completed', 'Closed']
        ]
        
        # Calculate velocity for each completed sprint
        sprint_velocities = []
        for sprint in completed_sprints_list:
            sprint_id = sprint['sprint_id']
            sprint_tasks = [t for t in task_data if t.get('sprint_id') == sprint_id]
            completed_sp = sum([
                t.get('story_points', 0) or 0 
                for t in sprint_tasks 
                if t['status'] == 'Completed'
            ])
            sprint_velocities.append(completed_sp)
        
        if not sprint_velocities:
            return {
                'best_case_end_date': end_date.isoformat(),
                'most_likely_end_date': end_date.isoformat(),
                'worst_case_end_date': end_date.isoformat(),
                'best_case_velocity': 0.0,
                'most_likely_velocity': 0.0,
                'worst_case_velocity': 0.0,
                'confidence_range_days': 0
            }
        
        # Get last N sprints for confidence calculation
        recent_velocities = sprint_velocities[-self.RECENT_SPRINTS_FOR_CONFIDENCE:]
        
        # Calculate confidence velocities
        best_case_velocity = max(recent_velocities)
        most_likely_velocity = sum(recent_velocities) / len(recent_velocities)
        worst_case_velocity = min(recent_velocities)
        
        # Calculate remaining sprints for each scenario
        if best_case_velocity > 0:
            best_remaining_sprints = remaining_story_points / best_case_velocity
        else:
            best_remaining_sprints = 0
        
        if most_likely_velocity > 0:
            likely_remaining_sprints = remaining_story_points / most_likely_velocity
        else:
            likely_remaining_sprints = 0
        
        if worst_case_velocity > 0:
            worst_remaining_sprints = remaining_story_points / worst_case_velocity
        else:
            worst_remaining_sprints = remaining_story_points * 2  # Pessimistic estimate
        
        # Convert to dates
        best_case_end_date = end_date + timedelta(days=int(best_remaining_sprints * sprint_size_days))
        most_likely_end_date = end_date + timedelta(days=int(likely_remaining_sprints * sprint_size_days))
        worst_case_end_date = end_date + timedelta(days=int(worst_remaining_sprints * sprint_size_days))
        
        # Calculate confidence range
        confidence_range_days = (worst_case_end_date - best_case_end_date).days
        
        return {
            'best_case_end_date': best_case_end_date.isoformat(),
            'most_likely_end_date': most_likely_end_date.isoformat(),
            'worst_case_end_date': worst_case_end_date.isoformat(),
            'best_case_velocity': round(best_case_velocity, 2),
            'most_likely_velocity': round(most_likely_velocity, 2),
            'worst_case_velocity': round(worst_case_velocity, 2),
            'confidence_range_days': confidence_range_days
        }
    
    def _calculate_velocity_trend(
        self,
        sprint_data: List[Dict],
        task_data: List[Dict],
        avg_velocity: float
    ) -> Dict[str, Any]:
        """
        ENHANCEMENT 2: Velocity Trend Analysis
        
        Detects if team velocity is accelerating or decelerating
        by comparing recent sprints to overall average.
        
        Returns:
            Dictionary with trend analysis
        """
        completed_sprints_list = [
            s for s in sprint_data 
            if s['sprint_status'] in ['Completed', 'Closed']
        ]
        
        if len(completed_sprints_list) < 2:
            return {
                'trend_direction': 'STABLE',
                'trend_value': 0.0,
                'recent_avg_velocity': avg_velocity,
                'overall_avg_velocity': avg_velocity,
                'is_improving': False,
                'is_declining': False
            }
        
        # Calculate velocity for each sprint
        sprint_velocities = []
        for sprint in completed_sprints_list:
            sprint_id = sprint['sprint_id']
            sprint_tasks = [t for t in task_data if t.get('sprint_id') == sprint_id]
            completed_sp = sum([
                t.get('story_points', 0) or 0 
                for t in sprint_tasks 
                if t['status'] == 'Completed'
            ])
            sprint_velocities.append(completed_sp)
        
        # Get recent sprints
        recent_velocities = sprint_velocities[-self.RECENT_SPRINTS_FOR_CONFIDENCE:]
        recent_avg = sum(recent_velocities) / len(recent_velocities) if recent_velocities else 0
        
        # Calculate trend
        trend_value = recent_avg - avg_velocity
        
        # Determine trend direction
        if trend_value > 0:
            trend_direction = 'ACCELERATING'
            is_improving = True
            is_declining = False
        elif trend_value < 0:
            trend_direction = 'DECELERATING'
            is_improving = False
            is_declining = True
        else:
            trend_direction = 'STABLE'
            is_improving = False
            is_declining = False
        
        return {
            'trend_direction': trend_direction,
            'trend_value': round(trend_value, 2),
            'recent_avg_velocity': round(recent_avg, 2),
            'overall_avg_velocity': round(avg_velocity, 2),
            'is_improving': is_improving,
            'is_declining': is_declining
        }
    
    def _calculate_scope_change(
        self,
        total_story_points: int,
        planned_total_sprints: float,
        avg_velocity: float
    ) -> Dict[str, Any]:
        """
        ENHANCEMENT 3: Scope Change Detection
        
        Measures scope creep by comparing current total story points
        to the originally planned baseline.
        
        Returns:
            Dictionary with scope change analysis
        """
        # Calculate original planned story points
        # (This is an estimate based on planned sprints and current velocity)
        if planned_total_sprints > 0 and avg_velocity > 0:
            original_planned_sp = planned_total_sprints * avg_velocity
        else:
            original_planned_sp = total_story_points
        
        # Calculate scope change
        if original_planned_sp > 0:
            scope_change_ratio = (total_story_points - original_planned_sp) / original_planned_sp
        else:
            scope_change_ratio = 0.0
        
        # Determine if significant scope change occurred
        has_scope_creep = scope_change_ratio > self.SCOPE_CHANGE_THRESHOLD
        
        return {
            'original_planned_story_points': round(original_planned_sp, 2),
            'current_total_story_points': total_story_points,
            'scope_change_story_points': round(total_story_points - original_planned_sp, 2),
            'scope_change_ratio': round(scope_change_ratio, 4),
            'scope_change_percentage': round(scope_change_ratio * 100, 2),
            'has_scope_creep': has_scope_creep
        }
    
    def _calculate_delay_attribution(
        self,
        delay_days_raw: float,
        adjusted_delay_days: float,
        avg_velocity: float,
        expected_velocity: float,
        scope_change_ratio: float,
        availability_ratio: float
    ) -> Dict[str, Any]:
        """
        ENHANCEMENT 4: Delay Attribution Breakdown
        
        Breaks down delay into contributing factors:
        - Low velocity
        - Availability (leave)
        - Scope change
        
        Returns:
            Dictionary with delay attribution percentages
        """
        if adjusted_delay_days <= 0:
            return {
                'velocity_impact_days': 0.0,
                'availability_impact_days': 0.0,
                'scope_impact_days': 0.0,
                'velocity_impact_percentage': 0.0,
                'availability_impact_percentage': 0.0,
                'scope_impact_percentage': 0.0,
                'primary_cause': 'NONE'
            }
        
        # Calculate velocity impact
        # (Difference between expected and actual velocity)
        if expected_velocity > 0:
            velocity_ratio = avg_velocity / expected_velocity
        else:
            velocity_ratio = 1.0
        
        if velocity_ratio < 1.0:
            velocity_impact_days = delay_days_raw * (1 - velocity_ratio)
        else:
            velocity_impact_days = 0.0
        
        # Calculate availability impact
        # (Difference between raw and adjusted delay)
        availability_impact_days = adjusted_delay_days - delay_days_raw
        
        # Calculate scope impact
        # (Estimated delay due to scope increase)
        if scope_change_ratio > 0:
            scope_impact_days = adjusted_delay_days * scope_change_ratio
        else:
            scope_impact_days = 0.0
        
        # Normalize to percentages
        total_impact = velocity_impact_days + availability_impact_days + scope_impact_days
        
        if total_impact > 0:
            velocity_pct = (velocity_impact_days / total_impact) * 100
            availability_pct = (availability_impact_days / total_impact) * 100
            scope_pct = (scope_impact_days / total_impact) * 100
        else:
            velocity_pct = 0.0
            availability_pct = 0.0
            scope_pct = 0.0
        
        # Determine primary cause
        max_impact = max(velocity_pct, availability_pct, scope_pct)
        if max_impact == velocity_pct and velocity_pct > 0:
            primary_cause = 'LOW_VELOCITY'
        elif max_impact == availability_pct and availability_pct > 0:
            primary_cause = 'AVAILABILITY'
        elif max_impact == scope_pct and scope_pct > 0:
            primary_cause = 'SCOPE_CHANGE'
        else:
            primary_cause = 'NONE'
        
        return {
            'velocity_impact_days': round(velocity_impact_days, 2),
            'availability_impact_days': round(availability_impact_days, 2),
            'scope_impact_days': round(scope_impact_days, 2),
            'velocity_impact_percentage': round(velocity_pct, 2),
            'availability_impact_percentage': round(availability_pct, 2),
            'scope_impact_percentage': round(scope_pct, 2),
            'primary_cause': primary_cause
        }
    
    def _generate_early_warnings(
        self,
        velocity_trend: Dict,
        scope_change_ratio: float,
        availability_ratio: float,
        sprint_data: List[Dict],
        task_data: List[Dict],
        completed_sprints: int
    ) -> List[Dict[str, Any]]:
        """
        ENHANCEMENT 5: Early Warning System
        
        Generates rule-based alerts for potential project risks.
        
        Returns:
            List of warning dictionaries
        """
        warnings = []
        
        # Warning 1: Velocity Drop
        if velocity_trend['is_declining']:
            velocity_drop_ratio = abs(velocity_trend['trend_value']) / velocity_trend['overall_avg_velocity'] if velocity_trend['overall_avg_velocity'] > 0 else 0
            if velocity_drop_ratio > self.VELOCITY_DROP_THRESHOLD:
                warnings.append({
                    'type': 'VELOCITY_DROP',
                    'severity': 'HIGH',
                    'message': f"Team velocity has dropped by {velocity_drop_ratio*100:.1f}% in recent sprints",
                    'recommendation': 'Investigate team capacity, blockers, or technical debt issues'
                })
        
        # Warning 2: Low Availability
        if availability_ratio < self.LOW_AVAILABILITY_THRESHOLD:
            warnings.append({
                'type': 'LOW_AVAILABILITY',
                'severity': 'MEDIUM',
                'message': f"Team availability is only {availability_ratio*100:.1f}% due to leave hours",
                'recommendation': 'Consider adjusting sprint commitments or adding resources'
            })
        
        # Warning 3: Scope Creep
        if scope_change_ratio > self.SCOPE_CHANGE_THRESHOLD:
            warnings.append({
                'type': 'SCOPE_CREEP',
                'severity': 'HIGH',
                'message': f"Project scope has increased by {scope_change_ratio*100:.1f}%",
                'recommendation': 'Review and prioritize backlog, consider descoping low-priority items'
            })
        
        # Warning 4: Low Sprint Completion
        if completed_sprints > 0:
            # Check last sprint completion rate
            completed_sprints_list = [
                s for s in sprint_data 
                if s['sprint_status'] in ['Completed', 'Closed']
            ]
            
            if completed_sprints_list:
                last_sprint = completed_sprints_list[-1]
                sprint_id = last_sprint['sprint_id']
                sprint_tasks = [t for t in task_data if t.get('sprint_id') == sprint_id]
                
                if sprint_tasks:
                    planned_sp = sum([t.get('story_points', 0) or 0 for t in sprint_tasks])
                    completed_sp = sum([
                        t.get('story_points', 0) or 0 
                        for t in sprint_tasks 
                        if t['status'] == 'Completed'
                    ])
                    
                    if planned_sp > 0:
                        completion_rate = completed_sp / planned_sp
                        if completion_rate < self.LOW_COMPLETION_THRESHOLD:
                            warnings.append({
                                'type': 'LOW_SPRINT_COMPLETION',
                                'severity': 'MEDIUM',
                                'message': f"Last sprint achieved only {completion_rate*100:.1f}% completion",
                                'recommendation': 'Review sprint planning accuracy and remove impediments'
                            })
        
        # Warning 5: Consecutive Low Performance
        if completed_sprints >= self.CONSECUTIVE_SPRINTS_FOR_TREND:
            completed_sprints_list = [
                s for s in sprint_data 
                if s['sprint_status'] in ['Completed', 'Closed']
            ]
            
            recent_sprints = completed_sprints_list[-self.CONSECUTIVE_SPRINTS_FOR_TREND:]
            low_performance_count = 0
            
            for sprint in recent_sprints:
                sprint_id = sprint['sprint_id']
                sprint_tasks = [t for t in task_data if t.get('sprint_id') == sprint_id]
                
                if sprint_tasks:
                    planned_sp = sum([t.get('story_points', 0) or 0 for t in sprint_tasks])
                    completed_sp = sum([
                        t.get('story_points', 0) or 0 
                        for t in sprint_tasks 
                        if t['status'] == 'Completed'
                    ])
                    
                    if planned_sp > 0:
                        completion_rate = completed_sp / planned_sp
                        if completion_rate < self.LOW_COMPLETION_THRESHOLD:
                            low_performance_count += 1
            
            if low_performance_count >= self.CONSECUTIVE_SPRINTS_FOR_TREND:
                warnings.append({
                    'type': 'CONSECUTIVE_LOW_PERFORMANCE',
                    'severity': 'CRITICAL',
                    'message': f"{low_performance_count} consecutive sprints with low completion rates",
                    'recommendation': 'Conduct retrospective to identify systemic issues and implement corrective actions'
                })
        
        return warnings
    
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
            List of sprint breakdown dictionaries (sorted by sprint_id)
        """
        breakdown = []
        
        for sprint in sprint_data:
            sprint_id = sprint['sprint_id']
            
            # Calculate story points for this sprint
            # Match sprint_id with type conversion to handle int/string mismatches
            sprint_tasks = [
                t for t in task_data 
                if t.get('sprint_id') is not None and str(t.get('sprint_id')) == str(sprint_id)
            ]
            
            planned_story_points = sum([t.get('story_points', 0) or 0 for t in sprint_tasks])
            completed_story_points = sum([
                t.get('story_points', 0) or 0 
                for t in sprint_tasks 
                if t.get('status') == 'Completed'
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
        
        # Sort by sprint number extracted from sprint name (e.g., "Sprint 1", "Sprint 2", "Sprint 3")
        # This ensures proper ordering: Sprint 1, Sprint 2, Sprint 3... regardless of dates or IDs
        def extract_sprint_number(sprint_dict):
            import re
            sprint_name = sprint_dict['sprint_name']
            # Try to extract number from sprint name (e.g., "Sprint 1" -> 1, "Sprint 2 - Core" -> 2)
            match = re.search(r'(\d+)', sprint_name)
            if match:
                return int(match.group(1))
            # If no number found, return a large number to sort at the end
            return 999
        
        breakdown.sort(key=extract_sprint_number)
        
        return breakdown
