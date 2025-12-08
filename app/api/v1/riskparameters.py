from fastapi import APIRouter, HTTPException
from app.schemas.riskparameters_schema import (
    RiskParameters,
    RiskCalculationResponse
)
from app.services.riskparameters_service import RiskParametersService
from app.services.risk_calculation_service import RiskCalculationService


router = APIRouter(tags=["Risk Parameters"])
service = RiskParametersService()
risk_calc_service = RiskCalculationService()


@router.post("/create")
async def create_parameters(params: RiskParameters):
    return await service.create_parameters(params)


@router.get("/get/{project_id}")
async def get_parameters(project_id: int):
    result = await service.get_parameters(project_id)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No parameters found")
    return result


@router.put("/update")
async def update_parameters(params: RiskParameters):
    return await service.update_parameters(params)


@router.get("/calculate-risk/{project_id}", response_model=RiskCalculationResponse)
async def calculate_project_risk(project_id: int):
    """
    Calculate total risk score for a project.
    
    This endpoint calculates the risk score based on selected parameters
    and their weights configured by the Project Manager.
    
    Returns:
        - Total risk score (0.0 - 1.0)
        - Risk level (LOW, MEDIUM, HIGH, CRITICAL)
        - Detailed breakdown for each parameter
        - Project metadata
    """
    try:
        result = await risk_calc_service.calculate_project_risk(project_id)
        return RiskCalculationResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate risk: {str(e)}"
        )