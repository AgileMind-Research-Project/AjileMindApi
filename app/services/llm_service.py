"""
LLM Service for AI-Powered Recommendations using Ollama + LangChain
"""
from typing import Dict, Any, List, Optional
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
import json


class LLMRecommendationService:
    """
    Service for generating AI-powered recommendations using local Ollama LLM.
    No hardcoded rules - all recommendations are generated dynamically by AI.
    """
    
    def __init__(self, model_name: str = "llama3.2", base_url: str = "http://localhost:11434"):
        """
        Initialize LLM service with Ollama.
        
        Args:
            model_name: Ollama model to use (llama3.2, mistral, codellama, etc.)
            base_url: Ollama API endpoint
        """
        self.model_name = model_name
        self.base_url = base_url
        self.llm = None
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize the Ollama LLM connection"""
        try:
            self.llm = OllamaLLM(
                model=self.model_name,
                base_url=self.base_url,
                temperature=0.7,  # Creative but not random
                num_predict=500,  # Max tokens per response
            )
            print(f"âœ… LLM Service initialized with {self.model_name}")
        except Exception as e:
            print(f"âš ï¸ Failed to initialize LLM: {e}")
            print("   Recommendations will fall back to rule-based system")
            self.llm = None
    
    async def generate_recommendations(
        self,
        risk_type: str,
        project_data: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> List[str]:
        """
        Generate AI-powered recommendations for a specific risk type.
        
        Args:
            risk_type: Type of risk (uncompleted_tasks, detected_bugs, etc.)
            project_data: Basic project information
            metadata: Detailed risk metrics
        
        Returns:
            List of 3-5 actionable recommendations
        """
        if not self.llm:
            print("âš ï¸ LLM not available, returning empty recommendations")
            return []
        
        try:
            # Build context-specific prompt
            prompt = self._build_prompt(risk_type, project_data, metadata)
            
            # Generate recommendations using LLM
            print(f"ðŸ¤– Generating AI recommendations for {risk_type}...")
            response = await self._call_llm(prompt)
            
            # Parse and clean recommendations
            recommendations = self._parse_recommendations(response)
            
            print(f"âœ… Generated {len(recommendations)} AI recommendations")
            return recommendations[:5]  # Return max 5
            
        except Exception as e:
            print(f"âŒ LLM generation failed: {e}")
            return []
    
    def _build_prompt(self, risk_type: str, project_data: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Build a context-aware prompt for the LLM based on risk type"""
        
        # Base system context
        system_context = """You are an expert AI project management consultant specializing in Agile/Scrum methodologies.
Your role is to analyze project risk data and provide actionable, specific recommendations to mitigate risks.

IMPORTANT RULES:
1. Generate EXACTLY 3-5 recommendations
2. Each recommendation should be specific and actionable
3. Use the actual data/numbers from the project metrics
4. Focus on practical solutions teams can implement immediately
5. Format each recommendation as a complete sentence
6. Number each recommendation (1., 2., 3., etc.)
7. Keep each recommendation to 2-3 sentences maximum
8. Be direct and avoid generic advice"""
        
        # Risk-specific prompts
        if risk_type == 'uncompleted_tasks':
            prompt = f"""{system_context}

RISK TYPE: Uncompleted Tasks

PROJECT METRICS:
- Total Tasks: {metadata.get('total_tasks', 0)}
- Uncompleted Tasks: {metadata.get('uncompleted_tasks', 0)}
- To-Do Tasks: {metadata.get('todo_tasks', 0)}
- In-Progress Tasks: {metadata.get('inprogress_tasks', 0)}
- Overdue Tasks: {metadata.get('overdue_tasks', 0)}
- Max Overdue Days: {metadata.get('max_overdue_days', 0)}

DEVELOPER WORKLOAD:
{json.dumps(metadata.get('developer_breakdown', {}), indent=2)}

AVAILABLE DEVELOPERS:
{json.dumps(metadata.get('available_developers_data', {}), indent=2)}

Generate 3-5 specific, actionable recommendations to reduce uncompleted tasks risk.
Focus on: task prioritization, workload distribution, deadline management, and team efficiency."""

        elif risk_type == 'detected_bugs':
            prompt = f"""{system_context}

RISK TYPE: Detected Bugs

PROJECT METRICS:
- Total Bugs: {metadata.get('total_bugs', 0)}
- To-Do Bugs: {metadata.get('todo_bugs', 0)}
- In-Progress Bugs: {metadata.get('inprogress_bugs', 0)}
- Completed Bugs: {metadata.get('completed_bugs', 0)}
- High Priority Bugs: {metadata.get('high_priority_bugs', 0)}
- Medium Priority Bugs: {metadata.get('medium_priority_bugs', 0)}
- Low Priority Bugs: {metadata.get('low_priority_bugs', 0)}

Generate 3-5 specific, actionable recommendations to reduce bug-related risks.
Focus on: bug prioritization, dedicated bug-fix time, code quality, QA collaboration, and preventive measures."""

        elif risk_type == 'blockers_count':
            prompt = f"""{system_context}

RISK TYPE: Blockers

PROJECT METRICS:
- Total Blockers: {metadata.get('total_blockers', 0)}
- Open Blockers: {metadata.get('open_blockers', 0)}
- Critical Blockers: {metadata.get('critical_blockers', 0)}
- High Priority Blockers: {metadata.get('high_blockers', 0)}
- Medium Priority Blockers: {metadata.get('medium_blockers', 0)}

Generate 3-5 specific, actionable recommendations to resolve blockers and prevent future ones.
Focus on: blocker resolution, dependency management, and process improvements."""

        elif risk_type == 'timeline_conflict':
            prompt = f"""{system_context}

RISK TYPE: Timeline Conflicts

PROJECT METRICS:
{json.dumps(metadata.get('timeline_conflicts', {}), indent=2)}

Generate 3-5 specific, actionable recommendations to resolve timeline conflicts.
Focus on: schedule optimization, resource allocation, and deadline management."""


        elif risk_type == 'developer_availability':
            prompt = f"""{system_context}

RISK TYPE: Developer Availability

PROJECT METRICS:
{json.dumps(metadata.get('developer_breakdown', {}), indent=2)}

Generate 3-5 specific, actionable recommendations to manage developer availability risks.
Focus on: capacity planning, leave management, and workload balancing."""

        elif risk_type == 'task_progress':
            prompt = f"""{system_context}

RISK TYPE: Task Progress

PROJECT METRICS:
{json.dumps(metadata, indent=2)}

Generate 3-5 specific, actionable recommendations to improve task progress and completion rates.
Focus on: task tracking, progress monitoring, bottleneck identification, and velocity improvement."""

        elif risk_type == 'sprint_completion_level':
            prompt = f"""{system_context}

RISK TYPE: Sprint Completion

PROJECT METRICS:
{json.dumps(metadata, indent=2)}

Generate 3-5 specific, actionable recommendations to improve sprint completion rates.
Focus on: sprint planning, velocity optimization, scope management, and team capacity."""

        else:
            # Generic prompt for unknown risk types
            prompt = f"""{system_context}

RISK TYPE: {risk_type}

PROJECT DATA:
{json.dumps(metadata, indent=2)}

Generate 3-5 specific, actionable recommendations to mitigate this risk."""
        
        return prompt
    
    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM and get response"""
        try:
            # Ollama is synchronous, but we wrap in async context
            response = self.llm.invoke(prompt)
            return response
        except Exception as e:
            print(f"âŒ LLM API call failed: {e}")
            raise
    
    def _parse_recommendations(self, response: str) -> List[str]:
        """
        Parse LLM response into list of recommendations.
        Handles different response formats.
        """
        recommendations = []
        
        # Split by lines and clean up
        lines = response.strip().split('\n')
        
        current_recommendation = ""
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                if current_recommendation:
                    recommendations.append(current_recommendation.strip())
                    current_recommendation = ""
                continue
            
            # Check if line starts with number (1., 2., etc.)
            if line and line[0].isdigit() and ('.' in line[:3] or ')' in line[:3]):
                # Save previous recommendation
                if current_recommendation:
                    recommendations.append(current_recommendation.strip())
                
                # Start new recommendation (remove number prefix)
                current_recommendation = line.split('.', 1)[-1].split(')', 1)[-1].strip()
            else:
                # Continue current recommendation
                if current_recommendation:
                    current_recommendation += " " + line
                else:
                    current_recommendation = line
        
        # Add last recommendation
        if current_recommendation:
            recommendations.append(current_recommendation.strip())
        
        # Clean up recommendations
        cleaned = []
        for rec in recommendations:
            # Remove markdown, asterisks, etc.
            rec = rec.replace('**', '').replace('*', '').strip()
            if rec and len(rec) > 10:  # Ignore very short entries
                cleaned.append(rec)
        
        return cleaned

    async def generate_blocker_suggestions(self, blocker_description: str) -> Dict[str, Any]:
        """
        Generate AI-powered suggestions and suggested mentor roles for a given blocker.

        Args:
            blocker_description: The description of the blocker.

        Returns:
            Dict containing 'suggestions' (list of strings) and 'suggested_mentor_role' (string)
        """
        if not self.llm:
            return {
                "suggestions": ["Break down the task into smaller sub-tasks.", "Consult with the team lead."],
                "suggested_mentor_role": "Senior Developer"
            }

        try:
            prompt = f"""You are an expert AI project management consultant.
