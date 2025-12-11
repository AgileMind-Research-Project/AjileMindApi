from fastapi import APIRouter, HTTPException, Query
from app.schemas.riskparameters_schema import (
    RiskParameters,
    RiskCalculationResponse
)
from app.services.riskparameters_service import RiskParametersService
from app.services.risk_calculation_service import RiskCalculationService


router = APIRouter(tags=["Risk Parameters"])
service = RiskParametersService()
risk_calc_service = RiskCalculationService()

# Calculate risk for a single parameter
@router.get("/calculate-parameter-risk/{project_id}")
async def calculate_parameter_risk(project_id: int, parameter: str = Query(..., description="Risk parameter name")):
    """
    Calculate the risk percentage and risk level for a single selected parameter.
    """
    result = await risk_calc_service.calculate_project_risk(project_id)
    breakdown = result.get("breakdown", [])
    param_info = next((item for item in breakdown if item["parameter"] == parameter), None)
    if not param_info:
        raise HTTPException(status_code=404, detail=f"Parameter '{parameter}' not found or not enabled for this project.")
    risk_score = param_info["risk_score"] or 0.0
    risk_percentage = round(risk_score * 100, 2)
    # Determine risk level for this parameter
    if risk_score < 0.25:
        risk_level = "LOW"
    elif risk_score < 0.50:
        risk_level = "MEDIUM"
    elif risk_score < 0.75:
        risk_level = "HIGH"
    else:
        risk_level = "CRITICAL"
    return {
        "project_id": project_id,
        "parameter": parameter,
        "risk_percentage": risk_percentage,
        "risk_level": risk_level
    }


@router.post("/create")
async def create_parameters(params: RiskParameters):
    await service.create_parameters(params)
    return {"message": "Risk parameters saved successfully"}


@router.get("/get/{project_id}")
async def get_parameters(project_id: int):
    result = await service.get_parameters(project_id)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No parameters found")
    return result


@router.put("/update")
async def update_parameters(params: RiskParameters):
    result = await service.update_parameters(params)
    return {"message": "Risk parameters updated successfully"}


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