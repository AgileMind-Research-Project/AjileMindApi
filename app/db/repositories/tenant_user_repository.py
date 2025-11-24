"""
Tenant User Repository

Dynamic repository for tenant-specific user tables.
Each tenant has their own user table: tenant_{domain}_users
"""

import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.db.database import Database
from app.core.logger import logger
from app.utils.domain_extractor import get_tenant_table_name, extract_domain_from_email
import json


class TenantUserRepository:
    """Repository for tenant-specific user database operations"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def create_tenant_in_registry(self, tenant_id: str, domain: str, company_name: str, admin_email: str) -> bool:
        """
        Create tenant entry in centralized tenants table.
        
        Args:
            tenant_id: Unique tenant identifier (e.g., tn-abc123)
            domain: Extracted domain (e.g., sliit)
            company_name: Company name
            admin_email: Admin email
        
        Returns:
            True if created successfully
        """
        try:
            query = """
                INSERT INTO tenants (tenant_id, company_name, status, created_at, updated_at)
                VALUES (%s, %s, 'ACTIVE', NOW(), NOW())
                ON DUPLICATE KEY UPDATE updated_at = NOW()
            """
            await self.db.execute_query(query, (tenant_id, company_name), commit=True)
            logger.info(f"Created tenant in centralized tenants table: {tenant_id} - {company_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create tenant in tenants table: {e}")
            raise
    
    async def create_tenant_users_table(self, table_name: str) -> bool:
        """
        Create users table in centralized database.
        Table name format: {domain} (e.g., visionexdigital)
        
        Args:
            table_name: Table name (domain only)
        
        Returns:
            True if created successfully
        """
        try:
            query = f"""
                CREATE TABLE IF NOT EXISTS `{table_name}` (
                    `id` INT AUTO_INCREMENT PRIMARY KEY,
                    `user_id` VARCHAR(50) UNIQUE NOT NULL,
                    `email` VARCHAR(255) UNIQUE NOT NULL,
                    `password_hash` VARCHAR(255) NOT NULL,
                    `first_name` VARCHAR(100),
                    `last_name` VARCHAR(100),
                    `role` VARCHAR(50) NOT NULL DEFAULT 'USER',
                    `status` ENUM('ACTIVE', 'SUSPENDED', 'PENDING_ACTIVATION') DEFAULT 'PENDING_ACTIVATION',
                    `password_change_required` BOOLEAN DEFAULT TRUE,
                    `last_login_at` DATETIME NULL,
                    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX `idx_email` (`email`),
                    INDEX `idx_user_id` (`user_id`),
                    INDEX `idx_status` (`status`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            await self.db.execute_query(query, commit=True)
            logger.info(f"Created users table in centralized DB: {table_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create users table {table_name}: {e}")
            raise
    
    async def create_tenant_database(self, db_name: str, tenant_name: str, tenant_email: str) -> bool:
        """
        Create separate database for tenant with tenant_info table.
        Database name = domain (e.g., visionexdigital)
        
        Args:
            db_name: Database name (domain)
            tenant_name: Tenant/company name
            tenant_email: Tenant admin email
        
        Returns:
            True if database and table created successfully
        """
        
        try:
            # Create database
            create_db_query = f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            await self.db.execute_query(create_db_query, commit=True)
            logger.info(f"Created database: {db_name}")
            
            # Create tenant_info table
            tenant_info_query = f"""
                CREATE TABLE IF NOT EXISTS `{db_name}`.`tenant_info` (
                    `id` INT AUTO_INCREMENT PRIMARY KEY,
                    `domain` VARCHAR(100) UNIQUE NOT NULL,
                    `tenant_name` VARCHAR(255) NOT NULL,
                    `tenant_email` VARCHAR(255) NOT NULL,
                    `tenant_status` ENUM('ACTIVE', 'SUSPENDED', 'INACTIVE') DEFAULT 'ACTIVE',
                    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX `idx_domain` (`domain`),
                    INDEX `idx_status` (`tenant_status`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            await self.db.execute_query(tenant_info_query, commit=True)
            logger.info(f"Created tenant_info table in {db_name}")
            
            # Insert tenant info (use db_name as domain identifier)
            insert_tenant_query = f"""
                INSERT INTO `{db_name}`.`tenant_info` (domain, tenant_name, tenant_email, tenant_status)
                VALUES (%s, %s, %s, 'ACTIVE')
                ON DUPLICATE KEY UPDATE tenant_name = VALUES(tenant_name), tenant_email = VALUES(tenant_email)
            """
            await self.db.execute_query(insert_tenant_query, (db_name, tenant_name, tenant_email), commit=True)
            logger.info(f"Inserted tenant info for {db_name}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to create tenant database {db_name}: {e}")
            raise
    
    async def create_tenant_user(
        self,
        domain: str,
        email: str,
        password_hash: str,
        role: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        status: str = "PENDING_ACTIVATION",
        password_change_required: bool = True
    ) -> Dict[str, Any]:
        """
        Create user in centralized users table.
        
        Args:
            domain: Company domain (table name)
            email: User email
            password_hash: Hashed password
            role: User role
            first_name: First name
            last_name: Last name
            status: User status
            password_change_required: Require password change
        
        Returns:
            Created user data
        """
        user_id = f"usr-{uuid.uuid4().hex[:16]}"
        
        # Table name in centralized DB (just domain, e.g., visionexdigital)
        table_name = domain
        
        # Insert into centralized users table
        query = f"""
            INSERT INTO `{table_name}` (
                user_id, email, password_hash, 
                first_name, last_name, role, status, 
                password_change_required, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """
        
        await self.db.execute_query(
            query,
            (user_id, email, password_hash, 
             first_name, last_name, role, status, password_change_required),
            commit=True
        )
        
        logger.info(f"User created in centralized {table_name} table: {user_id} - {email}")
        
        return {
            "user_id": user_id,
            "email": email,
            "role": role,
            "first_name": first_name,
            "last_name": last_name,
            "status": status,
            "password_change_required": password_change_required,
            "created_at": datetime.now().isoformat()
        }
    
    async def get_user_by_email(
        self,
        table_name: str,
        email: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get user by email from centralized users table.
        
        Args:
            table_name: Table name in centralized DB (e.g., tn_abc123_sliit)
            email: User email
        
        Returns:
            User data or None
        """
        query = f"""
            SELECT 
                user_id,
                email,
                password_hash,
                first_name,
                last_name,
                role,
                status,
                password_change_required,
                last_login_at,
                created_at,
                updated_at
            FROM `{table_name}`
            WHERE email = %s
        """
        
        result = await self.db.execute_query(query, (email,), fetch_one=True)
        
        if result and result.get('user_data'):
            try:
                # Parse JSON user_data if it's a string
                if isinstance(result['user_data'], str):
                    result['user_data'] = json.loads(result['user_data'])
            except json.JSONDecodeError:
                result['user_data'] = {}
        
        return result
    
    async def get_user_by_id(
        self,
        table_name: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get user by ID from centralized users table.
        
        Args:
            table_name: Table name in centralized DB (e.g., tn_abc123_sliit)
            user_id: User ID
        
        Returns:
            User data or None
        """
        query = f"""
            SELECT 
                user_id,
                email,
                password_hash,
                first_name,
                last_name,
                role,
                status,
                password_change_required,
                last_login_at,
                created_at,
                updated_at
            FROM `{table_name}`
            WHERE user_id = %s
        """
        
        result = await self.db.execute_query(query, (user_id,), fetch_one=True)
        
        if result and result.get('user_data'):
            try:
                if isinstance(result['user_data'], str):
                    result['user_data'] = json.loads(result['user_data'])
            except json.JSONDecodeError:
                result['user_data'] = {}
        
        return result
    
    async def update_password(
        self,
        table_name: str,
        user_id: str,
        password_hash: str,
        clear_password_change_required: bool = True
    ) -> bool:
        """
        Update user password in centralized users table.
        
        Args:
            table_name: Table name in centralized DB (e.g., tn_abc123_sliit)
            user_id: User ID
            password_hash: New hashed password
            clear_password_change_required: Clear password change flag
        
        Returns:
            True if updated
        """
        try:
            if clear_password_change_required:
                query = f"""
                    UPDATE `{table_name}`
                    SET password_hash = %s, password_change_required = FALSE,
                        status = 'ACTIVE', updated_at = NOW()
                    WHERE user_id = %s
                """
            else:
                query = f"""
                    UPDATE `{table_name}`
                    SET password_hash = %s, updated_at = NOW()
                    WHERE user_id = %s
                """
            
            logger.info(f"Updating password for user in {table_name} table: {user_id}")
            await self.db.execute_query(query, (password_hash, user_id), commit=True)
            logger.info(f"Password updated successfully for user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating password for user {user_id}: {str(e)}")
            raise
    
    async def update_last_login(
        self,
        table_name: str,
        user_id: str
    ) -> bool:
        """
        Update user last login timestamp in centralized users table.
        
        Args:
            table_name: Table name in centralized DB
            user_id: User ID
        
        Returns:
            True if updated
        """
        query = f"""
            UPDATE `{table_name}`
            SET last_login_at = NOW()
            WHERE user_id = %s
        """
        
        await self.db.execute_query(query, (user_id,), commit=True)
        return True
    
    async def update_user_data(
        self,
        domain: str,
        user_id: str,
        user_data: Dict[str, Any]
    ) -> bool:
        """
        Update user_data JSON field in tenant-specific table.
        
        Args:
            domain: Company domain
            user_id: User ID
            user_data: New user data dictionary
        
        Returns:
            True if updated
        """
        table_name = get_tenant_table_name(domain)
        user_data_json = json.dumps(user_data)
        
        query = f"""
            UPDATE `{table_name}`
            SET user_data = %s, updated_at = NOW()
            WHERE user_id = %s
        """
        
        await self.db.execute_query(query, (user_data_json, user_id), commit=True)
        logger.info(f"User data updated for {user_id} in {table_name}")
        return True
    
    async def update_user_status(
        self,
        domain: str,
        user_id: str,
        status: str
    ) -> bool:
        """
        Update user status in tenant-specific table.
        
        Args:
            domain: Company domain
            user_id: User ID
            status: New status (ACTIVE, SUSPENDED, PENDING_ACTIVATION)
        
        Returns:
            True if updated
        """
        table_name = get_tenant_table_name(domain)
        
        query = f"""
            UPDATE `{table_name}`
            SET status = %s, updated_at = NOW()
            WHERE user_id = %s
        """
        
        await self.db.execute_query(query, (status, user_id), commit=True)
        logger.info(f"User status updated to {status} for {user_id} in {table_name}")
        return True
    
    async def list_tenant_users(
        self,
        domain: str,
        page: int = 1,
        limit: int = 20,
        role: Optional[str] = None,
        status: Optional[str] = None
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        List users in tenant-specific table with pagination.
        
        Args:
            domain: Company domain
            page: Page number
            limit: Items per page
            role: Filter by role
            status: Filter by status
        
        Returns:
            Tuple of (users list, total count)
        """
        table_name = get_tenant_table_name(domain)
        offset = (page - 1) * limit
        
        # Build query with filters
        where_clauses = []
        params = []
        
        if role:
            where_clauses.append("role = %s")
            params.append(role)
        
        if status:
            where_clauses.append("status = %s")
            params.append(status)
        
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        # Get users
        query = f"""
            SELECT 
                tenant_id,
                user_id,
                email,
                role,
                user_data,
                status,
                last_login_at,
                created_at
            FROM `{table_name}`
            {where_sql}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        
        users = await self.db.execute_query(
            query,
            tuple(params + [limit, offset]),
            fetch_all=True
        )
        
        # Parse user_data JSON for each user
        if users:
            for user in users:
                if user.get('user_data'):
                    try:
                        if isinstance(user['user_data'], str):
                            user['user_data'] = json.loads(user['user_data'])
                    except json.JSONDecodeError:
                        user['user_data'] = {}
        
        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total
            FROM `{table_name}`
            {where_sql}
        """
        
        count_result = await self.db.execute_query(
            count_query,
            tuple(params),
            fetch_one=True
        )
        
        total = count_result['total'] if count_result else 0
        
        return users or [], total
    
    async def email_exists_in_tenant(
        self,
        domain: str,
        email: str
    ) -> bool:
        """
        Check if email exists in tenant-specific table.
        
        Args:
            domain: Company domain
            email: User email
        
        Returns:
            True if exists
        """
        table_name = get_tenant_table_name(domain)
        
        query = f"""
            SELECT COUNT(*) as count
            FROM `{table_name}`
            WHERE email = %s
        """
        
        result = await self.db.execute_query(query, (tenant_id, email), fetch_one=True)
        return result and result['count'] > 0
    
    async def delete_user(
        self,
        domain: str,
        user_id: str
    ) -> bool:
        """
        Delete user from tenant-specific table (soft delete - suspend).
        
        Args:
            domain: Company domain
            user_id: User ID
        
        Returns:
            True if deleted
        """
        table_name = get_tenant_table_name(domain)
        
        query = f"""
            UPDATE `{table_name}`
            SET status = 'SUSPENDED', updated_at = NOW()
            WHERE user_id = %s
        """
        
        await self.db.execute_query(query, (user_id,), commit=True)
        logger.info(f"User deleted (suspended) in {table_name}: {user_id}")
        return True
