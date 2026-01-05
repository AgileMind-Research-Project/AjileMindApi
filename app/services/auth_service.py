"""
Authentication Service

Business logic for authentication and user management.
"""

import uuid
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from app.db.database import Database
from app.db.repositories.tenant_user_repository import TenantUserRepository
from app.db.repositories.password_reset_repository import PasswordResetRepository
from app.utils.password import (
    hash_password,
    verify_password,
    validate_password,
    generate_user_password,
    generate_reset_token
)
from app.utils.jwt import create_token_pair, get_user_from_token
from app.utils.domain_extractor import extract_domain_from_email, validate_email_domain
from app.services.email_service import email_service
from app.core.logger import logger, log_auth_event
from app.core.config import settings


class AuthService:
    """Authentication service"""
    
    def __init__(self, db: Database):
        self.db = db
        self.tenant_user_repo = TenantUserRepository(db)
        self.reset_repo = PasswordResetRepository(db)
    
    async def register_tenant(
        self,
        company_name: str,
        email: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Register new tenant from Platform Home.
        
        Creates tenant-specific user table, super admin user, and sends welcome email.
        Users are NOT added to the global users table.
        
        Args:
            company_name: Company name
            email: Admin email
            password: Admin password
        
        Returns:
            Tenant and user data with tokens
        """
        # Validate email domain
        if not validate_email_domain(email):
            log_auth_event("tenant_registration_failed", email=email, reason="invalid_email_domain")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email domain cannot be extracted for tenant isolation"
            )
        
        # Extract domain from email
        domain = extract_domain_from_email(email)
        
        # Table/Database name = domain only (e.g., visionexdigital)
        table_db_name = domain
        
        # Step 1: Check if table already exists (prevent duplicate tenant registration)
        check_table_query = """
            SELECT COUNT(*) as count
            FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = %s
        """
        existing_table = await self.db.execute_query(check_table_query, (table_db_name,), fetch_one=True)
        
        if existing_table and existing_table.get("count", 0) > 0:
            logger.warning(f"Tenant registration failed: Table {table_db_name} already exists for domain {domain}")
            log_auth_event("tenant_registration_failed", email=email, reason="tenant_already_exists")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A tenant for domain '{domain}' already exists. Please contact your administrator."
            )
        
        logger.info(f"Creating new tenant with domain: {domain}, table: {table_db_name}")
        
        # Step 2: Create users table in CENTRALIZED database (table name: domain)
        await self.tenant_user_repo.create_tenant_users_table(
            table_name=table_db_name
        )
        logger.info(f"Created users table in centralized DB: {table_db_name}")
        
        # Step 3: Create NEW DATABASE with same name as the table
        await self.tenant_user_repo.create_tenant_database(
            db_name=table_db_name,
            tenant_name=company_name,
            tenant_email=email
        )
        logger.info(f"Created tenant database: {table_db_name}")
        
        # Hash password
        password_hash = hash_password(password)
        
        # Step 4: Create super admin user in centralized users table (table named domain)
        user = await self.tenant_user_repo.create_tenant_user(
            domain=domain,
            email=email,
            password_hash=password_hash,
            role="SUPER_ADMIN",
            first_name=None,
            last_name=None,
            status="ACTIVE",
            password_change_required=False
        )
        
        # Generate JWT tokens with domain
        token_data = {
            "sub": user["user_id"],
            "email": user["email"],
            "tenant_name": domain,
            "role": user["role"]
        }
        tokens = create_token_pair(token_data)
        
        # Send welcome email
        email_service.send_tenant_welcome_email(
            email=email,
            company_name=company_name,
            tenant_id=domain
        )
        
        log_auth_event(
            "tenant_registered",
            user_id=user["user_id"],
            email=email
        )
        
        return {
            "tenant_name": domain,
            "company_name": company_name,
            "user": {
                "user_id": user["user_id"],
                "email": user["email"],
                "first_name": user.get("first_name"),
                "last_name": user.get("last_name"),
                "role": user["role"]
            },
            "tokens": tokens,
            "redirect_url": f"{settings.AGILEMIND_PLATFORM_URL}/dashboard"
        }
    
    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user and return tokens.
        
        Extracts domain from email, queries tenant-specific table,
        verifies credentials, and includes tenant_name in JWT.
        
        Args:
            email: User email
            password: User password
        
        Returns:
            User data and tokens with tenant_name
        """
        # Validate email domain
        if not validate_email_domain(email):
            log_auth_event("login_failed", email=email, reason="invalid_email_domain")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Extract domain from email
        domain = extract_domain_from_email(email)
        
        # Find users table matching the domain pattern: %_{domain}
        # Example: For domain "sliit", find table like "tn_abc12345_sliit"
        find_table_query = """
            SELECT TABLE_NAME 
            FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME LIKE %s
            LIMIT 1
        """
        table_pattern = f"%{domain}"
        table_result = await self.db.execute_query(find_table_query, (table_pattern,), fetch_one=True)
        
        print(f"Finding table for domain '{domain}' with pattern '{table_pattern}': {table_result}")
        
        if not table_result:
            log_auth_event("login_failed", email=email, reason="tenant_table_not_found")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        table_name = table_result["TABLE_NAME"]
        
        logger.info(f"Found table {table_name} for domain {domain}")
        
        # Get user from centralized users table
        try:
            user = await self.tenant_user_repo.get_user_by_email(table_name, email)
        except Exception as e:
            logger.error(f"Error querying tenant database for domain {domain}: {e}")
            log_auth_event("login_failed", email=email, reason="tenant_table_not_found")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
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
        await self.tenant_user_repo.update_last_login(table_name, user["user_id"])
        
        # Generate tokens with domain and projects
        token_data = {
            "sub": user["user_id"],
            "email": user["email"],
            "tenant_name": domain,
            "role": user["role"],
            "projects": user.get("projects", [])
        }
        tokens = create_token_pair(token_data)
        
        log_auth_event(
            "login_success",
            user_id=user["user_id"],
            email=email
        )
        
        # Extract user data
        return {
            "user": {
                "user_id": user["user_id"],
                "email": user["email"],
                "first_name": user.get("first_name"),
                "last_name": user.get("last_name"),
                "role": user["role"],
                "tenant_name": domain,
                "projects": user.get("projects", [])
            },
            "tokens": tokens,
            "password_change_required": user.get("password_change_required", False)
        }
    
    async def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
        tenant_name: str  # domain
    ) -> Dict[str, Any]:
        """
        Change user password in tenant-specific table.
        
        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password
            tenant_name: Tenant domain name
        
        Returns:
            Success data
        """
        try:
            logger.info(f"Starting password change for user: {user_id}")
            
            # Get user from tenant's database
            user = await self.tenant_user_repo.get_user_by_id(tenant_name, user_id)
            
            if not user:
                logger.warning(f"User not found: {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            logger.info("User found, verifying current password")
            
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
            # Update password in tenant's database  
            await self.tenant_user_repo.update_password(
                table_name=tenant_name,
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
        # Extract domain from email to determine table name
        domain = extract_domain_from_email(email)
        table_name = domain
        
        # Get user from domain-based table
        user = await self.tenant_user_repo.get_user_by_email(table_name, email)
        
        if user:
            # Generate reset token
            reset_token = generate_reset_token()
            
            # Save token to database
            await self.reset_repo.create_reset_token(
                user_id=user["user_id"],
                token=reset_token,
                email=email,
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
        
        # Get user email to extract domain
        # Note: We need email in token_data or another way to get the table name
        # For now, we'll need to get user info from reset token table
        user_email = token_data.get("email")
        if not user_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot determine user tenant from token"
            )
        
        # Extract domain to determine table name
        domain = extract_domain_from_email(user_email)
        table_name = domain
        
        # Hash new password
        new_password_hash = hash_password(new_password)
        
        # Update password in domain-based table
        await self.tenant_user_repo.update_password(
            table_name=table_name,
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
        tenant_name: str,  # domain
        first_name: str,
        last_name: str,
        email: str,
        role: str,
        company_name: str
    ) -> Dict[str, Any]:
        """
        Invite new user to tenant-specific table.
        
        Args:
            tenant_name: Tenant domain name
            first_name: User first name
            last_name: User last name
            email: User email
            role: User role
            company_name: Company name for email
        
        Returns:
            Created user data
        """
        # Check if email already exists in tenant
        exists = await self.tenant_user_repo.email_exists_in_tenant(tenant_name, email)
        
        if exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists in this tenant"
            )
        
        # Generate temporary password
        temporary_password = generate_user_password(first_name, email)
        password_hash = hash_password(temporary_password)
        
        # Create user in tenant-specific table
        user = await self.tenant_user_repo.create_tenant_user(
            domain=tenant_name,
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
            company_name=company_name,
            role=role,
            temporary_password=temporary_password
        )
        
        log_auth_event(
            "user_invited",
            user_id=user["user_id"],
            email=email,
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
        
        # Extract tenant_name (domain) from token
        tenant_name = user_info.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing tenant information"
            )
        
        # Get user from tenant-specific table
        user = await self.tenant_user_repo.get_user_by_id(tenant_name, user_info["user_id"])
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "user_id": user["user_id"],
            "email": user["email"],
            "first_name": user.get("first_name"),
            "last_name": user.get("last_name"),
            "role": user["role"],
            "tenant_name": tenant_name,
            "status": user["status"],
            "projects": user.get("projects", []),
            "last_login_at": user.get("last_login_at"),
            "created_at": user.get("created_at")
        }
