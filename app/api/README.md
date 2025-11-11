# API Routes Module

## Overview
This module contains all API endpoints for the AgileMind platform, organized by version and resource type.

## Structure

```
api/
├── v1/                    # API Version 1
│   ├── auth.py           # Authentication endpoints
│   ├── tenants.py        # Tenant management
│   ├── users.py          # User management
│   ├── sprints.py        # Sprint planning endpoints
│   ├── tasks.py          # Task management
│   ├── meetings.py       # Meeting bot endpoints
│   ├── retrospectives.py # Retrospective endpoints
│   ├── governance.py     # Governance dashboard
│   ├── integrations.py   # External integrations
│   └── ai.py             # AI-powered endpoints
├── deps.py               # Dependency injection
└── __init__.py
```

## API Versioning

- **v1:** Current stable version
- All endpoints prefixed with `/api/v1/`
- Future versions will be `/api/v2/`, etc.

## Common Dependencies

### Authentication
```python
from app.api.deps import get_current_user, get_current_tenant

@router.get("/protected")
async def protected_route(
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant)
):
    # User is authenticated and tenant context is available
    pass
```

### Pagination
```python
from app.api.deps import CommonQueryParams

@router.get("/items")
async def list_items(commons: CommonQueryParams = Depends()):
    # commons.skip, commons.limit available
    pass
```

## Endpoint Categories

### 1. Authentication (`auth.py`)
- User registration
- Login/logout
- Token refresh
- Password reset

**Endpoints:**
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/forgot-password`

### 2. Tenants (`tenants.py`)
- Tenant CRUD operations
- Tenant settings
- Subscription management

**Endpoints:**
- `GET /api/v1/tenants`
- `POST /api/v1/tenants`
- `GET /api/v1/tenants/{id}`
- `PUT /api/v1/tenants/{id}`
- `DELETE /api/v1/tenants/{id}`

### 3. Users (`users.py`)
- User profile management
- Team member management
- Role assignments

**Endpoints:**
- `GET /api/v1/users/me`
- `PUT /api/v1/users/me`
- `GET /api/v1/users`
- `POST /api/v1/users/invite`

### 4. Sprints (`sprints.py`)
- Sprint CRUD operations
- Capacity planning
- Sprint analytics
- AI task generation

**Endpoints:**
- `GET /api/v1/sprints`
- `POST /api/v1/sprints`
- `GET /api/v1/sprints/{id}`
- `POST /api/v1/sprints/{id}/tasks/generate` *(AI)*
- `GET /api/v1/sprints/{id}/capacity`
- `GET /api/v1/sprints/{id}/burndown`

### 5. Tasks (`tasks.py`)
- Task CRUD operations
- Task status updates
- Task assignments
- Blocker management

**Endpoints:**
- `GET /api/v1/tasks`
- `POST /api/v1/tasks`
- `PUT /api/v1/tasks/{id}`
- `DELETE /api/v1/tasks/{id}`
- `PATCH /api/v1/tasks/{id}/status`

### 6. Meetings (`meetings.py`)
- Meeting scheduling
- Audio transcription
- Blocker detection
- Action item extraction
- Jira synchronization

**Endpoints:**
- `POST /api/v1/meetings`
- `POST /api/v1/meetings/transcribe` *(AI)*
- `GET /api/v1/meetings/{id}/blockers`
- `GET /api/v1/meetings/{id}/summary`
- `POST /api/v1/meetings/{id}/sync-jira`

### 7. Retrospectives (`retrospectives.py`)
- Retrospective creation
- Feedback collection
- Sentiment analysis
- Action plan generation

**Endpoints:**
- `GET /api/v1/retrospectives`
- `POST /api/v1/retrospectives`
- `POST /api/v1/retrospectives/{id}/analyze` *(AI)*
- `GET /api/v1/retrospectives/{id}/insights`

### 8. Governance (`governance.py`)
- Dashboard metrics
- Risk analytics
- CI/CD monitoring
- Budget tracking

**Endpoints:**
- `GET /api/v1/governance/dashboard`
- `GET /api/v1/governance/risks`
- `GET /api/v1/governance/cicd-status`
- `GET /api/v1/governance/budget`

### 9. Integrations (`integrations.py`)
- Jira configuration
- Teams configuration
- GitHub/GitLab setup
- Webhook management

**Endpoints:**
- `POST /api/v1/integrations/jira/connect`
- `POST /api/v1/integrations/teams/connect`
- `GET /api/v1/integrations/status`
- `POST /api/v1/integrations/webhooks`

### 10. AI Services (`ai.py`)
- Chat assistant
- Task suggestions
- Risk predictions
- Anomaly detection

**Endpoints:**
- `POST /api/v1/ai/chat`
- `POST /api/v1/ai/suggest-tasks`
- `POST /api/v1/ai/predict-risks`
- `POST /api/v1/ai/detect-anomalies`

## Request/Response Format

### Standard Success Response
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation successful"
}
```

### Standard Error Response
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": { ... }
  }
}
```

### Pagination Response
```json
{
  "success": true,
  "data": [ ... ],
  "pagination": {
    "total": 100,
    "page": 1,
    "limit": 20,
    "pages": 5
  }
}
```

## Error Codes

- `AUTH_001` - Invalid credentials
- `AUTH_002` - Token expired
- `AUTH_003` - Insufficient permissions
- `TENANT_001` - Tenant not found
- `TENANT_002` - Subscription limit reached
- `SPRINT_001` - Sprint not found
- `TASK_001` - Task not found
- `AI_001` - AI service unavailable

## Rate Limiting

- **Free Tier:** 100 requests/hour
- **Starter:** 1,000 requests/hour
- **Professional:** 10,000 requests/hour
- **Enterprise:** Unlimited

## WebSocket Endpoints

```python
# Real-time updates
ws://localhost:8000/ws/updates/{tenant_id}

# Chat assistant
ws://localhost:8000/ws/chat/{user_id}
```

## Authentication

All endpoints (except auth endpoints) require JWT token:

```bash
Authorization: Bearer <jwt_token>
```

## Example Usage

### Create Sprint
```bash
curl -X POST http://localhost:8000/api/v1/sprints \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sprint 1",
    "start_date": "2025-11-11",
    "end_date": "2025-11-25",
    "capacity_hours": 80
  }'
```

### Generate AI Tasks
```bash
curl -X POST http://localhost:8000/api/v1/sprints/123/tasks/generate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "context": "E-commerce checkout flow",
    "story_points": 20
  }'
```

## Testing Endpoints

```bash
# Run API tests
pytest tests/api/

# Test specific endpoint
pytest tests/api/test_sprints.py
```

## Adding New Endpoints

1. Create/update router file in `app/api/v1/`
2. Define route with appropriate HTTP method
3. Add Pydantic schemas for request/response
4. Implement business logic in service layer
5. Add tests in `tests/api/`
6. Update this README

## Best Practices

1. **Use Pydantic models** for request/response validation
2. **Keep routes thin** - delegate to service layer
3. **Handle errors gracefully** - use HTTPException
4. **Document with docstrings** - auto-generates OpenAPI
5. **Validate tenant context** - use dependency injection
6. **Log requests** - for debugging and monitoring
7. **Version APIs** - maintain backward compatibility

---

**Related Documentation:**
- [Schemas](../schemas/README.md)
- [Services](../services/README.md)
- [Models](../models/README.md)
