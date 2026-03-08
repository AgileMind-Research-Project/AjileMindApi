"""
Risk Remediation Recommendation Service

Generates actionable recommendations to reduce project risks using an LLM.
Focuses on practical Agile project management recommendations.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from app.core.logger import logger
from fastapi import HTTPException
import json

# Import LLM service for AI-powered recommendations
try:
    from app.services.llm_service import llm_service
    LLM_AVAILABLE = True
    print("✅ LLM Service loaded - AI-powered recommendations enabled")
except ImportError as e:
    LLM_AVAILABLE = False
    print(f"⚠️ LLM Service not available: {e}")
    print("   Falling back to rule-based recommendations")

from app.services.risk_calculation_service import RiskCalculationService
risk_calc_service = RiskCalculationService()


class RecommendationService:
    """Service for generating AI-powered risk remediation recommendations"""
    
    # System prompt that defines the AI's behavior and constraints
    SYSTEM_PROMPT = """You are an expert Agile project management consultant. Your task is to provide actionable remediation recommendations to reduce project risks.

IMPORTANT RULES:
❌ Do NOT calculate risk values or scores
❌ Do NOT override system-calculated risk levels  
❌ Do NOT suggest unrealistic or theoretical actions
❌ Do NOT mention AI, models, or algorithms

✅ ONLY provide practical Agile project management recommendations
✅ Base recommendations only on the provided data
✅ Keep recommendations clear, concise, and actionable
✅ Focus on reducing the identified risk

