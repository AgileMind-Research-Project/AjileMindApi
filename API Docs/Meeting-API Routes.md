# Meeting Management API Routes

## Base URL
```
/api/v1/meetings
```

---

## Endpoints

### 1. List Meetings
**GET** `/`

**Description:** Get all meetings.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Query Parameters:**
- `type`: Filter by type (standup, planning, retrospective, review)
- `status`: Filter by status (scheduled, in-progress, completed, cancelled)
- `startDate`: Filter from date
- `endDate`: Filter to date
- `page`: Page number (default: 1)
- `pageSize`: Items per page (default: 20)

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "meetings": [
      {
        "id": "meeting-uuid",
        "title": "Daily Standup",
        "type": "standup",
        "date": "2024-01-20T09:00:00Z",
        "duration": 15,
        "status": "completed",
        "participants": [
          {
            "id": "user-uuid-1",
            "name": "John Doe",
            "attended": true
          }
        ],
        "blockerCount": 2,
        "actionItemCount": 3,
        "sentiment": 0.75,
        "createdAt": "2024-01-19T10:30:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "pageSize": 20,
      "total": 156,
      "totalPages": 8
    }
  }
}
```

---

### 2. Get Meeting by ID
**GET** `/:meetingId`

**Description:** Get detailed meeting information.

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
    "id": "meeting-uuid",
    "title": "Daily Standup",
    "type": "standup",
    "date": "2024-01-20T09:00:00Z",
    "duration": 15,
    "status": "completed",
    "participants": [
      {
        "id": "user-uuid-1",
        "name": "John Doe",
        "avatar": "https://example.com/avatar.jpg",
        "attended": true,
        "speakingTime": 120
      }
    ],
    "transcript": "Full meeting transcript text...",
    "summary": "Team discussed progress on payment feature. Two blockers identified...",
    "blockers": [
      {
        "id": "blocker-uuid",
        "description": "API rate limiting issues",
        "severity": "high",
        "detectedAt": "2024-01-20T09:05:00Z",
        "assigneeId": "user-uuid-2"
      }
    ],
    "actionItems": [
      {
        "id": "action-uuid",
        "description": "Review API documentation",
        "ownerId": "user-uuid-1",
        "dueDate": "2024-01-21",
        "completed": false
      }
    ],
    "sentiment": 0.75,
    "recording": {
      "url": "https://example.com/recordings/meeting-uuid.mp4",
      "duration": 900
    },
    "createdAt": "2024-01-19T10:30:00Z",
    "completedAt": "2024-01-20T09:15:00Z"
  }
}
```

---

### 3. Schedule Meeting
**POST** `/`

**Description:** Schedule new meeting.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "title": "Sprint Planning",
  "type": "planning",
  "date": "2024-01-22T10:00:00Z",
  "duration": 120,
  "participants": ["user-uuid-1", "user-uuid-2", "user-uuid-3"],
  "recurring": {
    "enabled": true,
    "frequency": "weekly",
    "endDate": "2024-06-30"
  },
  "teamsIntegration": {
    "enabled": true,
    "sendInvite": true
  }
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "message": "Meeting scheduled successfully",
  "data": {
    "id": "meeting-uuid",
    "title": "Sprint Planning",
    "date": "2024-01-22T10:00:00Z",
    "teamsLink": "https://teams.microsoft.com/l/meetup-join/...",
    "createdAt": "2024-01-20T10:30:00Z"
  }
}
```

---

### 4. Update Meeting
**PUT** `/:meetingId`

**Description:** Update meeting details.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "title": "Sprint Planning - Q1",
  "date": "2024-01-22T14:00:00Z",
  "duration": 90
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Meeting updated successfully",
  "data": {
    "id": "meeting-uuid",
    "updatedAt": "2024-01-20T14:30:00Z"
  }
}
```

---

### 5. Start Meeting
**POST** `/:meetingId/start`

**Description:** Start scheduled meeting.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Meeting started",
  "data": {
    "id": "meeting-uuid",
    "status": "in-progress",
    "startedAt": "2024-01-20T09:00:00Z",
    "transcriptionEnabled": true
  }
}
```

---

### 6. End Meeting
**POST** `/:meetingId/end`

**Description:** End in-progress meeting.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Meeting ended successfully",
  "data": {
    "id": "meeting-uuid",
    "status": "completed",
    "endedAt": "2024-01-20T09:15:00Z",
    "summary": "AI-generated meeting summary...",
    "blockerCount": 2,
    "actionItemCount": 3
  }
}
```

---

### 7. Cancel Meeting
**POST** `/:meetingId/cancel`

**Description:** Cancel scheduled meeting.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "reason": "Rescheduling due to team availability"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Meeting cancelled successfully"
}
```

---

### 8. Get Meeting Transcript
**GET** `/:meetingId/transcript`

**Description:** Get meeting transcript.

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
    "transcript": [
      {
        "speaker": "John Doe",
        "timestamp": "2024-01-20T09:01:30Z",
        "text": "Yesterday I completed the payment integration..."
      },
      {
        "speaker": "Jane Smith",
        "timestamp": "2024-01-20T09:02:15Z",
        "text": "I'm blocked on the API rate limiting issue..."
      }
    ],
    "fullText": "Complete transcript text..."
  }
}
```

---

### 9. Get Blockers
**GET** `/:meetingId/blockers`

**Description:** Get detected blockers.

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
    "blockers": [
      {
        "id": "blocker-uuid",
        "description": "API rate limiting preventing data sync",
        "severity": "high",
        "detectedAt": "2024-01-20T09:05:00Z",
        "context": "Mentioned by Jane Smith during standup",
        "suggestedAssignee": "user-uuid-2",
        "resolved": false
      }
    ]
  }
}
```

---

### 10. Get Action Items
**GET** `/:meetingId/action-items`

**Description:** Get meeting action items.

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
    "actionItems": [
      {
        "id": "action-uuid",
        "description": "Review API rate limiting documentation",
        "ownerId": "user-uuid-1",
        "ownerName": "John Doe",
        "dueDate": "2024-01-21",
        "completed": false,
        "createdAt": "2024-01-20T09:15:00Z"
      }
    ]
  }
}
```

---

### 11. Mark Action Item Complete
**PATCH** `/:meetingId/action-items/:actionItemId`

**Description:** Mark action item as complete.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "completed": true
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Action item marked as complete"
}
```

---

### 12. Get Sentiment Analysis
**GET** `/:meetingId/sentiment`

**Description:** Get sentiment analysis.

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
    "overall": 0.75,
    "positive": 0.60,
    "neutral": 0.25,
    "negative": 0.15,
    "emotions": {
      "confident": 0.45,
      "concerned": 0.20,
      "frustrated": 0.10,
      "enthusiastic": 0.25
    },
    "keywords": ["progress", "blocked", "deadline", "testing"]
  }
}
```

---

## Error Responses

### 409 Conflict
```json
{
  "success": false,
  "message": "Meeting time conflicts with existing meeting"
}
```

### 400 Bad Request
```json
{
  "success": false,
  "message": "Cannot start meeting before scheduled time"
}
```

---

## Notes
- Real-time transcription powered by AI
- Automatic blocker detection using NLP
- Sentiment analysis on meeting completion
- Integration with MS Teams for video calls
- Recording stored for 90 days
- Action items can be converted to tasks
