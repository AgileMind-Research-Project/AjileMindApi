"""
Example Usage of Logging System

This file demonstrates how to use the logging system throughout the application.
"""

from app.core.logger import (
    logger,
    get_logger,
    add_context,
    log_request,
    log_auth_event,
    log_authorization,
    log_performance,
    log_database_query,
    log_ai_request,
    log_integration_event,
    log_exception,
)
from app.utils.logging_decorators import (
    log_function_call,
    monitor_performance,
    log_exceptions,
    log_db_query,
)


# Example 1: Basic Logging
def example_basic_logging():
    """Basic logging examples"""
    
    # Get module-specific logger
    service_logger = get_logger("user_service")
    
    # Different log levels
    service_logger.debug("Debug information")
    service_logger.info("User registration started")
    service_logger.warning("Rate limit approaching")
    service_logger.error("Failed to send email")
    service_logger.critical("Database connection lost")


# Example 2: Logging with Context
async def example_context_logging():
    """Logging with request context"""
    
    # Add context that will be included in all subsequent logs
    add_context(
        request_id="req-abc123",
        user_id="user-456",
        tenant_id="tenant-789"
    )
    
    # These logs will automatically include the context
    logger.info("Processing user request")
    logger.info("Fetching user data")
    logger.info("Request completed")


# Example 3: API Endpoint with Logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import time

app = FastAPI()

@app.get("/api/users/{user_id}")
async def get_user(user_id: str, request: Request):
    """Example API endpoint with logging"""
    
    start_time = time.time()
    
    # Add request context
    add_context(
        request_id=request.headers.get("X-Request-ID"),
        user_id=user_id,
    )
    
    logger.info(f"Fetching user: {user_id}")
    
    try:
        # Simulate user fetch
        user = {"id": user_id, "name": "John Doe"}
        
        # Log successful response
        duration_ms = (time.time() - start_time) * 1000
        log_request(
            method="GET",
            path=f"/api/users/{user_id}",
            status_code=200,
            duration_ms=duration_ms,
        )
        
        return JSONResponse(content=user)
        
    except Exception as e:
        # Log exception
        log_exception(e, context={"user_id": user_id})
        return JSONResponse(status_code=500, content={"error": "Internal server error"})


# Example 4: Authentication Logging
def example_auth_logging():
    """Authentication event logging"""
    
    # Successful login
    log_auth_event(
        event="login_success",
        user_id="user-123",
        email="john@example.com",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0...",
    )
    
    # Failed login
    log_auth_event(
        event="login_failed",
        email="john@example.com",
        ip_address="192.168.1.100",
        reason="invalid_password",
        attempt_count=3,
    )
    
    # Logout
    log_auth_event(
        event="logout",
        user_id="user-123",
        session_duration_minutes=45,
    )


# Example 5: Authorization Logging
def example_authorization_logging():
    """Authorization check logging"""
    
    # Access granted
    log_authorization(
        action="delete_sprint",
        user_id="user-123",
        resource="sprint",
        allowed=True,
        sprint_id="sprint-456",
        role="admin",
    )
    
    # Access denied
    log_authorization(
        action="delete_sprint",
        user_id="user-789",
        resource="sprint",
        allowed=False,
        sprint_id="sprint-456",
        role="viewer",
        required_permission="sprints.delete",
    )


# Example 6: Performance Monitoring with Decorator
@monitor_performance(threshold_ms=500)
async def example_slow_operation():
    """Operation with performance monitoring"""
    import asyncio
    
    logger.info("Starting slow operation")
    await asyncio.sleep(1.5)  # Simulate slow operation
    logger.info("Slow operation completed")


# Example 7: Database Query Logging
@log_db_query
async def example_database_query(query: str):
    """Database query with automatic logging"""
    
    # Simulate query execution
    import asyncio
    await asyncio.sleep(0.1)
    
    # Return mock result
    class MockResult:
        rowcount = 5
    
    return MockResult()


# Example 8: Database Query Logging (Manual)
async def example_manual_db_logging():
    """Manual database query logging"""
    
    import time
    
    query = "SELECT * FROM tasks WHERE sprint_id = ? AND status = ?"
    start_time = time.time()
    
    try:
        # Execute query (simulated)
        # result = await db.execute(query, sprint_id, status)
        
        duration_ms = (time.time() - start_time) * 1000
        rows_affected = 23  # From result
        
        log_database_query(
            query=query,
            duration_ms=duration_ms,
            rows_affected=rows_affected,
            sprint_id="sprint-123",
        )
        
    except Exception as e:
        log_exception(e, context={"query": query})


