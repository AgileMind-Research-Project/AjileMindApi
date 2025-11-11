# Logging Configuration

## Overview
Winston-based logging system for comprehensive application monitoring and debugging.

## Setup

### Installation
```bash
pip install python-json-logger
```

## Logger Configuration

### app/core/logger.py
Main logger configuration with multiple handlers and formatters.

## Log Levels

1. **DEBUG** - Detailed debugging information
2. **INFO** - General informational messages
3. **WARNING** - Warning messages for potentially harmful situations
4. **ERROR** - Error messages for serious problems
5. **CRITICAL** - Critical messages for very serious errors

## Log Destinations

### 1. Console Output
- Development environment
- Colored output
- Formatted for readability

### 2. File Logging
- **app.log** - All logs (INFO and above)
- **error.log** - Error logs only (ERROR and above)
- **access.log** - HTTP access logs
- **security.log** - Authentication and authorization logs
- **performance.log** - Performance metrics

### 3. Structured JSON Logs
- Machine-readable format
- Easy integration with log aggregation tools
- Includes metadata (timestamp, level, context)

## Usage Examples

### Basic Logging
```python
from app.core.logger import logger

# Info log
logger.info("User logged in", extra={"user_id": "123", "tenant_id": "abc"})

# Error log
logger.error("Database connection failed", exc_info=True)

# Warning log
logger.warning("API rate limit approaching", extra={"current": 95, "limit": 100})

# Debug log
logger.debug("Processing task", extra={"task_id": "task-123"})
```

### Request Logging
```python
from app.core.logger import log_request

@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    log_request(request, response)
    return response
```

### Exception Logging
```python
from app.core.logger import logger

try:
    result = risky_operation()
except Exception as e:
    logger.exception("Operation failed", extra={
        "operation": "risky_operation",
        "user_id": user_id
    })
    raise
```

### Performance Logging
```python
from app.core.logger import log_performance
import time

start_time = time.time()
# ... operation ...
duration = time.time() - start_time

log_performance(
    operation="database_query",
    duration=duration,
    metadata={"query": "SELECT * FROM tasks"}
)
```

## Log Format

### Standard Format
```
2024-01-20 10:30:45,123 - INFO - [user_service] - User logged in - user_id=123, tenant_id=abc
```

### JSON Format
```json
{
  "timestamp": "2024-01-20T10:30:45.123Z",
  "level": "INFO",
  "logger": "user_service",
  "message": "User logged in",
  "user_id": "123",
  "tenant_id": "abc",
  "request_id": "req-uuid",
  "environment": "production"
}
```

## Contextual Logging

### Add Request Context
```python
from app.core.logger import add_context, logger

# Add context for all subsequent logs in this request
add_context({
    "request_id": "req-123",
    "user_id": "user-456",
    "tenant_id": "tenant-789"
})

logger.info("Processing request")  # Automatically includes context
```

### Tenant Context
```python
from app.core.logger import with_tenant_context

with with_tenant_context(tenant_id="tenant-123"):
    logger.info("Tenant operation")  # Includes tenant_id
```

## Log Rotation

- **Size-based**: Rotate when file reaches 10MB
- **Time-based**: Daily rotation at midnight
- **Retention**: Keep logs for 30 days
- **Compression**: Old logs compressed to save space

## Monitoring & Alerts

### Critical Error Alerts
```python
from app.core.logger import logger, alert_critical

try:
    critical_operation()
except Exception as e:
    logger.critical("Critical failure", exc_info=True)
    alert_critical("System critical failure", exception=e)
```

### Performance Monitoring
```python
from app.core.logger import monitor_performance

@monitor_performance(threshold_ms=1000)
async def slow_operation():
    # If execution > 1000ms, automatically logs warning
    pass
```

## Security Logging

### Authentication Events
```python
from app.core.logger import log_auth_event

log_auth_event(
    event="login_success",
    user_id="user-123",
    ip_address="192.168.1.1",
    user_agent="Mozilla/5.0..."
)

log_auth_event(
    event="login_failed",
    email="user@example.com",
    ip_address="192.168.1.1",
    reason="invalid_password"
)
```

### Authorization Events
```python
from app.core.logger import log_authorization

log_authorization(
    action="access_denied",
    user_id="user-123",
    resource="sprint",
    resource_id="sprint-456",
    required_permission="sprints.delete"
)
```

## Integration with External Services

### ELK Stack (Elasticsearch, Logstash, Kibana)
- JSON format compatible
- Automatic log shipping
- Centralized log management

### Sentry Integration
```python
from app.core.logger import configure_sentry

configure_sentry(
    dsn="https://your-sentry-dsn",
    environment="production",
    traces_sample_rate=0.1
)
```

### CloudWatch Integration
```python
from app.core.logger import configure_cloudwatch

configure_cloudwatch(
    log_group="/aws/agile-mind/backend",
    stream_name="production"
)
```

## Best Practices

1. **Always include context**: Add user_id, tenant_id, request_id
2. **Use appropriate levels**: Don't overuse ERROR for warnings
3. **Include exception info**: Use `exc_info=True` for errors
4. **Sanitize sensitive data**: Never log passwords, tokens, credit cards
5. **Use structured logging**: Include metadata as extra fields
6. **Performance awareness**: Don't log in tight loops
7. **Meaningful messages**: Clear, actionable log messages

## Environment-Specific Configuration

### Development
```python
LOG_LEVEL=DEBUG
LOG_TO_CONSOLE=true
LOG_TO_FILE=false
LOG_FORMAT=colored
```

### Production
```python
LOG_LEVEL=INFO
LOG_TO_CONSOLE=true
LOG_TO_FILE=true
LOG_FORMAT=json
LOG_ROTATION=true
LOG_RETENTION_DAYS=30
```

## Log Analysis

### Common Queries
```bash
# Find all errors in last hour
grep "ERROR" app.log | tail -100

# Find logs for specific user
grep "user_id=123" app.log

# Count errors by type
grep "ERROR" app.log | awk '{print $5}' | sort | uniq -c

# Performance logs above 1 second
grep "duration" performance.log | awk '$3 > 1000'
```

## Troubleshooting

### Check Log Files
```bash
# View real-time logs
tail -f logs/app.log

# View errors only
tail -f logs/error.log

# Search for specific pattern
grep "database" logs/app.log
```

### Log Level Adjustment
```python
# Temporarily increase log level
from app.core.logger import set_log_level
set_log_level("DEBUG")

# For specific logger
from app.core.logger import get_logger
logger = get_logger("api.sprints")
logger.setLevel("DEBUG")
```

## Performance Impact

- **Console logging**: ~0.1ms per log
- **File logging**: ~0.5ms per log
- **JSON formatting**: ~0.2ms per log
- **Network logging**: ~5-10ms per log

**Recommendation**: Use async logging for high-throughput systems

---

## Related Files
- `app/core/logger.py` - Main logger implementation
- `app/middleware/logging_middleware.py` - Request logging middleware
- `logs/` - Log files directory
