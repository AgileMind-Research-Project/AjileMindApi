# Core Configuration Module

## Overview
This module contains core application configurations, security settings, middleware, and base functionality used across the entire backend.

## Structure

```
core/
├── config.py          # Application configuration
├── security.py        # JWT, password hashing, permissions
├── middleware.py      # Custom middleware
├── exceptions.py      # Custom exception classes
└── __init__.py
```

## Components

### 1. Configuration (`config.py`)

Manages all application settings using Pydantic BaseSettings.

```python
from app.core.config import settings

# Access configuration
database_url = settings.DATABASE_URL
jwt_secret = settings.JWT_SECRET
```

**Key Settings:**
- **App Settings:** Name, version, debug mode
- **Database:** Connection URL, pool settings
- **Redis:** Connection URL, cache TTL
- **JWT:** Secret key, algorithm, expiration
- **External APIs:** OpenAI, Jira, Teams credentials
- **CORS:** Allowed origins
- **Rate Limiting:** Per-tenant limits

**Environment Variables:**
All settings can be overridden via environment variables:
```env
APP_NAME=AgileMind
DEBUG=false
DATABASE_URL=mysql+asyncmy://user:pass@host/db
JWT_SECRET=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 2. Security (`security.py`)

Handles authentication, authorization, and cryptographic operations.

#### Password Hashing
```python
from app.core.security import get_password_hash, verify_password

# Hash password
hashed = get_password_hash("user_password")

# Verify password
is_valid = verify_password("user_password", hashed)
```

#### JWT Token Management
```python
from app.core.security import create_access_token, decode_token

# Create token
token = create_access_token(
    data={"sub": user.id, "tenant_id": tenant.id}
)

# Decode token
payload = decode_token(token)
```

#### Permission Checking
```python
from app.core.security import has_permission

# Check if user has permission
if has_permission(user, "sprint.write"):
    # User can write sprints
    pass
```

**Security Features:**
- **Password Hashing:** bcrypt with salt
- **JWT Tokens:** HS256 algorithm
- **Token Expiration:** Configurable TTL
- **Refresh Tokens:** Long-lived tokens
- **Permission System:** Role-based access control (RBAC)
- **API Key Authentication:** For service-to-service

### 3. Middleware (`middleware.py`)

Custom middleware for request processing.

#### Tenant Context Middleware
Automatically extracts and validates tenant from requests:
```python
# Extracts tenant from:
# 1. Subdomain (tenant.agilemind.com)
# 2. JWT token claim
# 3. Custom header (X-Tenant-ID)

# Validates tenant exists and is active
# Injects tenant into request state
```

#### Logging Middleware
Logs all requests with:
- Request ID
- User ID
- Tenant ID
- Duration
- Status code

#### Rate Limiting Middleware
Implements per-tenant rate limiting:
```python
# Uses Redis for distributed rate limiting
# Different limits per tier:
# - Free: 100 req/hour
# - Starter: 1,000 req/hour
# - Professional: 10,000 req/hour
# - Enterprise: Unlimited
```

#### CORS Middleware
Handles Cross-Origin Resource Sharing:
```python
# Configurable allowed origins
# Supports credentials
# Handles preflight requests
```

### 4. Custom Exceptions (`exceptions.py`)

Standardized exception classes for error handling.

```python
from app.core.exceptions import (
    NotFoundException,
    UnauthorizedException,
    ForbiddenException,
    ValidationException,
    TenantException
)

# Usage
if not user:
    raise NotFoundException("User not found")

if not has_permission(user, "admin"):
    raise ForbiddenException("Admin access required")
```

**Exception Types:**

#### Base Exceptions
- `AgileMindException` - Base exception class
- `APIException` - Base API exception

#### Auth Exceptions
- `UnauthorizedException` - 401 - Invalid credentials
- `ForbiddenException` - 403 - Insufficient permissions
- `TokenExpiredException` - 401 - Token expired

#### Resource Exceptions
- `NotFoundException` - 404 - Resource not found
- `AlreadyExistsException` - 409 - Resource exists
- `ValidationException` - 422 - Validation failed

#### Tenant Exceptions
- `TenantNotFoundException` - 404 - Tenant not found
- `TenantInactiveException` - 403 - Tenant inactive
- `SubscriptionLimitException` - 402 - Limit reached

#### Integration Exceptions
- `JiraConnectionException` - Jira API error
- `TeamsConnectionException` - Teams API error
- `AIServiceException` - AI service error

**Exception Handler:**
```python
@app.exception_handler(AgileMindException)
async def agilemind_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": false,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )
```

## Multi-Tenant Security

### Tenant Isolation Strategy

1. **Database Level:**
   ```python
   # Every query automatically filtered by tenant_id
   query = select(Sprint).where(
       Sprint.tenant_id == current_tenant.id
   )
   ```

2. **API Level:**
   ```python
   # Tenant context injected via middleware
   @router.get("/sprints")
   async def get_sprints(
       tenant: Tenant = Depends(get_current_tenant)
   ):
       # tenant is automatically validated
       pass
   ```

3. **Row-Level Security:**
   ```python
   # Base model includes tenant_id
   class BaseModel(DeclarativeBase):
       tenant_id: Mapped[int] = mapped_column(
           ForeignKey("tenants.id"),
           nullable=False,
           index=True
       )
   ```

### Permission System

**Roles:**
- `admin` - Full access
- `manager` - Team and project management
- `developer` - Task and sprint access
- `viewer` - Read-only access

**Permissions:**
```python
PERMISSIONS = {
    "admin": ["*"],
    "manager": [
        "sprint.read", "sprint.write",
        "task.read", "task.write",
        "meeting.read", "meeting.write",
        "team.read", "team.write"
    ],
    "developer": [
        "sprint.read",
        "task.read", "task.write",
        "meeting.read"
    ],
    "viewer": [
        "sprint.read",
        "task.read",
        "meeting.read"
    ]
}
```

## Logging Configuration

```python
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# Structured logging
logger.info(
    "Sprint created",
    extra={
        "tenant_id": tenant.id,
        "user_id": user.id,
        "sprint_id": sprint.id
    }
)
```

**Log Levels:**
- `DEBUG` - Development details
- `INFO` - General information
- `WARNING` - Warning messages
- `ERROR` - Error messages
- `CRITICAL` - Critical issues

## Database Connection

```python
from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine

# Async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20
)
```

## Redis Connection

```python
from aioredis import from_url
from app.core.config import settings

# Redis client
redis = from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True
)
```

## Health Check

```python
@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "database": await check_database(),
        "redis": await check_redis()
    }
```

## Best Practices

1. **Never hardcode secrets** - Use environment variables
2. **Validate tenant context** - Use middleware
3. **Log security events** - Failed logins, permission denials
4. **Use async operations** - For I/O bound tasks
5. **Handle errors gracefully** - Use custom exceptions
6. **Rate limit aggressively** - Prevent abuse
7. **Rotate secrets regularly** - JWT keys, API keys

## Testing

```python
# Test configuration
pytest tests/core/test_config.py

# Test security
pytest tests/core/test_security.py

# Test middleware
pytest tests/core/test_middleware.py
```

---

**Related Documentation:**
- [Security Best Practices](../../docs/security.md)
- [Configuration Guide](../../docs/configuration.md)
