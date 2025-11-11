# Sprint Management API Routes

## Base URL
```
/api/v1/sprints
```

---

## Endpoints

### 1. List Sprints
**GET** `/`

**Description:** Get all sprints for tenant.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Query Parameters:**
- `status`: Filter by status (planned, active, completed, cancelled)
- `teamId`: Filter by team
- `page`: Page number (default: 1)
- `pageSize`: Items per page (default: 20)

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "sprints": [
      {
        "id": "sprint-uuid",
        "name": "Sprint 24",
        "goal": "Complete checkout feature",
        "startDate": "2024-01-15",
        "endDate": "2024-01-29",
        "status": "active",
        "teamId": "team-uuid",
        "velocity": 42,
        "capacity": 50,
        "progress": {
          "totalTasks": 23,
          "completedTasks": 15,
          "totalStoryPoints": 42,
          "completedStoryPoints": 28
        },
        "createdAt": "2024-01-10T10:30:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "pageSize": 20,
      "total": 24,
      "totalPages": 2
    }
  }
}
```

---

### 2. Get Sprint by ID
**GET** `/:sprintId`

**Description:** Get detailed sprint information.

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
    "id": "sprint-uuid",
    "name": "Sprint 24",
    "goal": "Complete checkout feature",
    "startDate": "2024-01-15",
    "endDate": "2024-01-29",
    "status": "active",
    "teamId": "team-uuid",
    "velocity": 42,
    "capacity": 50,
    "daysRemaining": 5,
    "metrics": {
      "totalTasks": 23,
      "completedTasks": 15,
      "inProgressTasks": 6,
      "todoTasks": 2,
      "totalStoryPoints": 42,
      "completedStoryPoints": 28,
      "burndownData": [
        { "date": "2024-01-15", "remaining": 42, "ideal": 42 },
        { "date": "2024-01-16", "remaining": 38, "ideal": 39 }
      ]
    },
    "team": {
      "id": "team-uuid",
      "name": "Backend Team",
      "members": [
        {
          "id": "user-uuid-1",
          "name": "John Doe",
          "role": "developer"
        }
      ]
    },
    "createdAt": "2024-01-10T10:30:00Z"
  }
}
```

---

### 3. Create Sprint
**POST** `/`

**Description:** Create new sprint.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "name": "Sprint 25",
  "goal": "Payment integration",
  "startDate": "2024-01-30",
  "endDate": "2024-02-13",
  "teamId": "team-uuid",
  "capacity": 50
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "message": "Sprint created successfully",
  "data": {
    "id": "sprint-uuid",
    "name": "Sprint 25",
    "goal": "Payment integration",
    "startDate": "2024-01-30",
    "endDate": "2024-02-13",
    "status": "planned",
    "createdAt": "2024-01-20T10:30:00Z"
  }
}
```

---

### 4. Update Sprint
**PUT** `/:sprintId`

**Description:** Update sprint details.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "name": "Sprint 25 - Payment",
  "goal": "Complete payment integration and testing",
  "capacity": 55
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Sprint updated successfully",
  "data": {
    "id": "sprint-uuid",
    "updatedAt": "2024-01-20T14:30:00Z"
  }
}
```

---

### 5. Start Sprint
**POST** `/:sprintId/start`

**Description:** Start a planned sprint.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Sprint started successfully",
  "data": {
    "id": "sprint-uuid",
    "status": "active",
    "startedAt": "2024-01-15T09:00:00Z"
  }
}
```

---

### 6. Complete Sprint
**POST** `/:sprintId/complete`

**Description:** Mark sprint as completed.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "notes": "Sprint completed successfully with 90% completion rate"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Sprint completed successfully",
  "data": {
    "id": "sprint-uuid",
    "status": "completed",
    "completedAt": "2024-01-29T17:00:00Z",
    "finalMetrics": {
      "completionRate": 90,
      "velocity": 42,
      "tasksCompleted": 21,
      "tasksIncomplete": 2
    }
  }
}
```

---

### 7. Delete Sprint
**DELETE** `/:sprintId`

**Description:** Delete sprint (only if no tasks).

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Sprint deleted successfully"
}
```

---

### 8. Get Sprint Burndown
**GET** `/:sprintId/burndown`

**Description:** Get sprint burndown chart data.

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
    "burndownData": [
      {
        "date": "2024-01-15",
        "remaining": 42,
        "ideal": 42,
        "completed": 0
      },
      {
        "date": "2024-01-16",
        "remaining": 38,
        "ideal": 39,
        "completed": 4
      }
    ]
  }
}
```

---

### 9. Get Sprint Velocity
**GET** `/:sprintId/velocity`

**Description:** Get velocity metrics.

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
    "currentSprint": 42,
    "average": 38,
    "trend": "increasing",
    "history": [
      { "sprintId": "sprint-23", "velocity": 35 },
      { "sprintId": "sprint-24", "velocity": 42 }
    ]
  }
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "success": false,
  "message": "Sprint dates overlap with existing sprint"
}
```

### 409 Conflict
```json
{
  "success": false,
  "message": "Cannot delete sprint with tasks. Please remove or reassign tasks first."
}
```

---

## Notes
- Only one active sprint per team at a time
- Sprint duration typically 2 weeks
- Capacity measured in story points
- Burndown calculated daily at midnight UTC
