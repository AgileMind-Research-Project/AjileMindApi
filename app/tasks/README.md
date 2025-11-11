# Background Tasks Module

## Overview
Celery-based background task processing for long-running operations.

## Structure

```
tasks/
├── celery_app.py         # Celery configuration
├── meeting_tasks.py      # Meeting processing tasks
├── sync_tasks.py         # Synchronization tasks
├── ai_tasks.py           # AI/ML processing tasks
├── email_tasks.py        # Email notifications
└── __init__.py
```

## Celery Configuration

```python
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "agilemind",
    broker=settings.RABBITMQ_URL,
    backend=settings.REDIS_URL
)
```

## Task Types

### 1. Meeting Tasks
- Audio transcription (long-running)
- Blocker detection
- Summary generation
- Jira synchronization

```python
@celery_app.task
async def process_meeting_audio(meeting_id: int):
    # Transcribe audio
    transcript = await transcribe_audio(audio_file)
    
    # Detect blockers
    blockers = await detect_blockers(transcript)
    
    # Save results
    await save_meeting_results(meeting_id, transcript, blockers)
```

### 2. Sync Tasks
- Periodic Jira sync
- Teams notifications
- CI/CD status updates

```python
@celery_app.task
async def sync_jira_issues(tenant_id: int):
    client = JiraClient(tenant_id)
    await client.sync_all_issues()
```

### 3. AI Tasks
- Batch predictions
- Model training
- Risk analysis
- Report generation

```python
@celery_app.task
async def generate_sprint_report(sprint_id: int):
    data = await collect_sprint_data(sprint_id)
    report = await ai_service.generate_report(data)
    await save_report(sprint_id, report)
```

### 4. Email Tasks
- Welcome emails
- Notifications
- Reports
- Alerts

## Scheduling

```python
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'sync-jira-every-hour': {
        'task': 'app.tasks.sync_tasks.sync_jira_issues',
        'schedule': crontab(minute=0),  # Every hour
    },
    'daily-reports': {
        'task': 'app.tasks.ai_tasks.generate_daily_reports',
        'schedule': crontab(hour=9, minute=0),  # 9 AM daily
    },
}
```

## Usage

```python
# Trigger task
from app.tasks import process_meeting_audio

task = process_meeting_audio.delay(meeting_id=123)

# Check status
status = task.status  # PENDING, STARTED, SUCCESS, FAILURE

# Get result
result = task.get(timeout=10)
```

## Monitoring

```bash
# Start Flower (monitoring UI)
celery -A app.tasks.celery_app flower

# Access at: http://localhost:5555
```

---

**Related:** [AI Module](../ai/README.md), [Services](../services/README.md)
