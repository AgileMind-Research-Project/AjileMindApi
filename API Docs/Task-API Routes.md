# Task Management API Routes

## Base URL
```
/api/v1/tasks
```

---

## Endpoints

### 1. List Tasks
**GET** `/`

**Description:** Get all tasks.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Query Parameters:**
- `sprintId`: Filter by sprint
- `status`: Filter by status (todo, in-progress, review, done)
- `priority`: Filter by priority (low, medium, high, urgent)
- `assigneeId`: Filter by assignee
- `type`: Filter by type (feature, bug, technical, documentation)
- `page`: Page number (default: 1)
- `pageSize`: Items per page (default: 50)

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "tasks": [
      {
        "id": "task-uuid",
        "title": "Implement payment gateway",
        "description": "Integrate Stripe payment API",
        "status": "in-progress",
        "priority": "high",
        "type": "feature",
        "storyPoints": 8,
        "assigneeId": "user-uuid",
        "assignee": {
          "id": "user-uuid",
          "name": "John Doe",
          "avatar": "https://example.com/avatar.jpg"
        },
        "sprintId": "sprint-uuid",
        "tags": ["backend", "payment"],
        "dueDate": "2024-01-25",
        "createdAt": "2024-01-15T10:30:00Z",
        "updatedAt": "2024-01-20T14:30:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "pageSize": 50,
      "total": 123,
      "totalPages": 3
    }
  }
}
```

---

### 2. Get Task by ID
**GET** `/:taskId`

**Description:** Get detailed task information.

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
    "id": "task-uuid",
    "title": "Implement payment gateway",
    "description": "Integrate Stripe payment API with checkout flow",
    "status": "in-progress",
    "priority": "high",
    "type": "feature",
    "storyPoints": 8,
    "assigneeId": "user-uuid",
    "assignee": {
      "id": "user-uuid",
      "name": "John Doe",
      "avatar": "https://example.com/avatar.jpg"
    },
    "sprintId": "sprint-uuid",
    "sprint": {
      "id": "sprint-uuid",
      "name": "Sprint 24"
    },
    "tags": ["backend", "payment", "api"],
    "dueDate": "2024-01-25",
    "attachments": [
      {
        "id": "attachment-uuid",
        "name": "api-docs.pdf",
        "url": "https://example.com/files/api-docs.pdf",
        "size": 2048576
      }
    ],
    "comments": [
      {
        "id": "comment-uuid",
        "userId": "user-uuid-2",
        "userName": "Jane Smith",
        "content": "API key configured in .env",
        "createdAt": "2024-01-20T10:15:00Z"
      }
    ],
    "history": [
      {
        "action": "status_changed",
        "from": "todo",
        "to": "in-progress",
        "userId": "user-uuid",
        "timestamp": "2024-01-18T09:00:00Z"
      }
    ],
    "createdAt": "2024-01-15T10:30:00Z",
    "updatedAt": "2024-01-20T14:30:00Z"
  }
}
```

---

### 3. Create Task
**POST** `/`

**Description:** Create new task.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "title": "Add user authentication",
  "description": "Implement JWT-based authentication",
  "sprintId": "sprint-uuid",
  "priority": "high",
  "type": "feature",
  "storyPoints": 5,
  "assigneeId": "user-uuid",
  "tags": ["backend", "security"],
  "dueDate": "2024-01-28"
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "message": "Task created successfully",
  "data": {
    "id": "task-uuid",
    "title": "Add user authentication",
    "status": "todo",
    "createdAt": "2024-01-20T10:30:00Z"
  }
}
```

---

### 4. Update Task
**PUT** `/:taskId`

**Description:** Update task details.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "title": "Add user authentication with 2FA",
  "description": "Implement JWT-based authentication with two-factor support",
  "priority": "urgent",
  "storyPoints": 8,
  "tags": ["backend", "security", "2fa"]
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Task updated successfully",
  "data": {
    "id": "task-uuid",
    "updatedAt": "2024-01-20T14:30:00Z"
  }
}
```

---

### 5. Move Task
**PATCH** `/:taskId/move`

**Description:** Change task status.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "status": "in-progress"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Task moved successfully",
  "data": {
    "id": "task-uuid",
    "status": "in-progress",
    "updatedAt": "2024-01-20T14:30:00Z"
  }
}
```

---

### 6. Assign Task
**PATCH** `/:taskId/assign`

**Description:** Assign task to user.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "assigneeId": "user-uuid"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Task assigned successfully"
}
```

---

### 7. Delete Task
**DELETE** `/:taskId`

**Description:** Delete task.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Task deleted successfully"
}
```

---

### 8. Add Comment
**POST** `/:taskId/comments`

**Description:** Add comment to task.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "content": "Payment API testing completed successfully"
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "message": "Comment added successfully",
  "data": {
    "id": "comment-uuid",
    "content": "Payment API testing completed successfully",
    "userId": "user-uuid",
    "createdAt": "2024-01-20T10:30:00Z"
  }
}
```

---

### 9. Upload Attachment
**POST** `/:taskId/attachments`

**Description:** Upload file attachment.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
Content-Type: multipart/form-data
```

**Request Body:**
```
Form Data:
- file: [file]
```

**Response:** `201 Created`
```json
{
  "success": true,
  "message": "Attachment uploaded successfully",
  "data": {
    "id": "attachment-uuid",
    "name": "design-mockup.png",
    "url": "https://example.com/files/design-mockup.png",
    "size": 1048576,
    "uploadedAt": "2024-01-20T10:30:00Z"
  }
}
```

---

### 10. Get Task History
**GET** `/:taskId/history`

**Description:** Get task change history.

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
    "history": [
      {
        "action": "created",
        "userId": "user-uuid",
        "userName": "John Doe",
        "timestamp": "2024-01-15T10:30:00Z"
      },
      {
        "action": "status_changed",
        "from": "todo",
        "to": "in-progress",
        "userId": "user-uuid",
        "userName": "John Doe",
        "timestamp": "2024-01-18T09:00:00Z"
      },
      {
        "action": "assigned",
        "to": "user-uuid-2",
        "toName": "Jane Smith",
        "userId": "user-uuid",
        "userName": "John Doe",
        "timestamp": "2024-01-19T14:20:00Z"
      }
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
  "message": "Invalid status transition"
}
```

### 404 Not Found
```json
{
  "success": false,
  "message": "Task not found"
}
```

---

## Notes
- Tasks are automatically linked to sprints
- Story points range from 1-13 (Fibonacci sequence)
- Status transitions tracked in history
- File uploads limited to 10MB per file
- Supports drag-and-drop status changes via WebSocket
