"""
User Repository

Database operations for users.
"""

import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.db.database import Database
from app.core.logger import logger


class UserRepository:
    """Repository for user database operations"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def create_user(
        self,
        tenant_id: str,
        email: str,
        password_hash: str,
        role: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        status: str = "PENDING_ACTIVATION",
        password_change_required: bool = True
    ) -> Dict[str, Any]:
        """
        Create new user.
        
        Args:
            tenant_id: Tenant ID
            email: User email
            password_hash: Hashed password
            role: User role
            first_name: First name
            last_name: Last name
            status: User status
            password_change_required: Whether password change required
        
        Returns:
            Created user data
        """
        user_id = f"usr-{uuid.uuid4().hex[:16]}"
        
        query = """
            INSERT INTO users (
                USER_ID, TENANT_ID, EMAIL, PASSWORD_HASH, FIRST_NAME, LAST_NAME,
                ROLE, STATUS, PASSWORD_CHANGE_REQUIRED, CREATED_AT, UPDATED_AT
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """
        
        await self.db.execute_query(
            query,
            (user_id, tenant_id, email, password_hash, first_name, last_name,
             role, status, password_change_required),
            commit=True
        )
        
        logger.info(f"User created: {user_id} - {email} - Role: {role}")
        
        return {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "role": role,
            "status": status,
            "password_change_required": password_change_required,
            "created_at": datetime.utcnow().isoformat()
        }
    
    async def get_user_by_email(
        self,
        email: str,
        tenant_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get user by email.
        
        Args:
            email: User email
            tenant_id: Optional tenant ID filter
        
        Returns:
            User data or None
        """
        if tenant_id:
            query = """
                SELECT 
                    u.USER_ID as user_id,
                    u.TENANT_ID as tenant_id,
                    u.EMAIL as email,
                    u.PASSWORD_HASH as password_hash,
                    u.FIRST_NAME as first_name,
                    u.LAST_NAME as last_name,
                    u.ROLE as role,
                    u.STATUS as status,
                    u.PASSWORD_CHANGE_REQUIRED as password_change_required,
                    u.LAST_LOGIN_AT as last_login_at,
                    u.CREATED_AT as created_at,
                    u.UPDATED_AT as updated_at,
                    t.COMPANY_NAME as tenant_name
                FROM users u
                LEFT JOIN tenants t ON u.TENANT_ID = t.TENANT_ID
                WHERE u.EMAIL = %s AND u.TENANT_ID = %s
            """
            params = (email, tenant_id)
        else:
            query = """
                SELECT 
                    u.USER_ID as user_id,
                    u.TENANT_ID as tenant_id,
                    u.EMAIL as email,
                    u.PASSWORD_HASH as password_hash,
                    u.FIRST_NAME as first_name,
                    u.LAST_NAME as last_name,
                    u.ROLE as role,
                    u.STATUS as status,
                    u.PASSWORD_CHANGE_REQUIRED as password_change_required,
                    u.LAST_LOGIN_AT as last_login_at,
                    u.CREATED_AT as created_at,
                    u.UPDATED_AT as updated_at,
                    t.COMPANY_NAME as tenant_name
                FROM users u
                LEFT JOIN tenants t ON u.TENANT_ID = t.TENANT_ID
                WHERE u.EMAIL = %s
            """
            params = (email,)
        
        result = await self.db.execute_query(query, params, fetch_one=True)
        return result
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
        
        Returns:
            User data or None
        """
        query = """
            SELECT 
                u.USER_ID as user_id,
                u.TENANT_ID as tenant_id,
                u.EMAIL as email,
                u.PASSWORD_HASH as password_hash,
                u.FIRST_NAME as first_name,
                u.LAST_NAME as last_name,
                u.ROLE as role,
                u.STATUS as status,
                u.PASSWORD_CHANGE_REQUIRED as password_change_required,
                u.LAST_LOGIN_AT as last_login_at,
                u.CREATED_AT as created_at,
                u.UPDATED_AT as updated_at,
                t.COMPANY_NAME as tenant_name
            FROM users u
            LEFT JOIN tenants t ON u.TENANT_ID = t.TENANT_ID
            WHERE u.USER_ID = %s
        """
        
        result = await self.db.execute_query(query, (user_id,), fetch_one=True)
        return result
    
    async def email_exists_in_tenant(self, email: str, tenant_id: str) -> bool:
        """
        Check if email exists in tenant.
        
        Args:
            email: User email
            tenant_id: Tenant ID
        
        Returns:
            True if exists
        """
        query = """
            SELECT COUNT(*) as count
            FROM users
            WHERE EMAIL = %s AND TENANT_ID = %s
        """
        
        result = await self.db.execute_query(query, (email, tenant_id), fetch_one=True)
        return result and result['count'] > 0
    
    async def update_password(
        self,
        user_id: str,
        password_hash: str,
        clear_password_change_required: bool = True
    ) -> bool:
        """
        Update user password.
        
        Args:
            user_id: User ID
            password_hash: New hashed password
            clear_password_change_required: Clear password change flag
        
        Returns:
            True if updated
        """
        try:
            if clear_password_change_required:
                query = """
                    UPDATE users
                    SET PASSWORD_HASH = %s, PASSWORD_CHANGE_REQUIRED = FALSE,
                        STATUS = 'ACTIVE', UPDATED_AT = NOW()
                    WHERE USER_ID = %s
                """
            else:
                query = """
                    UPDATE users
                    SET PASSWORD_HASH = %s, UPDATED_AT = NOW()
                    WHERE USER_ID = %s
                """
            
            logger.info(f"Updating password for user: {user_id}")
            await self.db.execute_query(query, (password_hash, user_id), commit=True)
            logger.info(f"Password updated successfully for user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating password for user {user_id}: {str(e)}")
            raise
    
    async def update_last_login(self, user_id: str) -> bool:
        """
        Update user last login timestamp.
        
        Args:
            user_id: User ID
        
        Returns:
            True if updated
        """
        query = """
            UPDATE users
            SET LAST_LOGIN_AT = NOW()
            WHERE USER_ID = %s
        """
        
        await self.db.execute_query(query, (user_id,), commit=True)
        return True
    
    async def list_users(
        self,
        tenant_id: str,
        page: int = 1,
        limit: int = 20,
        role: Optional[str] = None,
        status: Optional[str] = None
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        List users in tenant with pagination.
        
        Args:
            tenant_id: Tenant ID
            page: Page number
            limit: Items per page
            role: Filter by role
            status: Filter by status
        
        Returns:
            Tuple of (users list, total count)
        """
        offset = (page - 1) * limit
        
        # Build query with filters
        where_clauses = ["u.TENANT_ID = %s"]
        params = [tenant_id]
        
        if role:
            where_clauses.append("u.ROLE = %s")
            params.append(role)
        
        if status:
            where_clauses.append("u.STATUS = %s")
            params.append(status)
        
        where_sql = " AND ".join(where_clauses)
        
        # Get users
        query = f"""
            SELECT 
                u.USER_ID as user_id,
                u.EMAIL as email,
                u.FIRST_NAME as first_name,
                u.LAST_NAME as last_name,
                u.ROLE as role,
                u.STATUS as status,
                u.LAST_LOGIN_AT as last_login_at,
                u.CREATED_AT as created_at
            FROM users u
            WHERE {where_sql}
            ORDER BY u.CREATED_AT DESC
            LIMIT %s OFFSET %s
        """
        
        users = await self.db.execute_query(
            query,
            tuple(params + [limit, offset]),
            fetch_all=True
        )
        
        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total
            FROM users u
            WHERE {where_sql}
        """
        
        count_result = await self.db.execute_query(
            count_query,
            tuple(params),
            fetch_one=True
        )
        
        total = count_result['total'] if count_result else 0
        
        return users or [], total
    
    async def update_user(
        self,
        user_id: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        role: Optional[str] = None,
        status: Optional[str] = None
    ) -> bool:
        """
        Update user details.
        
        Args:
            user_id: User ID
            first_name: New first name
            last_name: New last name
            role: New role
            status: New status
        
        Returns:
            True if updated
        """
        updates = []
        params = []
        
        if first_name is not None:
            updates.append("first_name = %s")
            params.append(first_name)
        
        if last_name is not None:
            updates.append("last_name = %s")
            params.append(last_name)
        
        if role is not None:
            updates.append("role = %s")
            params.append(role)
        
        if status is not None:
            updates.append("status = %s")
            params.append(status)
        
        if not updates:
            return False
        
        updates.append("updated_at = NOW()")
        params.append(user_id)
        
        query = f"""
            UPDATE users
            SET {', '.join(updates)}
            WHERE USER_ID = %s
        """
        
        await self.db.execute_query(query, tuple(params), commit=True)
        logger.info(f"User updated: {user_id}")
        return True
    
    async def delete_user(self, user_id: str) -> bool:
        """
        Delete user (or mark as inactive).
        
        Args:
            user_id: User ID
        
        Returns:
            True if deleted
        """
        # Soft delete - set status to SUSPENDED
        query = """
            UPDATE users
            SET STATUS = 'SUSPENDED', UPDATED_AT = NOW()
            WHERE USER_ID = %s
        """
        
        await self.db.execute_query(query, (user_id,), commit=True)
        logger.info(f"User deleted (suspended): {user_id}")
        return True
