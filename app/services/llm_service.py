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
            print(f"✅ LLM Service initialized with {self.model_name}")
        except Exception as e:
            print(f"⚠️ Failed to initialize LLM: {e}")
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
            print("⚠️ LLM not available, returning empty recommendations")
            return []
        
        try:
            # Build context-specific prompt
            prompt = self._build_prompt(risk_type, project_data, metadata)
            
            # Generate recommendations using LLM
            print(f"🤖 Generating AI recommendations for {risk_type}...")
            response = await self._call_llm(prompt)
            
            # Parse and clean recommendations
            recommendations = self._parse_recommendations(response)
            
            print(f"✅ Generated {len(recommendations)} AI recommendations")
            return recommendations[:5]  # Return max 5
            
        except Exception as e:
            print(f"❌ LLM generation failed: {e}")
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
            print(f"❌ LLM API call failed: {e}")
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


# Singleton instance
llm_service = LLMRecommendationService()
"""
LLM Service for AI-Powered Recommendations using Ollama + LangChain
"""
from typing import Dict, Any, List, Optional
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
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
            print(f"✅ LLM Service initialized with {self.model_name}")
        except Exception as e:
            print(f"⚠️ Failed to initialize LLM: {e}")
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
            print("⚠️ LLM not available, returning empty recommendations")
            return []
        
        try:
            # Build context-specific prompt
            prompt = self._build_prompt(risk_type, project_data, metadata)
            
            # Generate recommendations using LLM
            print(f"🤖 Generating AI recommendations for {risk_type}...")
            response = await self._call_llm(prompt)
            
            # Parse and clean recommendations
            recommendations = self._parse_recommendations(response)
            
            print(f"✅ Generated {len(recommendations)} AI recommendations")
            return recommendations[:5]  # Return max 5
            
        except Exception as e:
            print(f"❌ LLM generation failed: {e}")
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
            print(f"❌ LLM API call failed: {e}")
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


# Singleton instance
llm_service = LLMRecommendationService()
