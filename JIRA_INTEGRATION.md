# Jira Cloud Integration API

## Overview
Complete Jira Cloud integration for AgileMind platform. Allows tenants to connect their Jira workspace and create issues directly from the application.

## Features
- ✅ Connect/disconnect Jira Cloud
- ✅ Create Jira issues (Tasks, Stories, Bugs, etc.)
- ✅ Fetch Jira projects
- ✅ Credential verification
- ✅ Multi-tenant support

## Setup

### 1. Database Migration
Run the SQL migration to create required tables:
```bash
mysql -u root -p agilemind_db < database_jira_migration.sql
```

### 2. Install Dependencies
```bash
pip install aiohttp==3.9.1
```

### 3. Get Jira API Token
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Give it a name (e.g., "AgileMind Integration")
4. Copy the generated token

## API Endpoints

### 1. Connect Jira (`POST /api/v1/jira/connect`)
**Authentication:** Required (Admin/Super Admin only)

Connect or update Jira Cloud integration.

**Request:**
```json
{
  "jira_url": "https://yourcompany.atlassian.net",
  "email": "your-email@company.com",
  "api_token": "your-api-token-here",
  "project_key": "PROJ"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Jira Cloud connected successfully",
  "data": {
    "jira_url": "https://yourcompany.atlassian.net",
    "email": "your-email@company.com",
    "project_key": "PROJ",
    "is_active": true
  }
}
```

### 2. Get Integration Status (`GET /api/v1/jira/status`)
**Authentication:** Required

Check if Jira is connected for the tenant.

**Response:**
```json
{
  "success": true,
  "message": "Jira is connected",
  "data": {
    "connected": true,
    "jira_url": "https://yourcompany.atlassian.net",
    "email": "your-email@company.com",
    "default_project": "PROJ",
    "is_active": true
  }
}
```

### 3. Get Projects (`GET /api/v1/jira/projects`)
**Authentication:** Required

Fetch all accessible Jira projects.

**Response:**
```json
{
  "success": true,
  "message": "Found 5 Jira projects",
  "data": [
    {
      "id": "10000",
      "key": "PROJ",
      "name": "Project Name",
      "project_type": "software",
      "avatar_url": "https://..."
    }
  ]
}
```

### 4. Create Issue (`POST /api/v1/jira/issues`)
**Authentication:** Required

Create a new Jira issue.

**Request:**
```json
{
  "project_key": "PROJ",
  "summary": "Implement user authentication",
  "description": "Add JWT-based authentication to the API",
  "issue_type": "Task",
  "priority": "High",
  "assignee_email": "developer@company.com",
  "labels": ["backend", "security"]
}
```

**Supported Issue Types:**
- Task
- Story
- Bug
- Epic
- Subtask

**Priority Levels:**
- Highest
- High
- Medium
- Low
- Lowest

**Response:**
```json
{
  "success": true,
  "message": "Jira issue PROJ-123 created successfully",
  "data": {
    "issue_key": "PROJ-123",
    "issue_id": "10050",
    "self": "https://yourcompany.atlassian.net/rest/api/3/issue/10050",
    "jira_url": "https://yourcompany.atlassian.net/browse/PROJ-123"
  }
}
```

### 5. Disconnect Jira (`DELETE /api/v1/jira/disconnect`)
**Authentication:** Required (Admin/Super Admin only)

Disconnect Jira integration.

**Response:**
```json
{
  "success": true,
  "message": "Jira integration disconnected successfully",
  "data": {
    "connected": false
  }
}
```

## Frontend Integration

### Example: Connect Jira
```javascript
// Connect Jira
async function connectJira() {
  const response = await fetch('http://localhost:8000/api/v1/jira/connect', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${accessToken}`
    },
    body: JSON.stringify({
      jira_url: 'https://yourcompany.atlassian.net',
      email: 'admin@company.com',
      api_token: 'your-api-token',
      project_key: 'PROJ'
    })
  });
  
  const data = await response.json();
  console.log(data);
}
```

### Example: Create Issue
```javascript
// Create Jira issue
async function createJiraIssue() {
  const response = await fetch('http://localhost:8000/api/v1/jira/issues', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${accessToken}`
    },
    body: JSON.stringify({
      project_key: 'PROJ',
      summary: 'New feature request',
      description: 'Detailed description here',
      issue_type: 'Story',
      priority: 'High',
      labels: ['frontend', 'ui']
    })
  });
  
  const data = await response.json();
  console.log('Created issue:', data.data.issue_key);
  console.log('Jira URL:', data.data.jira_url);
}
```

### Example: Check Status
```javascript
// Check if Jira is connected
async function checkJiraStatus() {
  const response = await fetch('http://localhost:8000/api/v1/jira/status', {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });
  
  const data = await response.json();
  if (data.data.connected) {
    console.log('Jira is connected!');
  } else {
    console.log('Jira not connected');
  }
}
```

## Security Notes

1. **API Token Storage**: Tokens are stored in the database. Consider encrypting them in production.
2. **HTTPS Only**: Always use HTTPS in production to protect API tokens.
3. **Access Control**: Only Admins and Super Admins can connect/disconnect Jira.
4. **Token Validation**: Credentials are validated before saving.

## Error Handling

Common error responses:

**Invalid Credentials:**
```json
{
  "detail": "Invalid Jira credentials. Please check your URL, email, and API token."
}
```

**Not Connected:**
```json
{
  "detail": "Jira integration not configured. Please connect Jira first."
}
```

**Permission Denied:**
```json
{
  "detail": "Admin access required"
}
```

## Testing in Swagger

1. Start the server: `python main.py`
2. Open Swagger: http://localhost:8000/api/v1/docs
3. Authenticate using the 🔒 button
4. Test the endpoints under "Jira Integration" tag

## Database Schema

```sql
jira_integrations:
- id (Primary Key)
- tenant_id (Foreign Key → tenants)
- jira_url
- email
- api_token
- project_key
- is_active
- created_at
- updated_at

jira_issue_sync:
- id (Primary Key)
- tenant_id (Foreign Key → tenants)
- task_id (Optional internal link)
- jira_issue_key
- jira_issue_id
- project_key
- summary
- status
- issue_type
- last_synced_at
- created_at
```

## Future Enhancements

- [ ] Webhook support for issue updates
- [ ] Two-way sync (Jira → AgileMind)
- [ ] Bulk issue creation
- [ ] Custom field mapping
- [ ] Sprint synchronization
- [ ] Comment synchronization
- [ ] Attachment support

## Support

For issues or questions, check:
- API Documentation: http://localhost:8000/api/v1/docs
- Logs: `logs/daily.log.*`
- Jira API Docs: https://developer.atlassian.com/cloud/jira/platform/rest/v3/
