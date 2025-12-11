# Project Management API - Documentation

## Overview

This feature allows authorized users (Super Admin, Admin, or Project Manager) to create projects that are automatically created in Jira Cloud and stored in the tenant's database.

## Architecture

### Backend Components

1. **Schema** (`app/schemas/project_schemas.py`)
   - `CreateProjectRequest`: Request model with validation
   - `ProjectResponse`: Response model for project data
   - `ProjectListResponse`: Paginated list response
   - Enums for project types and templates

2. **Repository** (`app/db/repositories/project_repository.py`)
   - Database operations (CRUD)
   - Handles tenant-specific database queries
   - Project existence checks

3. **Services**
   - **JiraService** (`app/services/jira_service.py`): Jira Cloud integration
     - `create_project()`: Creates project in Jira using REST API v3
     - Retrieves API token from AWS Secrets Manager
     - Error handling for duplicate projects
   
   - **ProjectService** (`app/services/project_service.py`): Business logic
     - Two-phase creation: Jira first, then database
     - Validation and error handling
     - Project management operations

4. **API Endpoints** (`app/api/v1/projects.py`)
   - `POST /api/v1/projects/`: Create new project
   - `GET /api/v1/projects/`: List all projects (paginated)
   - `GET /api/v1/projects/{id}`: Get project by ID
   - `PUT /api/v1/projects/{id}`: Update project
   - `DELETE /api/v1/projects/{id}`: Delete project from database

### Frontend Components

1. **CreateProjectForm** (`src/components/projects/CreateProjectForm.tsx`)
   - Form with validation
   - Auto-generates project key from name
   - Dropdown selectors for project type and template
   - Date range picker

2. **ProjectsList** (`src/components/projects/ProjectsList.tsx`)
   - Displays all projects in a table
   - Pagination support
   - Create new project button

3. **Projects Page** (`src/app/dashboard/projects/page.tsx`)
   - Combines list and create form
   - Toggle between views

## Database Schema

```sql
CREATE TABLE IF NOT EXISTS `projects` (
    `id` BIGINT NOT NULL COMMENT 'Project ID from Jira',
    `project_name` VARCHAR(255) NOT NULL,
    `key` VARCHAR(255) NOT NULL,
    `project_type` VARCHAR(100) NOT NULL,
    `start_date` DATE NOT NULL,
    `end_date` DATE NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY `unique_project_id` (`id`),
    UNIQUE KEY `unique_project_key` (`key`),
    UNIQUE KEY `unique_project_name` (`project_name`),
    
    INDEX `idx_project_name` (`project_name`),
    INDEX `idx_project_key` (`key`),
    INDEX `idx_start_date` (`start_date`),
    INDEX `idx_end_date` (`end_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## API Usage

### Prerequisites

1. **Jira Integration**: Must be configured first
   ```bash
   POST /api/v1/jira/connect
   {
     "jira_url": "https://yourcompany.atlassian.net",
     "email": "your-email@company.com",
     "api_token": "your-api-token"
   }
   ```

2. **Authentication**: User must have one of these roles:
   - `SUPER_ADMIN`
   - `ADMIN`
   - `PROJECT_MANAGER`

### Create Project

**Endpoint:** `POST /api/v1/projects/`

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "project_name": "Agile Scrum Project 2025",
  "key": "ASP2025",
  "project_type": "software",
  "start_date": "2025-01-01",
  "end_date": "2025-12-31",
  "description": "Scrum project for development team",
  "template": "com.pyxis.greenhopper.jira:gh-scrum-template"
}
```

**Response (Success):**
```json
{
  "success": true,
  "message": "Project created successfully in Jira and database",
  "data": {
    "id": 10038,
    "project_name": "Agile Scrum Project 2025",
    "key": "ASP2025",
    "project_type": "software",
    "start_date": "2025-01-01",
    "end_date": "2025-12-31",
    "jira_url": "https://yourcompany.atlassian.net/projects/ASP2025",
    "created_at": "2025-12-01T10:30:00"
  }
}
```

**Error Responses:**

1. **Project Name Already Exists (400)**
```json
{
  "detail": "Project name already exists: A project with that name already exists."
}
```

2. **Project Key Already Exists (400)**
```json
{
  "detail": "Project key already exists: Project 'Agile Scrum Project 2024' uses this project key."
}
```

3. **Jira Not Configured (404)**
```json
{
  "detail": "Jira integration not configured. Please connect Jira first."
}
```

4. **Insufficient Permissions (403)**
```json
{
  "detail": "Access denied. Only SUPER_ADMIN, ADMIN, PROJECT_MANAGER can create projects."
}
```

### List Projects

**Endpoint:** `GET /api/v1/projects/?page=1&limit=20`

**Response:**
```json
{
  "success": true,
  "message": "Found 5 project(s)",
  "data": [
    {
      "id": 10038,
      "project_name": "Agile Scrum Project 2025",
      "key": "ASP2025",
      "project_type": "software",
      "start_date": "2025-01-01",
      "end_date": "2025-12-31",
      "created_at": "2025-12-01T10:30:00",
      "updated_at": "2025-12-01T10:30:00"
    }
  ],
  "total": 5,
  "page": 1,
  "limit": 20
}
```

## Project Types

- **software**: Software development projects
- **business**: Business projects
- **service_desk**: IT service desk projects

## Project Templates

- **Scrum**: `com.pyxis.greenhopper.jira:gh-scrum-template`
- **Kanban**: `com.pyxis.greenhopper.jira:gh-kanban-template`
- **Classic**: `com.atlassian.jira-core-project-templates:jira-core-project-management`

## Validation Rules

1. **Project Name**
   - Required
   - 1-255 characters
   - Must be unique in tenant

2. **Project Key**
   - Required
   - 2-10 characters
   - Must be uppercase letters and numbers
   - Must start with a letter
   - Must be unique in Jira and tenant
   - Pattern: `^[A-Z][A-Z0-9]*$`

3. **Dates**
   - Both start_date and end_date are required
   - end_date must be after start_date

## Workflow

1. **User submits form** with project details
2. **Frontend validates** data client-side
3. **Backend validates** data server-side
4. **Check database** for existing project with same key/name
5. **Create in Jira** using REST API v3
   - Authenticate with stored API token
   - Get account ID for project lead
   - Create project with specified template
   - Handle Jira errors (duplicate key/name)
6. **If Jira succeeds**, save to database
   - Store Jira project ID
   - Store all project metadata
7. **Return success** with project data and Jira URL

## Error Handling

### Jira Creation Failures

If Jira project creation fails, no database entry is created. Common errors:

- **Duplicate project name**: Project name already exists in Jira
- **Duplicate project key**: Project key already used in Jira
- **Invalid credentials**: API token expired or invalid
- **Permission denied**: User doesn't have project creation permission in Jira

### Database Save Failures

If project is created in Jira but database save fails:
- Error message includes Jira project ID
- Manual cleanup may be required
- Consider implementing compensation logic

## Frontend Usage

### Basic Implementation

```tsx
import CreateProjectForm from '@/components/projects/CreateProjectForm';

