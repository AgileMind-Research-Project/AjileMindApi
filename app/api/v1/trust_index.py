"""
Trust Index API Router

Endpoints:
  GET /trust-index/{project_id}  — Calculate and return the full Trust Index
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any

from app.utils.jwt import get_current_user_from_token
from app.services.trust_index_service import trust_index_service
from app.core.logger import logger

router = APIRouter()


@router.get(
    "/{project_id}",
    summary="Calculate Trust Index",
    description=(
        "Calculates the project Trust Index (0–100) using the HDI geometric mean approach "
        "across 6 components: Availability, Velocity Consistency, Scope Stability, "
        "Historical Accuracy, Risk Value, and Delay Value. "
        "A score ≥ 80 means the project is READY TO RELEASE."
    ),
)
async def get_trust_index(
    project_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
) -> Dict[str, Any]:
    """
    Calculate the Trust Index for a project.

    **Access:** All authenticated users.

    **Returns:**
    - `trust_index`: Aggregate score (0–100)
    - `is_ready_to_release`: True if score ≥ 80
    - `release_threshold`: 80 (fixed)
    - `components`: Breakdown of all 6 component scores with formulas
    - `insights`: Actionable recommendations for low-scoring components
    """
    tenant_name = current_user.get("tenant_name")
    if not tenant_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant name not found in token",
        )

    # Check project access
    user_roles = current_user.get("roles", [])
    if not user_roles and current_user.get("role"):
        user_roles = [current_user.get("role")]
    user_projects = current_user.get("projects", [])

    if not any(role in ["ADMIN", "SUPER_ADMIN"] for role in user_roles):
        if project_id not in user_projects:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this project",
            )

    try:
        result = await trust_index_service.calculate_trust_index(
            tenant_name=tenant_name,
            project_id=project_id,
        )
        return {
            "success": True,
            "message": "Trust Index calculated successfully",
            "data": result,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating trust index for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate Trust Index: {e}",
        )