# Example 9: AI Request Logging
async def example_ai_logging():
    """AI API request logging"""
    
    import time
    start_time = time.time()
    
    # Make AI request (simulated)
    # response = await openai.chat.completions.create(...)
    
    duration_ms = (time.time() - start_time) * 1000
    
    log_ai_request(
        operation="task_generation",
        model="gpt-4",
        tokens_used=1250,
        duration_ms=duration_ms,
        prompt_tokens=250,
        completion_tokens=1000,
        context="User authentication feature",
    )


# Example 10: Integration Event Logging
def example_integration_logging():
    """Integration event logging"""
    
    # Successful Jira sync
    log_integration_event(
        provider="jira",
        event="sync_issues",
        success=True,
        issues_synced=23,
        duration_ms=3450,
    )
    
    # Failed Teams notification
    log_integration_event(
        provider="teams",
        event="send_notification",
        success=False,
        error="Connection timeout",
        retry_count=3,
    )


# Example 11: Service with Full Logging
class UserService:
    """Example service with comprehensive logging"""
    
    def __init__(self):
        self.logger = get_logger("services.user_service")
    
    @log_exceptions
    @monitor_performance(threshold_ms=500)
    async def create_user(self, email: str, password: str, tenant_id: str):
        """Create user with full logging"""
        
        self.logger.info(f"Creating user: {email}")
        
        # Add context
        add_context(tenant_id=tenant_id, email=email)
        
        try:
            # Validate email
            self.logger.debug("Validating email format")
            if "@" not in email:
                self.logger.warning(f"Invalid email format: {email}")
                raise ValueError("Invalid email")
            
            # Check if user exists
            self.logger.debug("Checking if user exists")
            # exists = await self.user_repository.exists(email)
            exists = False
            
            if exists:
                self.logger.warning(f"User already exists: {email}")
                raise ValueError("User already exists")
            
            # Create user
            self.logger.info("Creating user in database")
            # user = await self.user_repository.create(...)
            
            # Log successful creation
            self.logger.info(f"User created successfully: {email}")
            
            # Log auth event
            log_auth_event(
                event="user_registered",
                email=email,
                tenant_id=tenant_id,
            )
            
            return {"id": "user-123", "email": email}
            
        except Exception as e:
            self.logger.error(f"Failed to create user: {email}")
            log_exception(e, context={"email": email, "tenant_id": tenant_id})
            raise


# Example 12: Exception Logging
def example_exception_logging():
    """Exception logging examples"""
    
    try:
        # Risky operation
        result = 10 / 0
    except Exception as e:
        # Log with full traceback and context
        log_exception(
            e,
            context={
                "operation": "division",
                "numerator": 10,
                "denominator": 0,
            }
        )


# Example 13: Custom Logger Configuration
def example_custom_logger():
    """Create custom logger for specific module"""
    
    from app.core.logger import setup_logger
    
    # Custom logger with specific settings
    custom_logger = setup_logger(
        name="custom_module",
        log_level="DEBUG",
        log_to_console=True,
        log_to_file=True,
        json_format=False,
    )
    
    custom_logger.info("Custom logger initialized")


# Example 14: Integration with FastAPI Middleware
from fastapi import FastAPI
from app.middleware.logging_middleware import setup_logging_middleware

def setup_app_with_logging():
    """Setup FastAPI app with logging middleware"""
    
    app = FastAPI(title="AgileMind API")
    
    # Add logging middleware
    setup_logging_middleware(app)
    
    @app.get("/")
    async def root():
        logger.info("Root endpoint accessed")
        return {"message": "Hello World"}
    
    return app


if __name__ == "__main__":
    """Run examples"""
    
    # Basic logging
    example_basic_logging()
    
    # Context logging
    import asyncio
    asyncio.run(example_context_logging())
    
    # Auth logging
    example_auth_logging()
    
    # Authorization logging
    example_authorization_logging()
    
    print("\nCheck logs directory for output files:")
    print("- logs/app.log")
    print("- logs/error.log")
    print("- logs/daily.log")
