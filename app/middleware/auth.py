"""
Authentication middleware for FastAPI dependencies
"""

from fastapi import Depends
from typing import Dict, Any

from app.utils.jwt import get_current_user_from_token

# Alias for consistency
get_current_user = get_current_user_from_token


async def get_tenant_db(current_user: Dict[str, Any] = Depends(get_current_user)) -> str:
    """
    Extract tenant database name from current user.
    
    Args:
        current_user: User info from token
        
    Returns:
        Tenant database name (e.g., 'visionexdigital_db')
    """
    tenant_name = current_user.get("tenant_name")
    if not tenant_name:
        raise ValueError("Tenant name not found in user token")
    
    return f"{tenant_name}_db"