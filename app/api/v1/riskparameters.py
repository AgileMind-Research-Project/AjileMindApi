from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Dict, Any, List
from app.schemas.riskparameters_schema import (
    RiskParameters,
    RiskCalculationResponse
)
from app.services.riskparameters_service import RiskParametersService
from app.services.risk_calculation_service import RiskCalculationService
from app.services.recommendation_service import recommendation_service
from app.utils.jwt import get_current_user_from_token


router = APIRouter(tags=["Risk Parameters"])
service = RiskParametersService()
risk_calc_service = RiskCalculationService()

# Calculate risk for a single parameter
@router.get("/calculate-parameter-risk/{project_id}")
async def calculate_parameter_risk(
    project_id: int, 
    parameter: str = Query(..., description="Risk parameter name"),
    current_user: Dict[str, Any] = Depends(get_current_user_from_token)
):
    """
    Calculate the risk percentage and risk level for a single selected parameter.
    """
    tenant_name = current_user.get("tenant_name")
    if not tenant_name:
        raise HTTPException(
            status_code=400,
            detail="Tenant name not found in token"
        )
    
    result = await risk_calc_service.calculate_project_risk(tenant_name, project_id)
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
async def create_parameters(
    params: RiskParameters,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token)
):
    """
    Create risk parameters for a project.
    Requires authentication and tenant context.
    """
    tenant_name = current_user.get("tenant_name")
    if not tenant_name:
        raise HTTPException(
            status_code=400,
            detail="Tenant name not found in token"
        )
    
    await service.create_parameters(tenant_name, params)
    return {"message": "Risk parameters saved successfully"}


@router.get("/get/{project_id}")
async def get_parameters(
    project_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token)
):
    """
    Get risk parameters for a project.
    Requires authentication and tenant context.
    """
    tenant_name = current_user.get("tenant_name")
    if not tenant_name:
        raise HTTPException(
            status_code=400,
            detail="Tenant name not found in token"
        )
    
    result = await service.get_parameters(tenant_name, project_id)
    if not result:
        raise HTTPException(status_code=404, detail="No parameters found")
    return result


@router.put("/update")
async def update_parameters(
    params: RiskParameters,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token)
):
    """
    Update risk parameters for a project.
    Requires authentication and tenant context.
    """
    tenant_name = current_user.get("tenant_name")
    if not tenant_name:
        raise HTTPException(
            status_code=400,
            detail="Tenant name not found in token"
        )
    
    result = await service.update_parameters(tenant_name, params)
    return {"message": "Risk parameters updated successfully"}


@router.get("/calculate-risk/{project_id}", response_model=RiskCalculationResponse)
async def calculate_project_risk(
    project_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token)
):
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
    tenant_name = current_user.get("tenant_name")
    if not tenant_name:
        raise HTTPException(
            status_code=400,
            detail="Tenant name not found in token"
        )
    
    try:
        result = await risk_calc_service.calculate_project_risk(tenant_name, project_id)
        return RiskCalculationResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate risk: {str(e)}"
        )


@router.get("/recommendations/{project_id}")
async def get_risk_recommendations(
    project_id: int,
    risk_type: str = Query(..., description="Risk parameter name (e.g., 'uncompleted_tasks', 'detected_bugs')"),
    current_user: Dict[str, Any] = Depends(get_current_user_from_token)
) -> Dict[str, Any]:
    """
    Generate AI-powered remediation recommendations for a specific risk type.
    
    This endpoint provides actionable, practical recommendations to reduce
    project risks based on the current project data and risk metrics.
    
    Args:
        project_id: Project ID to generate recommendations for
        risk_type: Type of risk parameter to focus on
        
    Returns:
        Dictionary containing:
            - risk_type: The risk parameter type
            - recommendations: List of 3-5 actionable recommendations
            - generated_at: Timestamp of generation
    """
    tenant_name = current_user.get("tenant_name")
    if not tenant_name:
        raise HTTPException(
            status_code=400,
            detail="Tenant name not found in token"
        )
    
    try:
        print(f"\n{'='*70}")
        print(f"🔍 Recommendations Request:")
        print(f"  Project ID: {project_id}")
        print(f"  Risk Type: {risk_type}")
        print(f"  Tenant: {tenant_name}")
        print(f"{'='*70}")
        
        # First, get the current risk calculation to have context
        print("📊 Fetching risk calculation data...")
        risk_data = await risk_calc_service.calculate_project_risk(tenant_name, project_id)
        print(f"✅ Risk data fetched: {risk_data.get('risk_level')}")
        
        # Verify that the requested risk type is enabled
        breakdown = risk_data.get("breakdown", [])
        print(f"📋 Risk breakdown has {len(breakdown)} parameters")
        
        risk_param = next((item for item in breakdown if item["parameter"] == risk_type), None)
        
        if not risk_param:
            print(f"❌ Risk parameter '{risk_type}' not found in breakdown")
            print(f"   Available parameters: {[item['parameter'] for item in breakdown]}")
            raise HTTPException(
                status_code=404,
                detail=f"Risk parameter '{risk_type}' not found for this project"
            )
        
        if not risk_param.get("enabled"):
            print(f"❌ Risk parameter '{risk_type}' is not enabled")
            raise HTTPException(
                status_code=404,
                detail=f"Risk parameter '{risk_type}' is not enabled for this project"
            )
        
        print(f"✅ Risk parameter '{risk_type}' is enabled")
        
        # Extract project data and metadata for context
        project_data = {
            'project_id': project_id,
            'risk_level': risk_data.get('risk_level'),
            'risk_percentage': risk_data.get('risk_percentage'),
        }
        
        metadata = risk_data.get('metadata', {})
        print(f"📊 Metadata keys: {list(metadata.keys())}")
        
        # Generate recommendations using the recommendation service
        print("🤖 Generating recommendations...")
        recommendations = await recommendation_service.generate_recommendations(
            risk_type=risk_type,
            project_data=project_data,
            metadata=metadata
        )
        
        print(f"✅ Generated {len(recommendations)} recommendations")
        print(f"{'='*70}\n")
        
        # Include available_developers_data in response if it exists
        response = {
            'risk_type': risk_type,
            'recommendations': recommendations,
            'project_id': project_id,
            'generated_at': risk_data.get('calculated_at')
        }
        
        # Add available developers data if available
        if 'available_developers_data' in metadata:
            response['available_developers_data'] = metadata['available_developers_data']
            print(f"📊 Including available_developers_data with {metadata['available_developers_data'].get('available_count', 0)} developers")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"💥 ERROR generating recommendations: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate recommendations: {str(e)}"
        )
