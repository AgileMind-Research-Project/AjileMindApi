# External Integrations Module

## Overview
Connectors for external platforms like Jira, Microsoft Teams, GitHub, and GitLab.

## Structure

```
integrations/
├── jira/
│   ├── client.py         # Jira API client
│   ├── webhooks.py       # Webhook handlers
│   ├── sync.py           # Data synchronization
│   └── README.md
├── teams/
│   ├── bot.py            # Teams bot
│   ├── webhooks.py       # Webhook handlers
│   ├── notifications.py  # Send notifications
│   └── README.md
├── github/
│   ├── client.py         # GitHub API client
│   ├── webhooks.py       # Webhook handlers
│   └── README.md
└── __init__.py
```

## Jira Integration

### Features
- OAuth 2.0 authentication
- Issue synchronization
- Status mapping
- Webhook handling
- Custom field mapping

```python
from app.integrations.jira import JiraClient

client = JiraClient(tenant_id=tenant.id)
await client.authenticate()

# Sync issue
issue = await client.sync_issue(jira_key="PROJ-123")

# Create issue
new_issue = await client.create_issue(
    project="PROJ",
    summary="Task from AgileMind",
    description=task.description
)
```

### Webhooks
- `issue_created`
- `issue_updated`
- `issue_deleted`
- `status_changed`

## Microsoft Teams Integration

### Features
- Bot framework integration
- Meeting notifications
- Blocker alerts
- Daily standup reminders
- Real-time updates

```python
from app.integrations.teams import TeamsBot

bot = TeamsBot(tenant_id=tenant.id)

# Send notification
await bot.send_message(
    channel_id="channel-123",
    message="Sprint started!",
    attachments=[card]
)

# Handle incoming message
await bot.handle_message(message)
```

### Bot Commands
- `/standup` - Start daily standup
- `/blockers` - Show current blockers
- `/sprint` - Sprint information
- `/help` - Show available commands

## GitHub Integration

### Features
- Repository webhooks
- CI/CD pipeline monitoring
- Pull request tracking
- Deployment status

```python
from app.integrations.github import GitHubClient

client = GitHubClient(tenant_id=tenant.id)

# Get CI/CD status
status = await client.get_pipeline_status(repo="org/repo")

# Get recent deployments
deployments = await client.get_deployments(repo="org/repo")
```

## Webhook Security

All webhooks validated using:
- Signature verification
- Timestamp validation
- IP allowlisting
- HTTPS only

```python
from app.integrations.webhooks import verify_signature

@router.post("/webhooks/jira")
async def jira_webhook(
    request: Request,
    signature: str = Header(None)
):
    payload = await request.body()
    
    if not verify_signature(payload, signature):
        raise UnauthorizedException("Invalid signature")
    
    # Process webhook
    await process_jira_webhook(payload)
```

## Configuration

Each integration requires configuration stored per tenant:

```python
{
    "jira": {
        "url": "https://company.atlassian.net",
        "client_id": "xxx",
        "client_secret": "xxx",
        "access_token": "xxx",
        "project_mappings": {"PROJ": "project-id"}
    },
    "teams": {
        "tenant_id": "xxx",
        "bot_id": "xxx",
        "webhook_url": "xxx"
    }
}
```

---

**Related:** [Services](../services/README.md), [API](../api/README.md)