Analyze the following blocker description and provide actionable recovery steps and the most appropriate senior position to help solve it.

BLOCKER DESCRIPTION:
{blocker_description}

IMPORTANT RULES:
1. Generate EXACTLY 3-4 specific and actionable recovery steps.
2. Suggest EXACTLY ONE senior position/role (e.g., Tech Lead, Senior Developer, DevOps Engineer, Product Owner, Architect) that should support the developer.
3. Keep each suggestion to 1-2 sentences.
4. Return the result in the following JSON format:
{{
  "suggestions": ["...", "...", "..."],
  "suggested_mentor_role": "..."
}}

Generate the JSON response now:"""
            
            response = await self._call_llm(prompt)
            
            # Extract JSON from response
            try:
                # Find JSON block if it exists
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start != -1 and json_end != -1:
                    json_str = response[json_start:json_end]
                    result = json.loads(json_str)
                    return {
                        "suggestions": result.get("suggestions", []),
                        "suggested_mentor_role": result.get("suggested_mentor_role", "Senior Developer")
                    }
            except:
                pass

            # Fallback parsing if JSON parsing fails
            suggestions = self._parse_recommendations(response)
            return {
                "suggestions": suggestions[:3],
                "suggested_mentor_role": "Senior Developer / Tech Lead"
            }

        except Exception as e:
            print(f"â Œ Blocker suggestion generation failed: {e}")
            return {
                "suggestions": ["Consult with the team lead to resolve the dependency."],
                "suggested_mentor_role": "Senior Developer"
            }

    async def generate_delay_suggestions(self, delay_data: Dict[str, Any]) -> List[str]:
        """
        Generate AI-powered recovery suggestions based on delay analysis data.

        Args:
            delay_data: Full delay analysis result from calculate_project_delay()

        Returns:
            List of 4-5 actionable recovery suggestions
        """
        if not self.llm:
            print("âš ï¸ LLM not available, cannot generate delay suggestions")
            return []

        try:
            # Build early warnings summary
            warnings = delay_data.get('early_warnings', [])
            warnings_summary = "; ".join(
                [f"{w.get('type', '')} ({w.get('severity', '')}): {w.get('message', '')}" for w in warnings]
            ) if warnings else "None"

            # Build sprint breakdown summary
            sprints = delay_data.get('sprint_breakdown', [])
            sprint_lines = []
            for s in sprints:
                sprint_lines.append(
                    f"  {s.get('sprint_name')}: {s.get('completed_story_points', 0)}/{s.get('planned_story_points', 0)} SP "
                    f"({s.get('completion_rate', 0):.0f}% completed, status: {s.get('status')})"
                )
            sprint_summary = "\n".join(sprint_lines) if sprint_lines else "No sprint data"

            delay_attribution = delay_data.get('delay_attribution', {})
            primary_cause = delay_attribution.get('primary_cause', 'UNKNOWN')

            prompt = f"""You are an expert Agile project management consultant. \
