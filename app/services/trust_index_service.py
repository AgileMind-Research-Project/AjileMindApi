"""
Trust Index Service

Calculates a holistic project trust score (0–100) using the HDI approach:
Geometric Mean of 6 component scores, each floored at 1 to prevent collapse.

Components:
  1. Availability           - Team leave impact (from delay service)
  2. Velocity Consistency   - Sprint-to-sprint velocity stability
  3. Scope Stability        - How much scope has grown vs plan
  4. Historical Accuracy    - Avg completion rate of completed sprints
  5. Risk Value             - Inverted overall risk score
  6. Delay Value            - Inverted overall delay score

Release Gate: Trust Index >= 80 → READY TO RELEASE
"""

import math
import logging
from typing import Dict, Any, List, Optional

from app.db.database import db
from app.services.risk_calculation_service import RiskCalculationService
from app.services.delay_calculation_service import DelayCalculationService
from fastapi import HTTPException

logger = logging.getLogger(__name__)

RELEASE_THRESHOLD = 80.0  # Fixed release readiness threshold


class TrustIndexService:
    """Calculates the Trust Index for a project using geometric mean (HDI approach)."""

    FLOOR = 1.0  # Minimum score for any component (prevents geometric collapse)

    def __init__(self):
        self.risk_service = RiskCalculationService()
        self.delay_service = DelayCalculationService(db)

   

    async def calculate_trust_index(
        self, tenant_name: str, project_id: int
    ) -> Dict[str, Any]:
        """
        Calculate the full Trust Index for a project.

        Returns a dict with:
          - trust_index (0–100, geometric mean with floor=1)
          - components (6 individual scores + names + formulas)
          - is_ready_to_release (bool)
          - release_threshold (80)
          - insights (list of actionable messages when score < threshold)
        """
        try:
            # ── 1. Collect raw data from existing services ──────────────
            risk_data = await self._safe_risk_data(tenant_name, project_id)
            delay_data = await self._safe_delay_data(project_id, tenant_name)

            # ── 2. Compute the 6 component scores ──────────────────────
            components = self._compute_components(risk_data, delay_data)

            # ── 3. Geometric Mean with floor=1 ─────────────────────────
            trust_index = self._geometric_mean(
                [c["score"] for c in components]
            )

            # ── 4. Release gate ─────────────────────────────────────────
            is_ready = trust_index >= RELEASE_THRESHOLD

            # ── 5. Insights when trust is low ──────────────────────────
            insights = self._generate_insights(components, trust_index, is_ready)

            return {
                "project_id": project_id,
                "trust_index": round(trust_index, 2),
                "release_threshold": RELEASE_THRESHOLD,
                "is_ready_to_release": is_ready,
                "components": components,
                "insights": insights,
                "calculation_method": "Geometric Mean (HDI approach, floor=1)",
                "num_components": len(components),
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error calculating trust index for project {project_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to calculate trust index: {e}")

    # ------------------------------------------------------------------ #
    #  Component scorers                                                   #
    # ------------------------------------------------------------------ #

    def _compute_components(
        self,
        risk_data: Optional[Dict[str, Any]],
        delay_data: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Compute all 6 component scores (0–100, floored at FLOOR)."""

        components = []

        # 1. Availability -----------------------------------------------
        availability_score = self.FLOOR
        availability_raw = 0.0
        if delay_data:
            ratio = delay_data.get("availability_ratio", 0) or 0
            availability_raw = round(ratio * 100, 2)
            availability_score = max(self.FLOOR, availability_raw)

        components.append({
            "name": "Team Availability",
            "key": "availability",
            "score": round(availability_score, 2),
            "raw_value": availability_raw,
            "unit": "%",
            "description": "Percentage of planned sprint hours actually available (not taken as leave)",
            "formula": "availability_ratio × 100",
        })

        # 2. Velocity Consistency ---------------------------------------
        velocity_score = self.FLOOR
        velocity_cv = 0.0
        if delay_data:
            velocity_score, velocity_cv = self._score_velocity_consistency(delay_data)
            velocity_score = max(self.FLOOR, velocity_score)

        components.append({
            "name": "Velocity Consistency",
            "key": "velocity_consistency",
            "score": round(velocity_score, 2),
            "raw_value": round(velocity_cv, 2),
            "unit": "CV%",
            "description": "How consistent sprint velocity is (lower coefficient of variation = higher trust)",
            "formula": "max(1, 100 − (std_dev / mean_velocity) × 100)",
        })

        # 3. Scope Stability --------------------------------------------
        scope_score = self.FLOOR
        scope_change_pct = 0.0
        if delay_data and delay_data.get("scope_analysis"):
            scope_change_pct = delay_data["scope_analysis"].get("scope_change_percentage", 0) or 0
            scope_raw = max(0, 100 - abs(scope_change_pct))
            scope_score = max(self.FLOOR, scope_raw)

        components.append({
            "name": "Scope Stability",
            "key": "scope_stability",
            "score": round(scope_score, 2),
            "raw_value": round(scope_change_pct, 2),
            "unit": "% change",
            "description": "How well the project scope has stayed on plan (lower scope creep = higher trust)",
            "formula": "max(1, 100 − |scope_change_percentage|)",
        })

        # 4. Historical Accuracy ----------------------------------------
        hist_score = self.FLOOR
        hist_avg = 0.0
        if risk_data:
            hist_score, hist_avg = self._score_historical_accuracy(risk_data)
            hist_score = max(self.FLOOR, hist_score)

        components.append({
            "name": "Historical Accuracy",
            "key": "historical_accuracy",
            "score": round(hist_score, 2),
            "raw_value": round(hist_avg, 2),
            "unit": "%",
            "description": "Average sprint completion rate across all completed sprints",
            "formula": "avg(completed_hours / estimated_hours) × 100 for completed sprints",
        })

        # 5. Risk Value -------------------------------------------------
        risk_score_val = self.FLOOR
        risk_pct = 100.0
        if risk_data:
            risk_pct = risk_data.get("risk_percentage", 100) or 100
            risk_raw = max(0, 100 - risk_pct)
            risk_score_val = max(self.FLOOR, risk_raw)

        components.append({
            "name": "Risk Value",
            "key": "risk_value",
            "score": round(risk_score_val, 2),
            "raw_value": round(risk_pct, 2),
            "unit": "% risk",
            "description": "Inverted overall risk score — lower project risk means higher trust",
            "formula": "max(1, 100 − risk_percentage)",
        })

        # 6. Delay Value ------------------------------------------------
        delay_score_val = self.FLOOR
        delay_pct = 100.0
        if delay_data:
            delay_pct = delay_data.get("delay_percentage", 100) or 100
            delay_raw = max(0, 100 - delay_pct)
            delay_score_val = max(self.FLOOR, delay_raw)

        components.append({
            "name": "Delay Value",
            "key": "delay_value",
            "score": round(delay_score_val, 2),
            "raw_value": round(delay_pct, 2),
            "unit": "% delay",
            "description": "Inverted delay percentage — less project delay means higher trust",
            "formula": "max(1, 100 − delay_percentage)",
        })

        return components

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _geometric_mean(self, scores: List[float]) -> float:
        """
        HDI-style geometric mean with floor=1.
        Applies floor to each score before multiplication to prevent collapse.
        """
        floored = [max(self.FLOOR, s) for s in scores]
        product = 1.0
        for s in floored:
            product *= s
        return product ** (1.0 / len(floored))

    def _score_velocity_consistency(self, delay_data: Dict[str, Any]):
        """
        Coefficient of Variation of sprint velocities.
        CV = std_dev / mean; lower = more consistent = higher trust.
        Returns (score 0–100, cv_percentage).
        """
        sprint_breakdown = delay_data.get("sprint_breakdown", [])
        velocities = [
            s.get("velocity", 0) or 0
            for s in sprint_breakdown
            if (s.get("status") or "").lower() == "closed"
        ]

        if len(velocities) < 2:
            # Not enough data — treat as neutral (50)
            return 50.0, 0.0

        mean_v = sum(velocities) / len(velocities)
        if mean_v == 0:
            return self.FLOOR, 0.0

        variance = sum((v - mean_v) ** 2 for v in velocities) / len(velocities)
        std_dev = math.sqrt(variance)
        cv = (std_dev / mean_v) * 100  # As percentage

        score = max(0.0, 100.0 - cv)
        return score, cv

    def _score_historical_accuracy(self, risk_data: Dict[str, Any]):
        """
        Average sprint completion rate for completed sprints only.
        Returns (score 0–100, avg_completion_percentage).
        """
        breakdown = (risk_data.get("metadata") or {}).get("sprint_progress_breakdown", [])
        completed = [
            s for s in breakdown
            if (s.get("sprint_status") or "").lower() == "closed"
        ]

        if not completed:
            return 50.0, 0.0  # No data — neutral

        avg_completion = sum(s.get("completion_percentage", 0) or 0 for s in completed) / len(completed)
        return min(100.0, avg_completion), avg_completion

    def _generate_insights(
        self,
        components: List[Dict[str, Any]],
        trust_index: float,
        is_ready: bool,
    ) -> List[Dict[str, str]]:
        """Generate actionable insight messages for low-scoring components."""

        LOW_THRESHOLD = 60.0
        insights = []

        if is_ready:
            return insights  # No insights needed when ready

        component_insights = {
            "availability": {
                "title": "Low Team Availability",
                "message": "Team availability is below 60%. A high volume of leave hours is reducing effective capacity.",
                "recommendation": "Review upcoming leave schedules, redistribute workload, or adjust sprint commitments to match actual availability.",
            },
            "velocity_consistency": {
                "title": "Inconsistent Sprint Velocity",
                "message": "Team velocity varies significantly across sprints, indicating unpredictable delivery pace.",
                "recommendation": "Investigate causes of velocity spikes and drops. Stabilise sprint planning, review blockers, and ensure consistent team composition.",
            },
            "scope_stability": {
                "title": "High Scope Creep",
                "message": "Project scope has grown significantly from the original plan, adding unplanned work.",
                "recommendation": "Enforce a change control process. Evaluate new requirements carefully before adding to the backlog, and communicate timeline impact to stakeholders.",
            },
            "historical_accuracy": {
                "title": "Poor Sprint Completion Rate",
                "message": "Completed sprints are finishing with a low average completion rate, meaning work is regularly being carried over.",
                "recommendation": "Reduce sprint commitments to match realistic capacity. Conduct retrospectives to identify why tasks are not finishing within the sprint.",
            },
            "risk_value": {
                "title": "High Project Risk",
                "message": "The overall risk score is elevated, indicating significant unresolved issues across risk parameters.",
                "recommendation": "Review the Risk Management dashboard for specific risk parameters. Prioritise resolving critical bugs, blockers, and overdue tasks.",
            },
            "delay_value": {
                "title": "Significant Project Delay",
                "message": "The project is forecasted to be significantly delayed beyond its planned end date.",
                "recommendation": "Review the Delay Management dashboard. Consider scope reduction, adding team capacity, or renegotiating the deadline with stakeholders.",
            },
        }

        for comp in components:
            if comp["score"] < LOW_THRESHOLD:
                key = comp["key"]
                if key in component_insights:
                    insights.append({
                        "component": comp["name"],
                        "score": str(round(comp["score"], 1)),
                        **component_insights[key],
                    })

        # Sort worst first
        insights.sort(key=lambda x: float(x["score"]))
        return insights

    # ------------------------------------------------------------------ #
    #  Safe data fetchers                                                  #
    # ------------------------------------------------------------------ #

    async def _safe_risk_data(
        self, tenant_name: str, project_id: int
    ) -> Optional[Dict[str, Any]]:
        """Fetch risk data, returning None on failure."""
        try:
            return await self.risk_service.calculate_project_risk(tenant_name, project_id)
        except Exception as e:
            logger.warning(f"Could not fetch risk data for project {project_id}: {e}")
            return None

    async def _safe_delay_data(
        self, project_id: int, tenant_name: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch delay data, returning None on failure."""
        try:
            return await self.delay_service.calculate_project_delay(project_id, tenant_name)
        except Exception as e:
            logger.warning(f"Could not fetch delay data for project {project_id}: {e}")
            return None


trust_index_service = TrustIndexService()
