# Business Services Module

## Overview
Business logic layer containing all service classes that implement core functionality.

## Structure

```
services/
├── auth_service.py       # Authentication logic
├── tenant_service.py     # Tenant management
├── sprint_service.py     # Sprint operations
├── meeting_service.py    # Meeting processing
├── jira_service.py       # Jira integration
├── teams_service.py      # Teams integration
├── ai_service.py         # AI orchestration
└── __init__.py
```

## Service Pattern

Each service follows this pattern:

```python
class SprintService:
    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
    
    async def create_sprint(self, data: SprintCreate) -> Sprint:
        # Business logic here
        sprint = Sprint(**data.dict(), tenant_id=self.tenant_id)
        self.db.add(sprint)
        await self.db.commit()
        return sprint
    
    async def generate_tasks_with_ai(self, sprint_id: int) -> List[Task]:
        # AI-powered task generation
        pass
```

## Key Services

### 1. AuthService
- User registration
- Login/logout
- Token management
- Password reset

### 2. SprintService
- CRUD operations
- Capacity planning
- Burndown calculations
- AI task generation

### 3. MeetingService
- Transcription processing
- Blocker detection
- Action item extraction
- Jira synchronization

### 4. AIService
- NLP processing
- Risk prediction
- Task recommendations
- Sentiment analysis

### 5. JiraService
- Authentication
- Issue synchronization
- Webhook handling
- Status mapping

## Best Practices

1. **Keep services focused** - Single responsibility
2. **Inject dependencies** - Database session, configs
3. **Use transactions** - Atomic operations
4. **Handle errors** - Raise custom exceptions
5. **Log operations** - For debugging and audit
6. **Test thoroughly** - Unit tests for each service

---

**Related:** [API Routes](../api/README.md), [Models](../models/README.md)