OUTPUT REQUIREMENTS:
- Provide exactly 3 to 5 recommendations
- Use simple, professional language
- Focus on reducing the identified risk
- Be applicable to real Agile projects
- Avoid repetition
- Be suitable for display in a project dashboard"""

    def __init__(self):
        """Initialize the recommendation service"""
        pass
    
    async def generate_recommendations(
        self,
        risk_type: str,
        project_data: Dict[str, Any],
        metadata: Dict[str, Any],
        params_config: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate AI-powered recommendations for a specific risk type.
        
        ⚠️ 100% AI-ONLY - NO HARDCODED FALLBACK RULES!
        
        This method ONLY uses Ollama LLM (via LangChain) to generate recommendations.
        If the LLM is unavailable, it returns an empty list.
        
        Requirements:
        - Ollama must be running
        - AI model (llama3.2) must be downloaded
        - LangChain packages must be installed
        
        Args:
            risk_type: The type of risk (e.g., 'uncompleted_tasks', 'detected_bugs')
            project_data: Project information and context
            metadata: Risk metadata including counts and breakdowns
            
        Returns:
            List of AI-generated recommendation strings (3-5 recommendations)
            Empty list if LLM is unavailable
        """
        try:
            # CHECK: Is LLM service available?
            if not LLM_AVAILABLE:
                print("❌ LLM Service not available - Cannot generate recommendations")
                print("   Please ensure:")
                print("   1. Ollama is installed and running")
                print("   2. Model is downloaded: ollama pull llama3.2")
                print("   3. Dependencies installed: pip install -r requirements.txt")
                return []
            
            # USE AI TO GENERATE RECOMMENDATIONS
            print(f"🤖 Using AI (Ollama + Llama3.2) to generate recommendations for {risk_type}")
            
            llm_recommendations = await llm_service.generate_recommendations(
                risk_type=risk_type,
                project_data=project_data,
                metadata=metadata
            )
            
            # Map recommendations to impact scores if available
            result = []
            if llm_recommendations:
                # Calculate potential impact for this risk type
                # For impact display, we show the reduction of 1 "unit" (1 bug, 1 task, etc.)
                # This gives the user a sense of "value per action"
                potential_reduction = 0.0
                if params_config:
                    potential_reduction = risk_calc_service.calculate_hypothetical_impact(
                        current_metrics=metadata,
                        params_config=params_config,
                        param_to_improve=risk_type,
                        improvement_amount=1.0
                    )

                for rec in llm_recommendations:
                    result.append({
                        "text": rec,
                        "potential_reduction": potential_reduction
                    })

            if result:
                print(f"✅ AI generated {len(result)} recommendations with impact scores")
                return result
            else:
                print("⚠️ AI returned empty recommendations")
                return []
                
        except Exception as e:
            print(f"❌ Error generating AI recommendations: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    # ============================================================================
    # LEGACY RULE-BASED METHODS BELOW (NOT USED ANYMORE - KEPT FOR REFERENCE)
    # ============================================================================
    # 
    # The following methods contain hardcoded rules and are NO LONGER CALLED.
    # They are kept here only for reference or emergency fallback if needed.
    # To re-enable fallback, modify generate_recommendations() above.
    #
    
    async def _generate_uncompleted_tasks_recommendations(
        self,
        project_data: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations for uncompleted tasks risk"""
        
        recommendations = []
        
        # Extract key metrics
        total_tasks = metadata.get('total_tasks', 0)
        uncompleted_tasks = metadata.get('uncompleted_tasks', 0)
        todo_tasks = metadata.get('todo_tasks', 0)
        inprogress_tasks = metadata.get('inprogress_tasks', 0)
        overdue_tasks = metadata.get('overdue_tasks', 0)
        max_overdue_days = metadata.get('max_overdue_days', 0)
        developer_breakdown = metadata.get('developer_breakdown', [])
        
        # Rule-based recommendations based on the data
        
        # 1. High number of To-Do tasks
        if todo_tasks > total_tasks * 0.5:  # More than 50% not started
            recommendations.append(
                f"Break down the {todo_tasks} unstarted tasks into smaller, manageable units. "
                "Consider splitting large tasks into sub-tasks with clear acceptance criteria "
                "to improve team velocity and reduce overwhelm."
            )
        
        # 2. Developer workload imbalance
        if developer_breakdown and isinstance(developer_breakdown, list) and len(developer_breakdown) > 0:
            # Ensure all items are dictionaries
            if all(isinstance(dev, dict) for dev in developer_breakdown):
                # Sort by uncompleted tasks
                sorted_devs = sorted(
                    developer_breakdown, 
                    key=lambda x: x.get('uncompleted_tasks', 0) if isinstance(x, dict) else 0,
                    reverse=True
                )
                if len(sorted_devs) >= 2:
                    highest_load = sorted_devs[0].get('uncompleted_tasks', 0)
                    lowest_load = sorted_devs[-1].get('uncompleted_tasks', 0)
                    
                    if highest_load > lowest_load * 2:  # Significant imbalance
                        overloaded_dev = sorted_devs[0].get('developer_name', 'team member')
                        recommendations.append(
                            f"Rebalance workload by reassigning tasks from {overloaded_dev} "
                            f"({highest_load} uncompleted tasks) to team members with lighter loads. "
                            "Hold a planning session to redistribute work fairly."
                        )
        
        
        # 3. Overdue tasks
        if overdue_tasks > 0:
            if max_overdue_days > 7:  # More than a week overdue
                recommendations.append(
                    f"Address the {overdue_tasks} overdue task{'s' if overdue_tasks > 1 else ''} immediately "
                    f"(some tasks are {max_overdue_days} days overdue). "
                    "Host a triage meeting to reprioritize, reassign, or defer these tasks to the next sprint."
                )
            else:
                recommendations.append(
                    f"Focus daily standup discussions on the {overdue_tasks} overdue task{'s' if overdue_tasks > 1 else ''}. "
                    "Identify blockers and provide necessary support to get these back on track."
                )
        
        # 4. Many in-progress tasks
        if inprogress_tasks > total_tasks * 0.4:  # More than 40% in progress
            recommendations.append(
                f"Reduce WIP (Work In Progress) by limiting concurrent tasks. "
                f"With {inprogress_tasks} tasks in progress, encourage the team to complete "
                "existing work before starting new tasks to improve flow and completion rate."
            )
        
        # 5. General recommendations if not enough specific ones
        if len(recommendations) < 3:
            # Check for high uncompleted ratio
            if total_tasks > 0:
                uncompleted_ratio = uncompleted_tasks / total_tasks
                if uncompleted_ratio > 0.6:
                    recommendations.append(
                        "Review sprint scope and timeline with the team. Consider deferring "
                        "low-priority tasks to future sprints to ensure the team can deliver "
                        "high-value items successfully."
                    )
        
        if len(recommendations) < 3:
            recommendations.append(
                "Improve daily coordination by ensuring blockers are raised and resolved quickly. "
                "Create a shared accountability system where team members check on each other's progress."
            )
        
        if len(recommendations) < 3:
            recommendations.append(
                "Conduct a retrospective on estimation accuracy. If tasks are consistently "
                "uncompleted, the team may be overestimating capacity or underestimating complexity."
            )
        
        # Check for available developers and add special recommendation
        available_devs_data = metadata.get('available_developers_data', {})
        available_count = available_devs_data.get('available_count', 0)
        
        if available_count > 0:
            available_developers = available_devs_data.get('available_developers', [])
            dev_names = [dev.get('name', 'Unknown') for dev in available_developers[:2]]  # Show max 2 names
            
            if len(dev_names) == 1:
                dev_list = dev_names[0]
            else:
                dev_list = f"{dev_names[0]} and {dev_names[1]}"
            
            # Add special recommendation with marker for frontend
            recommendations.append(
                f"[AVAILABLE_DEVELOPERS] Assign tasks to available developers: {dev_list} "
                f"{'has' if available_count == 1 else 'have'} low workload and can take on additional tasks. "
                f"Click to view {available_count} available developer{'s' if available_count > 1 else ''}."
            )
        
        # Limit to 5 recommendations
        return recommendations[:5]
    
    async def _generate_bug_recommendations(
        self,
        project_data: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations for detected bugs risk"""
        
        recommendations = []
        
        # Extract bug metrics
        total_bugs = metadata.get('total_bugs', 0)
        todo_bugs = metadata.get('todo_bugs', 0)
        inprogress_bugs = metadata.get('inprogress_bugs', 0)
        completed_bugs = metadata.get('completed_bugs', 0)
        high_priority_bugs = metadata.get('high_priority_bugs', 0)
        medium_priority_bugs = metadata.get('medium_priority_bugs', 0)
        low_priority_bugs = metadata.get('low_priority_bugs', 0)
        
        # Calculate critical bug percentage
        critical_bug_ratio = (high_priority_bugs / total_bugs * 100) if total_bugs > 0 else 0
        
        # 1. Prioritize critical and high-severity bugs
        if high_priority_bugs > 0:
            if critical_bug_ratio > 30:  # More than 30% are high priority
                recommendations.append(
                    f"CRITICAL: Prioritize the {high_priority_bugs} high-priority bugs immediately. "
                    f"With {critical_bug_ratio:.1f}% of bugs being high-priority, assign your most "
                    "experienced developers to resolve these critical issues before they impact production. "
                    "Consider pausing new feature development until critical bugs are addressed."
                )
            else:
                recommendations.append(
                    f"Focus on resolving {high_priority_bugs} high-priority bug{'s' if high_priority_bugs > 1 else ''} "
                    "first. Create a priority queue with dedicated senior developers for critical bug fixes. "
                    "Ensure these bugs are addressed within the current sprint to prevent production issues."
                )
        
        # 2. Allocate dedicated bug-fix time
        if todo_bugs > total_bugs * 0.4:  # More than 40% bugs not started
            recommendations.append(
                f"Allocate dedicated bug-fix time by implementing 'Bug Fix Fridays' or reserving 30% "
                f"of sprint capacity specifically for the {todo_bugs} unstarted bugs. "
                "Create a rotating bug-fix schedule where developers spend dedicated hours on bug resolution. "
                "This structured approach prevents bugs from accumulating in the backlog."
            )
        elif inprogress_bugs > 5:
            recommendations.append(
                f"Focus team efforts on completing the {inprogress_bugs} in-progress bugs before starting new ones. "
                "Implement a 'bugs first' policy during daily standups where bug status is reviewed before feature work. "
                "Limit work-in-progress by requiring bug completion before picking up new tasks."
            )
        
        # 3. Strengthen code reviews and testing
        if total_bugs > 10:
            bug_density_msg = "high bug count" if total_bugs > 20 else "significant bug count"
            recommendations.append(
                f"Strengthen code reviews and testing processes to address the {bug_density_msg} ({total_bugs} bugs). "
                "Implement mandatory peer code reviews for all changes, add automated unit and integration tests, "
                "and establish a 'Definition of Done' that includes test coverage requirements. "
                "Analyze bug patterns to identify root causes and prevent recurrence through better testing."
            )
        
        # 4. Reduce new feature development temporarily (if critical situation)
        if critical_bug_ratio > 40 or (high_priority_bugs > 5 and todo_bugs > total_bugs * 0.5):
            recommendations.append(
                f"Temporarily reduce new feature development to focus on bug resolution. "
                f"With {high_priority_bugs} high-priority bugs and {todo_bugs} unstarted bugs, "
                "shift 70% of team capacity to bug fixes until the backlog is under control. "
                "Communicate this priority shift to stakeholders and adjust sprint commitments accordingly."
            )
        elif total_bugs > 15:
            recommendations.append(
                "Balance feature development with bug resolution by allocating at least 40% of sprint capacity "
                f"to address the {total_bugs} detected bugs. Ensure every sprint includes measurable bug reduction goals "
                "to prevent technical debt accumulation."
            )
        
        # 5. Improve QA collaboration
        if inprogress_bugs > 3 or todo_bugs > 10:
            recommendations.append(
                "Improve QA collaboration by establishing daily sync meetings between developers and QA team. "
                "Implement pair debugging sessions where QA works directly with developers to reproduce and validate fixes. "
                "Create a shared bug dashboard with real-time status updates to improve transparency and coordination. "
                "Ensure QA is involved early in the development process to catch issues before they reach production."
            )
        
        # Additional recommendations based on bug completion rate
        if completed_bugs > 0 and total_bugs > 0:
            completion_rate = (completed_bugs / total_bugs) * 100
            if completion_rate < 30:
                recommendations.append(
                    f"Accelerate bug resolution rate - only {completion_rate:.1f}% of bugs are completed. "
                    "Hold retrospective meetings to identify blockers preventing bug fixes. "
                    "Consider bringing in additional resources or reducing sprint scope to focus on quality."
                )
        
        # Ensure we have fallback recommendations
        if len(recommendations) < 3:
            recommendations.append(
                "Create a comprehensive bug triage process with the Product Owner to classify bugs by severity and business impact. "
                "Establish clear SLAs for different bug priorities (e.g., critical bugs fixed within 24 hours, "
                "high priority within 3 days). Use this framework to make data-driven decisions about bug prioritization."
            )
        
        if len(recommendations) < 3:
            recommendations.append(
                "Implement preventive quality measures including pre-commit hooks, automated linting, "
                "continuous integration testing, and regular code quality reviews. "
                "Track bug metrics over time to measure improvement and adjust processes accordingly."
            )
        
        # Return top 5 recommendations
        return recommendations[:5]
    
    async def _generate_blocker_recommendations(
        self,
        project_data: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations for blockers risk"""
        
        recommendations = []
        
        total_blockers = metadata.get('total_blockers', 0)
        open_blockers = metadata.get('open_blockers', 0)
        critical_blockers = metadata.get('critical_blockers', 0)
        high_blockers = metadata.get('high_blockers', 0)
        
        if critical_blockers > 0:
            recommendations.append(
                f"Escalate the {critical_blockers} critical blocker{'s' if critical_blockers > 1 else ''} "
                "to senior management immediately. Create a war room or focused task force "
                "to resolve these blockers within 24-48 hours."
            )
        
        if open_blockers > 3:
            recommendations.append(
                f"Review all {open_blockers} open blockers in today's standup. Assign clear "
                "ownership for each blocker resolution and set specific target dates. "
                "Track blocker age to prevent prolonged impediments."
            )
        
        if (critical_blockers + high_blockers) > 0:
            recommendations.append(
                "Identify dependencies causing high-severity blockers. Work with cross-functional "
                "teams or external vendors to establish dedicated communication channels for "
                "faster resolution."
            )
        
        if total_blockers > 5:
            recommendations.append(
                "Implement a blocker prevention strategy by identifying common blocker patterns. "
                "Create early warning systems and establish clear escalation paths to prevent "
                "blockers from occurring."
            )
        
        if len(recommendations) < 3:
            recommendations.append(
                "Hold a blocker retrospective to understand root causes. Document solutions "
                "for common blockers to build a knowledge base for faster resolution in the future."
            )
        
        return recommendations[:5]
    
    async def _generate_timeline_recommendations(
        self,
        project_data: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations for timeline conflicts"""
        
        recommendations = []
        
        recommendations.append(
            "Review and adjust task schedules to resolve timeline conflicts. Use a sprint "
            "planning session to realign deadlines with team capacity and dependencies."
        )
        
        recommendations.append(
            "Identify critical path tasks and ensure they receive priority. Adjust non-critical "
            "task timelines to accommodate high-priority deliverables."
        )
        
        recommendations.append(
            "Communicate timeline adjustments to all stakeholders. Set realistic expectations "
            "and negotiate scope or deadline changes with the Product Owner if necessary."
        )
        
        recommendations.append(
            "Implement buffer time in future sprints to account for unexpected delays. "
            "Use historical velocity data to create more accurate estimations."
        )
        
        return recommendations[:5]
    
    async def _generate_availability_recommendations(
        self,
        project_data: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations for developer availability issues"""
        
        recommendations = []
        
        total_leave_hours = metadata.get('total_leave_hours', 0)
        developer_availability_breakdown = metadata.get('developer_availability_breakdown', [])
        
        if developer_availability_breakdown and isinstance(developer_availability_breakdown, list) and len(developer_availability_breakdown) > 0:
            # Ensure first item is a dictionary before accessing
            if isinstance(developer_availability_breakdown[0], dict):
                highest_leave = developer_availability_breakdown[0]
                dev_name = highest_leave.get('developer_name', 'team member')
                leave_hours = highest_leave.get('leave_hours', 0)
                
                if leave_hours > 40:  # More than a week
                    recommendations.append(
                        f"Plan for {dev_name}'s extended absence ({leave_hours}h). Cross-train "
                        "team members on their critical tasks and document knowledge to prevent "
                        "bottlenecks during their leave."
                    )
        
        
        recommendations.append(
            f"Adjust sprint capacity to account for {total_leave_hours} hours of team leave. "
            "Reduce sprint commitment proportionally to maintain realistic delivery targets."
        )
        
        recommendations.append(
            "Redistribute work from team members on leave to available developers. "
            "Hold a capacity planning session to ensure fair distribution and prevent overload."
        )
        
        recommendations.append(
            "Create a knowledge transfer plan for critical tasks. Ensure at least two team "
            "members are familiar with each major component to reduce dependency risks."
        )
        
        return recommendations[:5]
    
    async def _generate_available_developers_recommendations(
        self,
        project_data: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations for available developers (low workload)"""
        
        recommendations = []
        
        # Get available developers data
        available_devs_data = metadata.get('available_developers_data', {})
        available_developers = available_devs_data.get('available_developers', [])
        available_count = available_devs_data.get('available_count', 0)
        threshold = available_devs_data.get('threshold_percentage', 40)
        sprint_info = available_devs_data.get('sprint_info')
        
        if available_count == 0:
            return [
                "All team members are optimally utilized in the current sprint.",
                "Continue monitoring workload distribution during daily standups.",
                "Plan for future capacity adjustments if needed."
            ]
        
        # Create developer names list for recommendations
        dev_names = [dev.get('name', 'Unknown') for dev in available_developers[:3]]  # Show max 3 names
        
        # Main recommendation with developer names
        if len(dev_names) == 1:
            dev_list = dev_names[0]
        elif len(dev_names) == 2:
            dev_list = f"{dev_names[0]} and {dev_names[1]}"
        else:
            dev_list = f"{', '.join(dev_names[:-1])}, and {dev_names[-1]}"
        
        if available_count <= 3:
            recommendations.append(
                f"{dev_list} currently {'has' if available_count == 1 else 'have'} low workload "
                f"(< {threshold}% utilization). Consider assigning pending backlog items or "
                "helping overloaded team members to optimize sprint throughput."
            )
        else:
            recommendations.append(
                f"{available_count} developers have  low workload (< {threshold}% utilization) including {dev_list}. "
                "Review sprint planning to ensure optimal task distribution across the team."
            )
        
        # Calculate capacity statistics
        if sprint_info:
            available_capacity = sprint_info.get('available_capacity_hours', 0)
            if available_capacity > 0:
                recommendations.append(
                    f"The team has {available_capacity:.0f} hours of unused capacity in {sprint_info.get('sprint_name', 'this sprint')}. "
                    "Consider pulling high-priority items from the backlog to maximize sprint value delivery."
                )
        
        # Specific recommendations based on utilization
        zero_util_devs = [dev for dev in available_developers if dev.get('utilization_percentage', 0) == 0]
        if zero_util_devs:
            if len(zero_util_devs) == 1:
                recommendations.append(
                    f"{zero_util_devs[0].get('name')} has no tasks assigned in the current sprint. "
                    "Ensure they are aware of sprint goals and have work allocated immediately."
                )
            else:
                zero_names = [dev.get('name') for dev in zero_util_devs[:2]]
                recommendations.append(
                    f"{len(zero_util_devs)} developers have no task assignments including {', '.join(zero_names)}. "
                    "Hold an immediate planning session to distribute work and engage the full team."
                )
        
        # Balance workload recommendation
        recommendations.append(
            "Use daily standups to identify tasks that can be redistributed to available developers. "
            "This helps prevent burnout for overloaded team members and improves overall team velocity."
        )
        
        # Preventive recommendation
        if len(recommendations) < 5:
            recommendations.append(
                "Review sprint planning process to improve initial task distribution. "
                "Consider team member skills, availability, and capacity during sprint planning to "
                "achieve better workload balance from the start."
            )
        
        return recommendations[:5]
    
    def _get_default_recommendations(self, risk_type: str) -> List[str]:
        """Get default recommendations when specific data is unavailable"""
        
        return [
            f"Schedule a focused session to review and address '{risk_type.replace('_', ' ')}' risks with the team.",
            "Identify the root causes of this risk through data analysis and team input.",
            "Create an action plan with specific, measurable steps to reduce this risk.",
            "Assign clear ownership for risk mitigation activities with defined deadlines.",
            "Monitor progress weekly and adjust strategies based on results."
        ]


# Create a singleton instance
recommendation_service = RecommendationService()
