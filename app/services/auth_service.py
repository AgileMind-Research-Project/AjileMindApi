"""
Authentication Service

Business logic for authentication and user management.
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from app.db.database import Database
from app.db.repositories.tenant_repository import TenantRepository
from app.db.repositories.user_repository import UserRepository
from app.db.repositories.password_reset_repository import PasswordResetRepository
from app.utils.password import (
    hash_password,
    verify_password,
    validate_password,
    generate_user_password,
    generate_reset_token
)
from app.utils.jwt import create_token_pair, get_user_from_token
from app.services.email_service import email_service
from app.core.logger import logger, log_auth_event
from app.core.config import settings


class AuthService:
    """Authentication service"""
    
    def __init__(self, db: Database):
        self.db = db
        self.tenant_repo = TenantRepository(db)
        self.user_repo = UserRepository(db)
        self.reset_repo = PasswordResetRepository(db)
    
    async def _create_super_admin_role(self, tenant_id: str, role_id: str) -> None:
        """
        Create Super Admin role for new tenant.
        
        Args:
            tenant_id: Tenant ID
            role_id: Role ID to use
        """
        query = """
            INSERT INTO roles (ROLE_ID, TENANT_ID, NAME, DISPLAY_NAME, DESCRIPTION, PERMISSIONS, IS_SYSTEM_ROLE, CREATED_AT, UPDATED_AT)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """
        
        await self.db.execute_query(
            query,
            (
                role_id,
                tenant_id,
                "SUPER_ADMIN",
                "Super Administrator",
                "Full system access with all permissions",
                '["*"]',  # JSON array of permissions
                False  # Not a system role (tenant-specific)
            ),
            commit=True
        )
        
        logger.info(f"Created Super Admin role for tenant {tenant_id}")
    
    async def register_tenant(
        self,
        company_name: str,
        email: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Register new tenant from Platform Home.
        
        Creates tenant, super admin user, and sends welcome email.
        
        Args:
            company_name: Company name
            email: Admin email
            password: Admin password
        
        Returns:
            Tenant and user data with tokens
        """
        # Check if email already exists (any tenant)
        existing_user = await self.user_repo.get_user_by_email(email)
        if existing_user:
            log_auth_event("tenant_registration_failed", email=email, reason="email_exists")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Company email already registered"
            )
        
        # Create tenant
        tenant = await self.tenant_repo.create_tenant(company_name)
        
        # Create Super Admin role for this tenant
        role_id = f"role_{tenant['tenant_id']}_super_admin"
        await self._create_super_admin_role(tenant["tenant_id"], role_id)
        
        # Hash password
        password_hash = hash_password(password)
        
        # Create super admin user
        user = await self.user_repo.create_user(
            tenant_id=tenant["tenant_id"],
            email=email,
            password_hash=password_hash,
            role="SUPER_ADMIN",
            status="ACTIVE",
            password_change_required=False
        )
        
        # Generate JWT tokens
        token_data = {
            "sub": user["user_id"],
            "email": user["email"],
            "tenant_id": tenant["tenant_id"],
            "role": user["role"]
        }
        tokens = create_token_pair(token_data)
        
        # Send welcome email
        email_service.send_tenant_welcome_email(
            email=email,
            company_name=company_name,
            tenant_id=tenant["tenant_id"]
        )
        
        log_auth_event(
            "tenant_registered",
            user_id=user["user_id"],
            tenant_id=tenant["tenant_id"],
            email=email
        )
        
        return {
            "tenant_id": tenant["tenant_id"],
            "company_name": company_name,
            "user": {
                "user_id": user["user_id"],
                "email": user["email"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "role": user["role"]
            },
            "tokens": tokens,
            "redirect_url": f"{settings.AGILEMIND_PLATFORM_URL}/dashboard"
        }
    
    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user and return tokens.
        
        Args:
            email: User email
            password: User password
        
        Returns:
            User data and tokens
        """
        # Get user
        user = await self.user_repo.get_user_by_email(email)
        
        if not user:
            log_auth_event("login_failed", email=email, reason="user_not_found")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not verify_password(password, user["password_hash"]):
            log_auth_event(
                "login_failed",
                user_id=user["user_id"],
                email=email,
                reason="invalid_password"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if account is active
        if user["status"] == "SUSPENDED":
            log_auth_event("login_failed", user_id=user["user_id"], reason="account_suspended")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is suspended"
            )
        
        # Update last login
        await self.user_repo.update_last_login(user["user_id"])
        
        # Generate tokens
        token_data = {
            "sub": user["user_id"],
            "email": user["email"],
            "tenant_id": user["tenant_id"],
            "role": user["role"]
        }
        tokens = create_token_pair(token_data)
        
        log_auth_event(
            "login_success",
            user_id=user["user_id"],
            email=email,
            tenant_id=user["tenant_id"]
        )
        
        return {
            "user": {
                "user_id": user["user_id"],
                "email": user["email"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "role": user["role"],
                "tenant_id": user["tenant_id"],
                "tenant_name": user.get("tenant_name")
            },
            "tokens": tokens,
            "password_change_required": user.get("password_change_required", False)
        }
    
    async def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str
    ) -> Dict[str, Any]:
        """
        Change user password.
        
        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password
        
        Returns:
            Success data
        """
        try:
            logger.info(f"Starting password change for user: {user_id}")
            
            # Get user
            user = await self.user_repo.get_user_by_id(user_id)
            
            if not user:
                logger.warning(f"User not found: {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            logger.info(f"User found, verifying current password")
            
            # Verify current password
            if not verify_password(current_password, user["password_hash"]):
                logger.warning(f"Incorrect current password for user: {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Current password is incorrect"
                )
            
            # Check new password is different
            if current_password == new_password:
                logger.warning(f"New password same as current for user: {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="New password must be different from current password"
                )
            
            logger.info(f"Hashing new password for user: {user_id}")
            # Hash new password
            new_password_hash = hash_password(new_password)
            
            logger.info(f"Updating password in database for user: {user_id}")
            # Update password
            await self.user_repo.update_password(
                user_id=user_id,
                password_hash=new_password_hash,
                clear_password_change_required=True
            )
            
            logger.info(f"Password changed successfully for user: {user_id}")
            log_auth_event("password_changed", user_id=user_id, email=user["email"])
            
            return {
                "password_updated": True,
                "password_change_required": False
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error changing password for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to change password: {str(e)}"
            )
    
    async def forgot_password(self, email: str) -> bool:
        """
        Initiate password reset process.
        
        Args:
            email: User email
        
        Returns:
            True (always, for security)
        """
        # Get user
        user = await self.user_repo.get_user_by_email(email)
        
        if user:
            # Generate reset token
            reset_token = generate_reset_token()
            
            # Save token to database
            await self.reset_repo.create_reset_token(
                user_id=user["user_id"],
                token=reset_token,
                expires_in_hours=1
            )
            
            # Send reset email
            email_service.send_password_reset_email(
                email=email,
                first_name=user.get("first_name") or "User",
                reset_token=reset_token
            )
            
            log_auth_event("password_reset_requested", user_id=user["user_id"], email=email)
        
        # Always return success (don't reveal if email exists)
        return True
    
    async def reset_password(self, token: str, new_password: str) -> bool:
        """
        Reset password using token.
        
        Args:
            token: Reset token
            new_password: New password
        
        Returns:
            True if successful
        """
        # Validate token
        token_data = await self.reset_repo.get_valid_token(token)
        
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        # Hash new password
        new_password_hash = hash_password(new_password)
        
        # Update password
        await self.user_repo.update_password(
            user_id=token_data["user_id"],
            password_hash=new_password_hash,
            clear_password_change_required=False
        )
        
        # Mark token as used
        await self.reset_repo.mark_token_used(token)
        
        # Invalidate all other tokens for this user
        await self.reset_repo.invalidate_user_tokens(token_data["user_id"])
        
        log_auth_event("password_reset_completed", user_id=token_data["user_id"])
        
        return True
    
    async def invite_user(
        self,
        tenant_id: str,
        first_name: str,
        last_name: str,
        email: str,
        role: str
    ) -> Dict[str, Any]:
        """
        Invite new user to tenant.
        
        Args:
            tenant_id: Tenant ID
            first_name: User first name
            last_name: User last name
            email: User email
            role: User role
        
        Returns:
            Created user data
        """
        # Check if email already exists in tenant
        exists = await self.user_repo.email_exists_in_tenant(email, tenant_id)
        
        if exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists in this tenant"
            )
        
        # Generate temporary password
        temporary_password = generate_user_password(first_name, email)
        password_hash = hash_password(temporary_password)
        
        # Get tenant details
        tenant = await self.tenant_repo.get_tenant_by_id(tenant_id)
        
        # Create user
        user = await self.user_repo.create_user(
            tenant_id=tenant_id,
            email=email,
            password_hash=password_hash,
            role=role,
            first_name=first_name,
            last_name=last_name,
            status="PENDING_ACTIVATION",
            password_change_required=True
        )
        
        # Send welcome email
        email_service.send_user_welcome_email(
            email=email,
            first_name=first_name,
            last_name=last_name,
            company_name=tenant["company_name"],
            role=role,
            temporary_password=temporary_password
        )
        
        log_auth_event(
            "user_invited",
            user_id=user["user_id"],
            email=email,
            tenant_id=tenant_id,
            role=role
        )
        
        return {
            **user,
            "temporary_password": temporary_password,
            "welcome_email_sent": True
        }
    
    async def get_current_user(self, token: str) -> Dict[str, Any]:
        """
        Get current user from token.
        
        Args:
            token: JWT access token
        
        Returns:
            User data
        """
        user_info = get_user_from_token(token)
        
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        user = await self.user_repo.get_user_by_id(user_info["user_id"])
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "user_id": user["user_id"],
            "email": user["email"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "role": user["role"],
            "tenant_id": user["tenant_id"],
            "tenant_name": user.get("tenant_name"),
            "status": user["status"],
            "last_login_at": user.get("last_login_at"),
            "created_at": user.get("created_at")
        }
