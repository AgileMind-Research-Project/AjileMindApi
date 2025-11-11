# Database Module

## Overview
Database session management and initialization.

## Structure

```
db/
├── session.py      # Database session factory
├── base.py         # Base class for models
├── init_db.py      # Database initialization
└── __init__.py
```

## Database Session

```python
from app.db.session import AsyncSessionLocal

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

## Initialization

```python
from app.db.init_db import init_db

# Initialize database
await init_db()
```

## Migrations

See [Alembic README](../../alembic/README.md)

---

**Related:** [Models](../models/README.md)
