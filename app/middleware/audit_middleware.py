"""
Audit Logging Middleware

Automatically log audit events from API requests.
"""

from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.db.repositories.audit_repository import AuditRepository
from app.db.database import db
from app.core.logger import logger
from app.utils.jwt import decode_token
import json


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically log audit events.
    
    Logs API requests that modify data (POST, PUT, DELETE).
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Process request
        response = await call_next(request)
        
        # Only log successful mutations (POST, PUT, DELETE)
        if request.method in ['POST', 'PUT', 'DELETE'] and response.status_code < 400:
            try:
                await self._log_request(request, response)
            except Exception as e:
                logger.error(f"Failed to log audit event: {e}")
        
        return response
    
    def _extract_user_from_token(self, request: Request) -> Optional[dict]:
        """Extract user information from JWT token in request"""
        try:
            auth_header = request.headers.get('authorization')
            if not auth_header:
                return None
            
            parts = auth_header.split()
            if len(parts) != 2 or parts[0].lower() != 'bearer':
                return None
            
            token = parts[1]
            payload = decode_token(token)
            
            if payload:
                return {
                    'user_id': payload.get('sub'),
                    'tenant_id': payload.get('tenant_id'),
                    'email': payload.get('email'),
                    'role': payload.get('role')
                }
        except Exception as e:
            logger.debug(f"Could not extract user from token: {e}")
        
        return None
    
    async def _log_request(self, request: Request, response: Response):
        """Log request to audit table"""
        # Extract path
        path = request.url.path
        
        # Skip certain paths
        skip_paths = ['/health', '/docs', '/redoc', '/openapi.json']
        if any(path.startswith(skip) for skip in skip_paths):
            return
        
        # Determine event type from path and method
        event_type = self._determine_event_type(path, request.method)
        
        if not event_type:
            return
        
        # Extract user info from JWT token
        user_info = self._extract_user_from_token(request)
        
        # Skip audit logging if no valid tenant (e.g., public endpoints like register)
        if not user_info or not user_info.get('tenant_id'):
            logger.debug(f"Skipping audit log for {path} - no tenant info")
            return
        
        tenant_id = user_info['tenant_id']
        user_id = user_info.get('user_id')
        
        # Get IP address
        ip_address = request.client.host if request.client else None
        
        # Get user agent
        user_agent = request.headers.get('user-agent')
        
        # Get request body if available
        event_data = {}
        try:
            if hasattr(request, '_body'):
                body = request._body.decode('utf-8')
                if body:
                    event_data = json.loads(body)
        except:
            pass
        
        # Create audit log
        audit_repo = AuditRepository(db)
        
        # Check if logging is enabled for this tenant
        settings = await audit_repo.get_audit_settings(tenant_id)
        if not settings.get('audit_logging_enabled', True):
            return
        
        await audit_repo.create_audit_log(
            tenant_id=tenant_id,
            event_type=event_type,
            user_id=user_id,
            event_data=event_data,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def _determine_event_type(self, path: str, method: str) -> str:
        """Determine audit event type from request path and method"""
        # User operations
        if '/users' in path:
            if method == 'POST':
                return 'user_created'
            elif method == 'PUT':
                return 'user_updated'
            elif method == 'DELETE':
                return 'user_deleted'
        
        # Role operations
        if '/roles' in path:
            if method == 'POST':
                return 'role_created'
            elif method == 'PUT':
                return 'role_updated'
            elif method == 'DELETE':
                return 'role_deleted'
        
        # Auth operations
        if '/auth/login' in path:
            return 'login_success'
        if '/auth/logout' in path:
            return 'logout'
        if '/auth/change-password' in path:
            return 'password_changed'
        if '/auth/register' in path:
            return 'tenant_created'
        
        # Settings operations
        if '/settings' in path and method == 'PUT':
            return 'settings_updated'
        
        return ''
