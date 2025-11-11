"""
Tenant Repository

Database operations for tenants.
"""

import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from app.db.database import Database
from app.core.logger import logger


class TenantRepository:
    """Repository for tenant database operations"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def create_tenant(
        self,
        company_name: str,
        status: str = "ACTIVE"
    ) -> Dict[str, Any]:
        """
        Create new tenant.
        
        Args:
            company_name: Company name
            status: Tenant status
        
        Returns:
            Created tenant data
        """
        tenant_id = f"tn-{uuid.uuid4().hex[:16]}"
        
        query = """
            INSERT INTO TENANTS (TENANT_ID, COMPANY_NAME, STATUS, CREATED_AT, UPDATED_AT)
            VALUES (%s, %s, %s, NOW(), NOW())
        """
        
        await self.db.execute_query(
            query,
            (tenant_id, company_name, status),
            commit=True
        )
        
        logger.info(f"Tenant created: {tenant_id} - {company_name}")
        
        return {
            "tenant_id": tenant_id,
            "company_name": company_name,
            "status": status,
            "created_at": datetime.utcnow().isoformat()
        }
    
    async def get_tenant_by_id(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get tenant by ID.
        
        Args:
            tenant_id: Tenant ID
        
        Returns:
            Tenant data or None
        """
        query = """
            SELECT 
                TENANT_ID as tenant_id,
                COMPANY_NAME as company_name,
                STATUS as status,
                CREATED_AT as created_at,
                UPDATED_AT as updated_at
            FROM TENANTS
            WHERE TENANT_ID = %s
        """
        
        result = await self.db.execute_query(query, (tenant_id,), fetch_one=True)
        return result
    
    async def tenant_exists(self, tenant_id: str) -> bool:
        """
        Check if tenant exists.
        
        Args:
            tenant_id: Tenant ID
        
        Returns:
            True if exists
        """
        query = "SELECT COUNT(*) as count FROM TENANTS WHERE TENANT_ID = %s"
        result = await self.db.execute_query(query, (tenant_id,), fetch_one=True)
        return result and result['count'] > 0
    
    async def update_tenant_status(self, tenant_id: str, status: str) -> bool:
        """
        Update tenant status.
        
        Args:
            tenant_id: Tenant ID
            status: New status
        
        Returns:
            True if updated
        """
        query = """
            UPDATE TENANTS
            SET STATUS = %s, UPDATED_AT = NOW()
            WHERE TENANT_ID = %s
        """
        
        await self.db.execute_query(query, (status, tenant_id), commit=True)
        logger.info(f"Tenant {tenant_id} status updated to {status}")
        return True
