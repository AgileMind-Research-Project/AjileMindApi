# AgileMind Backend - FastAPI Application

## Overview
This is the backend service for AgileMind, a cloud-native, AI-powered SaaS platform for Agile project management. Built with FastAPI (Python 3.11+), it provides RESTful APIs, WebSocket support, and AI/ML capabilities.

## Technology Stack
- **Framework:** FastAPI 0.104+
- **Language:** Python 3.11+
- **ORM:** SQLAlchemy 2.0
- **Migration:** Alembic
- **Validation:** Pydantic v2
- **Authentication:** JWT (python-jose)
- **Database:** MySQL 8.0+ (with asyncmy)
- **Cache:** Redis 7.0+
- **Task Queue:** Celery + RabbitMQ
- **AI/ML:** OpenAI API, spaCy, scikit-learn
- **Testing:** Pytest

## Project Structure

```
agile-mind-backend/
├── app/
│   ├── api/              # API endpoints
│   ├── core/             # Core configurations
│   ├── models/           # Database models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   ├── ai/               # AI/ML components
│   ├── integrations/     # External API integrations
│   ├── db/               # Database setup
│   ├── tasks/            # Celery background tasks
│   └── utils/            # Utility functions
├── tests/                # Test suite
├── alembic/              # Database migrations
├── requirements.txt      # Python dependencies
├── Dockerfile            # Docker configuration
└── README.md            # This file
```

## Installation

### Prerequisites
- Python 3.11+
- MySQL 8.0+
- Redis 7.0+
- RabbitMQ (for Celery)

### Setup

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

5. **Start development server:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Running with Docker

```bash
# Build and run
docker-compose up -d backend

# View logs
docker-compose logs -f backend
```

## API Documentation

Once running, access:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

## Key Features

### 1. Multi-Tenant Architecture
- Row-level security with `tenant_id`
- JWT-based authentication
- Automatic tenant context injection

### 2. Four Major Capability Areas

#### Planning & Task Automation
- Sprint planning endpoints
- AI-powered task generation
- Capacity planning algorithms
- Historical performance analysis

#### Daily Scrum Assistant
- Meeting transcription processing
- Blocker detection using NLP
- Knowledge transfer mapping
- Jira synchronization

#### Retrospective & Documentation
- Feedback aggregation
- Release notes generation
- Bug pattern analysis
- Historical context retrieval

#### Project Governance
- Risk analytics
- CI/CD pipeline monitoring
- Delay analytics
- Budget tracking

### 3. AI/ML Core Intelligence
- Natural Language Processing
- Predictive analytics
- Anomaly detection
- Task recommendation engine

### 4. External Integrations
- Jira API integration
- Microsoft Teams webhooks
- GitHub/GitLab CI/CD
- Custom webhook support

## Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# View migration history
alembic history
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_auth.py

# Run with verbose output
pytest -v
```

## Background Tasks (Celery)

```bash
# Start Celery worker
celery -A app.tasks.celery_app worker --loglevel=info

# Start Celery beat (scheduler)
celery -A app.tasks.celery_app beat --loglevel=info

# Monitor tasks
celery -A app.tasks.celery_app flower
```

## Environment Variables

Key environment variables (see `.env.example` for complete list):

```env
DATABASE_URL=mysql+asyncmy://user:pass@localhost:3306/agilemind_db
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=your-secret-key
OPENAI_API_KEY=your-openai-key
JIRA_CLIENT_ID=your-jira-client-id
TEAMS_CLIENT_ID=your-teams-client-id
```

## Component Documentation

Each component has its own README.md:
- [API Routes](./app/api/README.md)
- [Core Configuration](./app/core/README.md)
- [Database Models](./app/models/README.md)
- [Pydantic Schemas](./app/schemas/README.md)
- [Business Services](./app/services/README.md)
- [AI/ML Components](./app/ai/README.md)
- [External Integrations](./app/integrations/README.md)
- [Background Tasks](./app/tasks/README.md)

## API Endpoints Overview

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Refresh token

### Tenants
- `GET /api/v1/tenants` - List tenants
- `POST /api/v1/tenants` - Create tenant
- `GET /api/v1/tenants/{id}` - Get tenant details

### Sprints
- `GET /api/v1/sprints` - List sprints
- `POST /api/v1/sprints` - Create sprint
- `POST /api/v1/sprints/{id}/tasks/generate` - AI task generation

### Meetings
- `POST /api/v1/meetings/transcribe` - Process meeting audio
- `GET /api/v1/meetings/{id}/blockers` - Detected blockers

### Governance
- `GET /api/v1/governance/dashboard` - Dashboard data
- `GET /api/v1/governance/risks` - Risk analysis

## Development Guidelines

1. **Code Style:** Follow PEP 8
2. **Type Hints:** Use Python type hints everywhere
3. **Documentation:** Add docstrings to all functions
4. **Testing:** Write tests for new features
5. **Async:** Use async/await for I/O operations
6. **Logging:** Use structured logging
7. **Error Handling:** Use custom exceptions

## Performance Optimization

- Database query optimization with indexes
- Redis caching for frequently accessed data
- Async database operations
- Connection pooling
- Query result pagination
- Background task processing

## Security

- JWT token authentication
- Password hashing with bcrypt
- SQL injection prevention (SQLAlchemy ORM)
- CORS configuration
- Rate limiting per tenant
- Input validation with Pydantic
- Secure environment variable handling

## Monitoring & Logging

- Structured JSON logging
- Request/response logging
- Error tracking (Sentry integration ready)
- Performance metrics
- Health check endpoint: `/api/health`

## Contributing

1. Create feature branch
2. Write tests
3. Ensure all tests pass
4. Update documentation
5. Submit pull request

## License

Proprietary - AgileMind Platform

## Support

- **Documentation:** See component-specific READMEs
- **API Docs:** http://localhost:8000/docs
- **Issues:** GitHub Issues
- **Email:** support@agilemind.io

---

**Version:** 1.0.0  
**Last Updated:** November 11, 2025  
**Python Version:** 3.11+