function MyPage() {
  return (
    <CreateProjectForm
      onSuccess={() => {
        console.log('Project created!');
        // Redirect or refresh
      }}
      onCancel={() => {
        // Handle cancel
      }}
    />
  );
}
```

### With List

```tsx
import ProjectsList from '@/components/projects/ProjectsList';

function ProjectsPage() {
  const [showForm, setShowForm] = useState(false);
  
  return (
    <div>
      {showForm ? (
        <CreateProjectForm
          onSuccess={() => {
            setShowForm(false);
            // Refresh list
          }}
        />
      ) : (
        <ProjectsList onCreateNew={() => setShowForm(true)} />
      )}
    </div>
  );
}
```

## Testing

### Manual Testing Steps

1. **Setup Jira Integration**
   ```bash
   POST /api/v1/jira/connect
   ```

2. **Create Project**
   ```bash
   POST /api/v1/projects/
   ```

3. **Verify in Jira**
   - Check project exists at: `https://yourcompany.atlassian.net/projects/[KEY]`

4. **Verify in Database**
   ```sql
   SELECT * FROM projects WHERE `key` = 'ASP2025';
   ```

### Test Cases

1. ✅ Create project with valid data
2. ✅ Reject duplicate project name
3. ✅ Reject duplicate project key
4. ✅ Validate end_date > start_date
5. ✅ Validate project key format
6. ✅ Reject unauthorized users (non-admin/pm)
7. ✅ Handle Jira API errors gracefully
8. ✅ List projects with pagination

## Configuration

### Environment Variables

```env
# Backend (.env)
JIRA_URL=https://yourcompany.atlassian.net/
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=stored-in-aws-secrets-manager

# Frontend (.env.local)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Hardcoded Credentials (Temporary)

In `jira_service.py`, temporarily hardcoded for testing:
```python
JIRA_URL = "https://agilmind.atlassian.net/"
EMAIL = "lahiru.sa.200011@gmail.com"
API_TOKEN = "ATATT3xFfGF0-..."  # Stored in AWS Secrets Manager
```

**TODO**: Move to configurable settings per tenant.

## Future Enhancements

1. **Project Synchronization**
   - Sync project updates from Jira to database
   - Webhook integration for real-time updates

2. **Bulk Operations**
   - Import multiple projects from Jira
   - Bulk project creation

3. **Advanced Features**
   - Project members management
   - Project settings synchronization
   - Custom field mapping

4. **Monitoring**
   - Project creation success rate
   - Jira API usage tracking
   - Error alerting

## Troubleshooting

### Common Issues

1. **"Jira integration not configured"**
   - Solution: Connect Jira first using `/api/v1/jira/connect`

2. **"Project name already exists"**
   - Solution: Use a different project name
   - Check existing projects in Jira

3. **"Access denied"**
   - Solution: Ensure user has SUPER_ADMIN, ADMIN, or PROJECT_MANAGER role

4. **"Failed to retrieve API token"**
   - Solution: Reconnect Jira integration
   - Check AWS Secrets Manager configuration

## Support

For issues or questions:
- Check API documentation: `/api/v1/docs`
- Review logs: `logs/daily.log.YYYY-MM-DD`
- Contact: Backend team
