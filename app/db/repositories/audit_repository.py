"""
Audit Log Repository

Database operations for audit logs.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from app.db.database import Database
from app.core.logger import logger
import uuid


class AuditRepository:
    """Repository for audit log operations"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def create_audit_log(
        self,
        tenant_id: str,
        event_type: str,
        user_id: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create audit log entry.
        
        Args:
            tenant_id: Tenant ID
            event_type: Type of event
            user_id: User ID (optional)
            event_data: Additional event data (JSON)
            ip_address: IP address
            user_agent: User agent string
        
        Returns:
            Created audit log
        """
        log_id = f"audit_{uuid.uuid4().hex[:12]}"
        
        query = """
            INSERT INTO AUDIT_LOGS (
                LOG_ID, TENANT_ID, USER_ID, EVENT_TYPE, EVENT_DATA,
                IP_ADDRESS, USER_AGENT, CREATED_AT
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        """
        
        import json
        event_data_json = json.dumps(event_data) if event_data else None
        
        await self.db.execute_query(
            query,
            (log_id, tenant_id, user_id, event_type, event_data_json, ip_address, user_agent),
            commit=True
        )
        
        return await self.get_audit_log_by_id(log_id)
    
    async def get_audit_log_by_id(self, log_id: str) -> Optional[Dict[str, Any]]:
        """Get audit log by ID"""
        query = """
            SELECT 
                al.*,
                u.EMAIL as user_email
            FROM AUDIT_LOGS al
            LEFT JOIN USERS u ON al.USER_ID = u.USER_ID
            WHERE al.LOG_ID = %s
        """
        
        result = await self.db.execute_query(query, (log_id,), fetch_one=True)
        
        if result:
            import json
            audit_log = dict(result)
            if audit_log.get('event_data'):
                try:
                    audit_log['event_data'] = json.loads(audit_log['event_data'])
                except:
                    pass
            return audit_log
        
        return None
    
    async def get_audit_logs(
        self,
        tenant_id: str,
        event_type: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """
        Get audit logs with filters and pagination.
        
        Args:
            tenant_id: Tenant ID
            event_type: Filter by event type
            user_id: Filter by user ID
            start_date: Filter by start date
            end_date: Filter by end date
            page: Page number
            page_size: Items per page
        
        Returns:
            Dict with logs and pagination info
        """
        conditions = ["al.TENANT_ID = %s"]
        params = [tenant_id]
        
        if event_type:
            conditions.append("al.EVENT_TYPE = %s")
            params.append(event_type)
        
        if user_id:
            conditions.append("al.USER_ID = %s")
            params.append(user_id)
        
        if start_date:
            conditions.append("al.CREATED_AT >= %s")
            params.append(start_date)
        
        if end_date:
            conditions.append("al.CREATED_AT <= %s")
            params.append(end_date)
        
        where_clause = " AND ".join(conditions)
        
        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total
            FROM AUDIT_LOGS al
            WHERE {where_clause}
        """
        
        count_result = await self.db.execute_query(count_query, tuple(params), fetch_one=True)
        total = count_result['total'] if count_result else 0
        
        # Get paginated logs
        offset = (page - 1) * page_size
        
        query = f"""
            SELECT 
                al.*,
                u.EMAIL as user_email
            FROM AUDIT_LOGS al
            LEFT JOIN USERS u ON al.USER_ID = u.USER_ID
            WHERE {where_clause}
            ORDER BY al.CREATED_AT DESC
            LIMIT %s OFFSET %s
        """
        
        params.extend([page_size, offset])
        results = await self.db.execute_query(query, tuple(params), fetch_all=True)
        
        # Parse JSON event_data
        import json
        logs = []
        for result in results:
            log = dict(result)
            if log.get('event_data'):
                try:
                    log['event_data'] = json.loads(log['event_data'])
                except:
                    pass
            logs.append(log)
        
        total_pages = (total + page_size - 1) // page_size
        
        return {
            "logs": logs,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages
            }
        }
    
    async def delete_audit_log(self, log_id: str) -> bool:
        """Delete single audit log"""
        query = "DELETE FROM AUDIT_LOGS WHERE LOG_ID = %s"
        await self.db.execute_query(query, (log_id,), commit=True)
        return True
    
    async def delete_audit_logs_by_ids(self, log_ids: List[str]) -> int:
        """Delete multiple audit logs by IDs"""
        if not log_ids:
            return 0
        
        placeholders = ','.join(['%s'] * len(log_ids))
        query = f"DELETE FROM AUDIT_LOGS WHERE LOG_ID IN ({placeholders})"
        
        await self.db.execute_query(query, tuple(log_ids), commit=True)
        return len(log_ids)
    
    async def delete_audit_logs_before_date(
        self,
        tenant_id: str,
        before_date: datetime
    ) -> int:
        """Delete audit logs before specified date"""
        query = """
            DELETE FROM AUDIT_LOGS
            WHERE TENANT_ID = %s AND CREATED_AT < %s
        """
        
        await self.db.execute_query(query, (tenant_id, before_date), commit=True)
        
        # Return approximate count (MySQL doesn't return affected rows easily)
        return 0
    
    async def clear_all_audit_logs(self, tenant_id: str) -> bool:
        """Clear all audit logs for tenant"""
        query = "DELETE FROM AUDIT_LOGS WHERE TENANT_ID = %s"
        await self.db.execute_query(query, (tenant_id,), commit=True)
        return True
    
    async def get_audit_settings(self, tenant_id: str) -> Dict[str, Any]:
        """Get audit settings for tenant"""
        query = """
            SELECT AUDIT_LOGGING_ENABLED, AUDIT_RETENTION_DAYS
            FROM TENANTS
            WHERE TENANT_ID = %s
        """
        
        result = await self.db.execute_query(query, (tenant_id,), fetch_one=True)
        
        if result:
            return {
                "audit_logging_enabled": result.get('audit_logging_enabled', True),
                "retention_days": result.get('audit_retention_days', 90)
            }
        
        return {
            "audit_logging_enabled": True,
            "retention_days": 90
        }
    
    async def update_audit_settings(
        self,
        tenant_id: str,
        audit_logging_enabled: bool,
        retention_days: int = 90
    ) -> Dict[str, Any]:
        """Update audit settings"""
        query = """
            UPDATE TENANTS
            SET 
                AUDIT_LOGGING_ENABLED = %s,
                AUDIT_RETENTION_DAYS = %s,
                UPDATED_AT = NOW()
            WHERE TENANT_ID = %s
        """
        
        await self.db.execute_query(query, (audit_logging_enabled, retention_days, tenant_id), commit=True)
        
        return await self.get_audit_settings(tenant_id)
    
    async def cleanup_old_logs(self, tenant_id: str, retention_days: int) -> int:
        """Cleanup old audit logs based on retention policy"""
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        query = """
            DELETE FROM AUDIT_LOGS
            WHERE TENANT_ID = %s AND CREATED_AT < %s
        """
        
        await self.db.execute_query(query, (tenant_id, cutoff_date), commit=True)
        
        logger.info(f"Cleaned up audit logs older than {retention_days} days for tenant {tenant_id}")
        return 0
