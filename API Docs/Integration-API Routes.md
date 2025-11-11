# Integration API Routes

## Base URL
```
/api/v1/integrations
```

---

## Endpoints

## Jira Integration

### 1. Connect Jira
**POST** `/jira/connect`

**Description:** Connect Jira account via OAuth.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "siteUrl": "https://yourcompany.atlassian.net",
  "redirectUri": "https://agilemind.com/integrations/jira/callback"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "authUrl": "https://auth.atlassian.com/authorize?client_id=...",
    "state": "state-token"
  }
}
```

---

### 2. Jira OAuth Callback
**POST** `/jira/callback`

**Description:** Complete Jira OAuth flow.

**Request Body:**
```json
{
  "code": "auth-code-from-jira",
  "state": "state-token"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Jira connected successfully",
  "data": {
    "connected": true,
    "siteName": "Your Company",
    "userEmail": "admin@company.com"
  }
}
```

---

### 3. Sync Jira Issues
**POST** `/jira/sync`

**Description:** Sync Jira issues to AgileMind tasks.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "projectKey": "PROJ",
  "sprintId": "sprint-uuid",
  "syncType": "two-way"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Sync initiated",
  "data": {
    "jobId": "sync-job-uuid",
    "status": "in-progress",
    "estimatedCompletion": "2024-01-20T10:35:00Z"
  }
}
```

---

### 4. Get Jira Sync Status
**GET** `/jira/sync/:jobId`

**Description:** Check sync job status.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "jobId": "sync-job-uuid",
    "status": "completed",
    "summary": {
      "issuesImported": 23,
      "issuesUpdated": 5,
      "issuesSkipped": 2,
      "errors": 0
    },
    "completedAt": "2024-01-20T10:34:00Z"
  }
}
```

---

### 5. Disconnect Jira
**DELETE** `/jira/disconnect`

**Description:** Disconnect Jira integration.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Jira disconnected successfully"
}
```

---

## Microsoft Teams Integration

### 6. Connect Teams
**POST** `/teams/connect`

**Description:** Connect Microsoft Teams via OAuth.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "redirectUri": "https://agilemind.com/integrations/teams/callback"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "authUrl": "https://login.microsoftonline.com/...",
    "state": "state-token"
  }
}
```

---

### 7. Teams OAuth Callback
**POST** `/teams/callback`

**Description:** Complete Teams OAuth flow.

**Request Body:**
```json
{
  "code": "auth-code-from-teams",
  "state": "state-token"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Teams connected successfully",
  "data": {
    "connected": true,
    "tenantName": "Your Company",
    "userEmail": "admin@company.com"
  }
}
```

---

### 8. Send Teams Notification
**POST** `/teams/notify`

**Description:** Send notification to Teams channel.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "channelId": "channel-uuid",
  "message": "Sprint 24 has started!",
  "type": "sprint-started",
  "data": {
    "sprintId": "sprint-uuid",
    "sprintName": "Sprint 24"
  }
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Notification sent successfully",
  "data": {
    "messageId": "teams-message-id"
  }
}
```

---

### 9. Schedule Teams Meeting
**POST** `/teams/meetings`

**Description:** Create Teams meeting via integration.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "title": "Daily Standup",
  "startTime": "2024-01-21T09:00:00Z",
  "duration": 15,
  "attendees": [
    "john@company.com",
    "jane@company.com"
  ]
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "message": "Teams meeting created successfully",
  "data": {
    "meetingId": "teams-meeting-id",
    "joinUrl": "https://teams.microsoft.com/l/meetup-join/...",
    "scheduledTime": "2024-01-21T09:00:00Z"
  }
}
```

---

### 10. Configure Teams Webhook
**POST** `/teams/webhooks`

**Description:** Configure webhook for Teams notifications.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "channelId": "channel-uuid",
  "events": ["sprint-started", "sprint-completed", "blocker-detected"],
  "active": true
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "message": "Webhook configured successfully",
  "data": {
    "webhookId": "webhook-uuid",
    "webhookUrl": "https://api.agilemind.com/webhooks/teams/webhook-uuid"
  }
}
```

---

### 11. Disconnect Teams
**DELETE** `/teams/disconnect`

