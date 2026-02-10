"""
Permission Utilities

Helper functions for checking user roles and permissions.
"""

from typing import Dict, Any, List, Union
from fastapi import HTTPException, status
from app.core.logger import logger


def has_role(user: Dict[str, Any], required_role: str) -> bool:
    """
    Check if user has a specific role.
    
    Args:
        user: User dictionary with roles array
        required_role: Required role name
    
    Returns:
        True if user has the role, False otherwise
    """
    user_roles = user.get("roles", [])
    
    # Handle legacy single role field
    if not user_roles and user.get("role"):
        user_roles = [user.get("role")]
    
    return required_role in user_roles


def has_any_role(user: Dict[str, Any], required_roles: List[str]) -> bool:
    """
    Check if user has any of the specified roles.
    
    Args:
        user: User dictionary with roles array
        required_roles: List of allowed role names
    
    Returns:
        True if user has at least one of the roles, False otherwise
    """
    user_roles = user.get("roles", [])
    
    # Handle legacy single role field
    if not user_roles and user.get("role"):
        user_roles = [user.get("role")]
    
    return any(role in required_roles for role in user_roles)


def is_super_admin(user: Dict[str, Any]) -> bool:
    """
    Check if user is a Super Admin.
    Super Admin has full access to everything and bypasses all permission checks.
    
    Args:
        user: User dictionary with roles array
    
    Returns:
        True if user is Super Admin, False otherwise
    """
    return has_role(user, "SUPER_ADMIN")


def require_role(user: Dict[str, Any], required_role: Union[str, List[str]]) -> None:
    """
    Check if user has required role(s), raise HTTPException if not.
    Super Admin bypasses all checks.
    
    Args:
        user: User dictionary with roles array
        required_role: Single role string or list of allowed roles
    
    Raises:
        HTTPException: 403 Forbidden if user doesn't have required permissions
    """
    # Super Admin bypasses all permission checks
    if is_super_admin(user):
        logger.debug(f"Super Admin {user.get('user_id')} accessing resource - permission granted")
        return
    
    # Check if it's a single role or list of roles
    if isinstance(required_role, str):
        if not has_role(user, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {required_role}"
            )
    elif isinstance(required_role, list):
        if not has_any_role(user, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required one of roles: {', '.join(required_role)}"
            )
    else:
        raise ValueError("required_role must be string or list of strings")
    
    logger.debug(f"User {user.get('user_id')} permission check passed")


def require_admin(user: Dict[str, Any]) -> None:
    """
    Require user to be Admin or Super Admin.
    
    Args:
        user: User dictionary with roles array
    
    Raises:
        HTTPException: 403 Forbidden if user is not Admin or Super Admin
    """
    require_role(user, ["ADMIN", "SUPER_ADMIN"])


def require_super_admin(user: Dict[str, Any]) -> None:
    """
    Require user to be Super Admin.
    
    Args:
        user: User dictionary with roles array
    
    Raises:
        HTTPException: 403 Forbidden if user is not Super Admin
    """
    if not is_super_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin access required"
        )


def get_user_roles_list(user: Dict[str, Any]) -> List[str]:
    """
    Get list of user's roles, handling both new array and legacy single role format.
    
    Args:
        user: User dictionary
    
    Returns:
        List of role names
    """
    roles = user.get("roles", [])
    
    # Handle legacy single role field
    if not roles and user.get("role"):
        roles = [user.get("role")]
    
    return roles


def can_edit_user_roles(current_user: Dict[str, Any], target_user: Dict[str, Any]) -> bool:
    """
    Check if current user can edit target user's roles.
    Rules:
    - Super Admin can edit anyone except other Super Admins
    - Admin can edit non-Admin and non-Super Admin users
    - No one can edit their own roles
    
    Args:
        current_user: The user attempting to make changes
        target_user: The user being edited
    
    Returns:
        True if allowed, False otherwise
    """
    # Can't edit your own roles
    if current_user.get("user_id") == target_user.get("user_id"):
        return False
    
    target_roles = get_user_roles_list(target_user)
    
    # Can't edit Super Admin users unless you're also Super Admin
    if "SUPER_ADMIN" in target_roles:
        return is_super_admin(current_user)
    
    # Super Admin can edit anyone (except other super admins, checked above)
    if is_super_admin(current_user):
        return True
    
    # Admin can edit users who are not Admin or Super Admin
    if has_role(current_user, "ADMIN"):
        return "ADMIN" not in target_roles and "SUPER_ADMIN" not in target_roles
    
    # Others can't edit roles
    return False
