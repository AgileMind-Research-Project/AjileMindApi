# Pydantic Schemas Module

## Overview
Pydantic models for request validation and response serialization.

## Structure

```
schemas/
├── auth.py              # Login, register schemas
├── tenant.py            # Tenant schemas
├── user.py              # User schemas
├── sprint.py            # Sprint schemas
├── task.py              # Task schemas
├── meeting.py           # Meeting schemas
├── governance.py        # Dashboard schemas
└── __init__.py
```

## Schema Types

### Base Schemas
- `<Model>Base` - Shared fields
- `<Model>Create` - Create operation
- `<Model>Update` - Update operation
- `<Model>Response` - API response
- `<Model>InDB` - Database representation

### Example

```python
# Base schema
class SprintBase(BaseModel):
    name: str
    start_date: date
    end_date: date

# Create schema
class SprintCreate(SprintBase):
    capacity_hours: int

# Update schema
class SprintUpdate(BaseModel):
    name: Optional[str] = None
    capacity_hours: Optional[int] = None

# Response schema
class SprintResponse(SprintBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
```

## Validation

- Field validators
- Custom validators
- Type checking
- Required vs optional fields

---

**Related:** [API Routes](../api/README.md)