**Description:** Disconnect Teams integration.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Teams disconnected successfully"
}
```

---

## GitHub Integration

### 12. Connect GitHub
**POST** `/github/connect`

**Description:** Connect GitHub account via OAuth.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "redirectUri": "https://agilemind.com/integrations/github/callback"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "authUrl": "https://github.com/login/oauth/authorize?client_id=...",
    "state": "state-token"
  }
}
```

---

### 13. GitHub OAuth Callback
**POST** `/github/callback`

**Description:** Complete GitHub OAuth flow.

**Request Body:**
```json
{
  "code": "auth-code-from-github",
  "state": "state-token"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "GitHub connected successfully",
  "data": {
    "connected": true,
    "username": "yourcompany",
    "avatarUrl": "https://avatars.githubusercontent.com/..."
  }
}
```

---

### 14. List Repositories
**GET** `/github/repositories`

**Description:** List connected GitHub repositories.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "repositories": [
      {
        "id": "repo-123",
        "name": "agile-mind-backend",
        "fullName": "yourcompany/agile-mind-backend",
        "private": true,
        "url": "https://github.com/yourcompany/agile-mind-backend"
      }
    ]
  }
}
```

---

### 15. Get Repository CI/CD Status
**GET** `/github/repositories/:repoId/cicd`

**Description:** Get CI/CD pipeline status.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "workflows": [
      {
        "id": "workflow-123",
        "name": "Build & Test",
        "status": "success",
        "lastRun": "2024-01-20T14:30:00Z",
        "duration": 180,
        "branch": "main",
        "conclusion": "success"
      }
    ],
    "deployments": [
      {
        "id": "deploy-123",
        "environment": "production",
        "status": "success",
        "ref": "main",
        "sha": "abc123...",
        "deployedAt": "2024-01-20T15:00:00Z"
      }
    ]
  }
}
```

---

### 16. Link Task to Pull Request
**POST** `/github/link`

**Description:** Link AgileMind task to GitHub PR.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "taskId": "task-uuid",
  "repositoryId": "repo-123",
  "pullRequestNumber": 42
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Task linked to PR successfully",
  "data": {
    "taskId": "task-uuid",
    "prUrl": "https://github.com/yourcompany/repo/pull/42",
    "prTitle": "Add authentication feature"
  }
}
```

---

### 17. Configure GitHub Webhook
**POST** `/github/webhooks`

**Description:** Configure webhook for GitHub events.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "repositoryId": "repo-123",
  "events": ["push", "pull_request", "workflow_run", "deployment"],
  "active": true
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "message": "Webhook configured successfully",
  "data": {
    "webhookId": "webhook-uuid",
    "webhookUrl": "https://api.agilemind.com/webhooks/github/webhook-uuid",
    "secret": "webhook-secret-key"
  }
}
```

---

### 18. Disconnect GitHub
**DELETE** `/github/disconnect`

**Description:** Disconnect GitHub integration.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "GitHub disconnected successfully"
}
```

---

## General Integration Endpoints

### 19. List All Integrations
**GET** `/`

**Description:** List all configured integrations.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "integrations": [
      {
        "provider": "jira",
        "connected": true,
        "connectedAt": "2024-01-15T10:30:00Z",
        "lastSync": "2024-01-20T09:00:00Z",
        "status": "active"
      },
      {
        "provider": "teams",
        "connected": true,
        "connectedAt": "2024-01-16T14:20:00Z",
        "status": "active"
      },
      {
        "provider": "github",
        "connected": true,
        "connectedAt": "2024-01-17T11:10:00Z",
        "repositoriesConnected": 3,
        "status": "active"
      }
    ]
  }
}
```

---

## Error Responses

### 401 Unauthorized
```json
{
  "success": false,
  "message": "OAuth authentication failed. Please reconnect integration."
}
```

### 429 Too Many Requests
```json
{
  "success": false,
  "message": "Integration API rate limit exceeded"
}
```

---

## Notes
- OAuth tokens refreshed automatically
- Jira sync runs every 30 minutes by default
- Teams notifications support adaptive cards
- GitHub webhooks sign requests with HMAC
- All integrations support disconnect/reconnect
- Integration credentials encrypted at rest
