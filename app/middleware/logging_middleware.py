"""
Logging Middleware for FastAPI

Middleware to log all HTTP requests and responses with timing information.
Automatically adds request context to all logs during request processing.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import uuid
from typing import Callable

from app.core.logger import (
    logger,
    add_context,
    clear_context,
    log_request,
    log_exception,
)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log HTTP requests and responses.
    
    Features:
    - Generates unique request ID
    - Logs request details (method, path, query params)
    - Logs response details (status code, duration)
    - Adds context to all logs during request
    - Handles exceptions and logs them
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Extract request information
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params)
        client_host = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Extract tenant and user from headers/auth
        tenant_id = request.headers.get("X-Tenant-ID")
        # Note: user_id would be extracted from JWT token in actual implementation
        
        # Set logging context for this request
        context = {
            "request_id": request_id,
            "client_ip": client_host,
            "user_agent": user_agent[:100],  # Truncate long user agents
        }
        
        if tenant_id:
            context["tenant_id"] = tenant_id
        
        add_context(**context)
        
        # Log incoming request
        logger.info(
            f"Incoming request: {method} {path}",
            extra={
                "extra_fields": {
                    "query_params": query_params,
                    "path": path,
                    "method": method,
                }
            }
        )
        
        # Process request and measure time
        start_time = time.time()
        
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000
            
            # Log request completion
            log_request(
                method=method,
                path=path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                request_id=request_id,
                tenant_id=tenant_id,
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            # Log exception
            log_exception(
                e,
                context={
                    "method": method,
                    "path": path,
                    "duration_ms": duration_ms,
                    "request_id": request_id,
                }
            )
            
            # Re-raise to be handled by exception handlers
            raise
            
        finally:
            # Clear context after request
            clear_context()


class PerformanceLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log slow endpoints.
    Warns if request takes longer than threshold.
    """
    
    def __init__(self, app: ASGIApp, threshold_ms: float = 1000):
        super().__init__(app)
        self.threshold_ms = threshold_ms
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        
        if duration_ms > self.threshold_ms:
            logger.warning(
                f"Slow endpoint detected: {request.method} {request.url.path} took {duration_ms:.2f}ms",
                extra={
                    "extra_fields": {
                        "endpoint": request.url.path,
                        "method": request.method,
                        "duration_ms": duration_ms,
                        "threshold_ms": self.threshold_ms,
                    }
                }
            )
        
        return response


# Utility function to add middleware to FastAPI app
def setup_logging_middleware(app):
    """
    Add logging middleware to FastAPI application.
    
    Usage:
        from app.middleware.logging_middleware import setup_logging_middleware
        setup_logging_middleware(app)
    """
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(PerformanceLoggingMiddleware, threshold_ms=1000)
