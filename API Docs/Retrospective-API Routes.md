# Retrospective API Routes

## Base URL
```
/api/v1/retrospectives
```

---

## Endpoints

### 1. List Retrospectives
**GET** `/`

**Description:** Get all retrospectives.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Query Parameters:**
- `sprintId`: Filter by sprint
- `status`: Filter by status (draft, published)
- `page`: Page number (default: 1)
- `pageSize`: Items per page (default: 20)

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "retrospectives": [
      {
        "id": "retro-uuid",
        "sprintId": "sprint-uuid",
        "sprintName": "Sprint 24",
        "date": "2024-01-29T16:00:00Z",
        "status": "published",
        "feedbackCount": 18,
        "sentiment": {
          "overall": 0.72,
          "positive": 0.60,
          "negative": 0.18
        },
        "actionPlanCount": 5,
        "createdAt": "2024-01-29T14:30:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "pageSize": 20,
      "total": 12,
      "totalPages": 1
    }
  }
}
```

---

### 2. Get Retrospective by ID
**GET** `/:retroId`

**Description:** Get detailed retrospective information.

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
    "id": "retro-uuid",
    "sprintId": "sprint-uuid",
    "sprintName": "Sprint 24",
    "date": "2024-01-29T16:00:00Z",
    "status": "published",
    "feedback": [
      {
        "id": "feedback-uuid-1",
        "type": "went-well",
        "content": "Great team collaboration",
        "votes": 8,
        "authorId": "user-uuid",
        "authorName": "John Doe",
        "anonymous": false,
        "createdAt": "2024-01-29T16:10:00Z"
      },
      {
        "id": "feedback-uuid-2",
        "type": "needs-improvement",
        "content": "Better code review process needed",
        "votes": 5,
        "anonymous": true,
        "createdAt": "2024-01-29T16:12:00Z"
      },
      {
        "id": "feedback-uuid-3",
        "type": "action",
        "content": "Implement automated testing",
        "votes": 12,
        "authorId": "user-uuid-2",
        "authorName": "Jane Smith",
        "anonymous": false,
        "createdAt": "2024-01-29T16:15:00Z"
      }
    ],
    "sentiment": {
      "overall": 0.72,
      "positive": 0.60,
      "neutral": 0.22,
      "negative": 0.18,
      "keywords": ["collaboration", "testing", "code review", "deployment"],
      "emotions": {
        "satisfied": 0.45,
        "concerned": 0.25,
        "frustrated": 0.10,
        "optimistic": 0.20
      }
    },
    "actionPlan": {
      "items": [
        {
          "id": "action-uuid",
          "description": "Set up automated testing pipeline",
          "priority": 1,
          "ownerId": "user-uuid-3",
          "ownerName": "Bob Johnson",
          "dueDate": "2024-02-15",
          "status": "pending"
        }
      ],
      "createdAt": "2024-01-29T17:00:00Z"
    },
    "participants": [
      {
        "id": "user-uuid-1",
        "name": "John Doe",
        "avatar": "https://example.com/avatar.jpg",
        "contributionCount": 3
      }
    ],
    "createdAt": "2024-01-29T14:30:00Z",
    "publishedAt": "2024-01-29T17:00:00Z"
  }
}
```

---

### 3. Create Retrospective
**POST** `/`

**Description:** Create new retrospective.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "sprintId": "sprint-uuid",
  "date": "2024-01-29T16:00:00Z",
  "type": "standard"
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "message": "Retrospective created successfully",
  "data": {
    "id": "retro-uuid",
    "sprintId": "sprint-uuid",
    "status": "draft",
    "createdAt": "2024-01-29T14:30:00Z"
  }
}
```

---

### 4. Add Feedback
**POST** `/:retroId/feedback`

**Description:** Add feedback item to retrospective.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "type": "went-well",
  "content": "Sprint planning was very effective",
  "anonymous": false
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "message": "Feedback added successfully",
  "data": {
    "id": "feedback-uuid",
    "type": "went-well",
    "content": "Sprint planning was very effective",
    "votes": 0,
    "createdAt": "2024-01-29T16:10:00Z"
  }
}
```