Analyze the following project delay situation and provide specific, actionable recovery strategies.

PROJECT DELAY ANALYSIS:
- Project: {delay_data.get('project_name')} ({delay_data.get('project_key')})
- Risk Level: {delay_data.get('risk_level')} ({delay_data.get('delay_percentage', 0):.1f}% delay)
- Planned End Date: {delay_data.get('planned_end_date')}
- Forecasted End Date: {delay_data.get('forecasted_end_date')} ({delay_data.get('delay_days', 0):.0f} days overdue)
- Sprint Progress: {delay_data.get('completed_sprints', 0)}/{delay_data.get('total_sprints', 0)} sprints closed
- Story Points: {delay_data.get('completed_story_points', 0)}/{delay_data.get('total_story_points', 0)} completed ({delay_data.get('story_point_completion_rate', 0):.1f}%)
- Actual Velocity: {delay_data.get('actual_velocity', 0):.1f} SP/sprint (expected: {delay_data.get('expected_velocity', 0):.1f})
- Team Availability: {delay_data.get('availability_ratio', 1) * 100:.0f}% (leave hours: {delay_data.get('total_leave_hours', 0):.0f}h of {delay_data.get('total_planned_hours', 0):.0f}h planned)
- Primary Delay Cause: {primary_cause} \
(velocity impact: {delay_attribution.get('velocity_impact_percentage', 0):.0f}%, \
availability: {delay_attribution.get('availability_impact_percentage', 0):.0f}%, \
scope: {delay_attribution.get('scope_impact_percentage', 0):.0f}%)
- Active Warnings: {warnings_summary}

SPRINT BREAKDOWN:
{sprint_summary}

IMPORTANT RULES:
1. Generate EXACTLY 4-5 recovery recommendations
2. Reference actual numbers from the data (velocity, dates, story points, sprint counts)
3. Be specific and immediately actionable â€” no generic advice
4. Number each recommendation (1., 2., 3., etc.)
5. Keep each to 2-3 sentences maximum
6. Focus on the PRIMARY cause: {primary_cause}

Generate the recovery recommendations now:"""

            print(f"ðŸ¤– Generating AI delay suggestions for {delay_data.get('project_name')}...")
            response = await self._call_llm(prompt)
            suggestions = self._parse_recommendations(response)
            print(f"âœ… Generated {len(suggestions)} delay suggestions")
            return suggestions[:5]

        except Exception as e:
            print(f"âŒ Delay suggestion generation failed: {e}")
            return []


# Singleton instance
llm_service = LLMRecommendationService()