---

### 5. Vote on Feedback
**POST** `/:retroId/feedback/:feedbackId/vote`

**Description:** Vote on feedback item.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Vote recorded successfully",
  "data": {
    "feedbackId": "feedback-uuid",
    "votes": 9
  }
}
```

---

### 6. Group Feedback
**POST** `/:retroId/feedback/group`

**Description:** Group similar feedback items.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "feedbackIds": ["feedback-uuid-1", "feedback-uuid-2"],
  "groupTitle": "Testing concerns"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Feedback grouped successfully",
  "data": {
    "groupId": "group-uuid",
    "title": "Testing concerns",
    "itemCount": 2
  }
}
```

---

### 7. Generate Action Plan
**POST** `/:retroId/action-plan/generate`

**Description:** AI-generate action plan from feedback.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Action plan generated successfully",
  "data": {
    "items": [
      {
        "id": "action-uuid",
        "description": "Implement automated testing for API endpoints",
        "priority": 1,
        "suggestedOwner": "user-uuid-3",
        "suggestedDueDate": "2024-02-15",
        "basedOnFeedback": ["feedback-uuid-2", "feedback-uuid-5"]
      }
    ]
  }
}
```

---

### 8. Update Action Plan
**PUT** `/:retroId/action-plan/:actionId`

**Description:** Update action plan item.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "description": "Implement automated testing for all API endpoints",
  "ownerId": "user-uuid-3",
  "dueDate": "2024-02-20",
  "priority": 1
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Action plan item updated successfully"
}
```

---

### 9. Mark Action Complete
**PATCH** `/:retroId/action-plan/:actionId/complete`

**Description:** Mark action plan item as complete.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Action plan item marked as complete"
}
```

---

### 10. Publish Retrospective
**POST** `/:retroId/publish`

**Description:** Publish retrospective (makes it read-only).

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Retrospective published successfully",
  "data": {
    "id": "retro-uuid",
    "status": "published",
    "publishedAt": "2024-01-29T17:00:00Z"
  }
}
```

---

### 11. Get Sentiment Analysis
**GET** `/:retroId/sentiment`

**Description:** Get detailed sentiment analysis.

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
    "overall": 0.72,
    "byType": {
      "went-well": 0.85,
      "needs-improvement": 0.40,
      "action": 0.65
    },
    "trend": "improving",
    "comparison": {
      "previousSprint": 0.65,
      "change": "+7%"
    },
    "keywords": [
      { "word": "collaboration", "sentiment": 0.90, "count": 8 },
      { "word": "testing", "sentiment": 0.55, "count": 6 }
    ],
    "emotions": {
      "satisfied": 0.45,
      "concerned": 0.25,
      "frustrated": 0.10,
      "optimistic": 0.20
    }
  }
}
```

---

### 12. Get Retrospective Trends
**GET** `/trends`

**Description:** Get historical retrospective trends.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Query Parameters:**
- `timeframe`: last-6-sprints, last-quarter, last-year

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "sentimentTrend": [
      { "sprintId": "sprint-20", "overall": 0.60 },
      { "sprintId": "sprint-21", "overall": 0.65 },
      { "sprintId": "sprint-22", "overall": 0.70 },
      { "sprintId": "sprint-23", "overall": 0.68 },
      { "sprintId": "sprint-24", "overall": 0.72 }
    ],
    "recurringThemes": [
      {
        "theme": "Testing automation",
        "frequency": 5,
        "avgSentiment": 0.55,
        "sprints": ["sprint-20", "sprint-21", "sprint-22", "sprint-23", "sprint-24"]
      }
    ],
    "actionPlanCompletion": {
      "average": 78,
      "trend": "increasing"
    }
  }
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "success": false,
  "message": "Cannot add feedback to published retrospective"
}
```

### 404 Not Found
```json
{
  "success": false,
  "message": "Retrospective not found"
}
```

---

## Notes
- Only one retrospective per sprint
- Feedback types: went-well, needs-improvement, action
- Anonymous feedback hides author identity
- AI-powered sentiment analysis on feedback
- Action items can be converted to tasks
- Published retrospectives are read-only
