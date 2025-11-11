# AI & Intelligence API Routes

## Base URL
```
/api/v1/ai
```

---

## Endpoints

### 1. Chat with AI Assistant
**POST** `/chat`

**Description:** Interact with AI assistant for historical context and insights.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "query": "Show me all blockers from last sprint",
  "context": {
    "type": "sprint",
    "id": "sprint-uuid"
  },
  "conversationId": "conv-uuid"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "response": "I found 5 blockers in Sprint 23:\n\n1. API rate limiting (High severity) - Resolved by John Doe\n2. Database migration issues (Medium) - Resolved\n3. Third-party integration timeout (High) - Still active\n4. Memory leak in background tasks (Medium) - Resolved\n5. SSL certificate expiration (Low) - Resolved\n\nWould you like more details on any of these?",
    "conversationId": "conv-uuid",
    "sources": [
      {
        "type": "meeting",
        "id": "meeting-uuid-1",
        "date": "2024-01-18"
      },
      {
        "type": "task",
        "id": "task-uuid-2"
      }
    ],
    "suggestions": [
      "View details of active blockers",
      "Compare with current sprint blockers",
      "Show blocker resolution trends"
    ]
  }
}
```

---

### 2. Generate Task Suggestions
**POST** `/tasks/generate`

**Description:** AI-generate task suggestions from context.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "context": "User authentication with JWT and refresh tokens",
  "storyPoints": 13,
  "sprintId": "sprint-uuid",
  "assigneeId": "user-uuid"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "suggestions": [
      {
        "title": "Set up JWT authentication middleware",
        "description": "Create middleware to validate JWT tokens on protected routes",
        "type": "feature",
        "priority": "high",
        "storyPoints": 3,
        "estimatedHours": 6,
        "tags": ["backend", "security", "authentication"],
        "acceptanceCriteria": [
          "JWT tokens validated on all protected routes",
          "Invalid tokens return 401 status",
          "Token expiration handled correctly"
        ]
      },
      {
        "title": "Implement refresh token rotation",
        "description": "Add refresh token endpoint with rotation for enhanced security",
        "type": "feature",
        "priority": "high",
        "storyPoints": 5,
        "estimatedHours": 10,
        "tags": ["backend", "security", "authentication"],
        "acceptanceCriteria": [
          "Refresh tokens stored securely",
          "Old refresh tokens invalidated after use",
          "Token rotation implemented"
        ]
      },
      {
        "title": "Add login rate limiting",
        "description": "Implement rate limiting to prevent brute force attacks",
        "type": "feature",
        "priority": "medium",
        "storyPoints": 2,
        "estimatedHours": 4,
        "tags": ["backend", "security"],
        "acceptanceCriteria": [
          "Max 5 login attempts per 15 minutes",
          "Account locked after failed attempts",
          "Admin notification on multiple failures"
        ]
      },
      {
        "title": "Write authentication unit tests",
        "description": "Comprehensive test coverage for auth endpoints",
        "type": "technical",
        "priority": "medium",
        "storyPoints": 3,
        "estimatedHours": 6,
        "tags": ["testing", "backend"],
        "acceptanceCriteria": [
          "100% code coverage for auth module",
          "Edge cases tested",
          "Integration tests included"
        ]
      }
    ],
    "totalStoryPoints": 13,
    "confidence": 0.87
  }
}
```

---

### 3. Predict Sprint Risks
**POST** `/predict/risks`

**Description:** Predict potential risks for sprint or project.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "sprintId": "sprint-uuid",
  "projectId": "project-uuid"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "risks": [
      {
        "title": "Sprint may not complete on time",
        "description": "Current velocity suggests 85% completion probability",
        "probability": 0.65,
        "impact": 0.75,
        "riskScore": 49,
        "category": "schedule",
        "indicators": [
          "Velocity 15% below average",
          "3 high-priority tasks still in todo",
          "2 unresolved blockers"
        ],
        "recommendations": [
          "Move 2 low-priority tasks to next sprint",
          "Address blockers in next standup",
          "Consider adding team capacity"
        ]
      },
      {
        "title": "Quality issues likely to increase",
        "description": "Bug rate trending upward",
        "probability": 0.45,
        "impact": 0.60,
        "riskScore": 27,
        "category": "quality",
        "indicators": [
          "Bug rate increased by 25%",
          "Code review time decreased",
          "Test coverage dropped to 78%"
        ],
        "recommendations": [
          "Allocate more time for code reviews",
          "Increase test coverage targets",
          "Schedule tech debt sprint"
        ]
      }
    ],
    "overallRiskLevel": "medium",
    "confidence": 0.82
  }
}
```

---

### 4. Estimate Task Complexity
**POST** `/estimate`

**Description:** AI-estimate story points for task.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "title": "Implement real-time chat feature",
  "description": "Add WebSocket-based real-time chat with message persistence",
  "type": "feature",
  "tags": ["backend", "websocket", "real-time"]
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "estimatedStoryPoints": 8,
    "confidence": 0.78,
    "estimatedHours": 16,
    "complexity": "high",
    "reasoning": "Real-time features require WebSocket setup, message persistence, connection management, and testing. Similar tasks in history averaged 7-9 story points.",
    "similarTasks": [
      {
        "id": "task-uuid-1",
        "title": "Real-time notifications",
        "storyPoints": 5,
        "actualHours": 12
      },
      {
        "id": "task-uuid-2",
        "title": "Live sprint board updates",
        "storyPoints": 8,
        "actualHours": 18
      }
    ],
    "breakdown": [
      {
        "component": "WebSocket server setup",
        "points": 2
      },
      {
        "component": "Message persistence",
        "points": 3
      },
      {
        "component": "Client integration",
        "points": 2
      },
      {
        "component": "Testing & optimization",
        "points": 1
      }
    ]
  }
}
```

---

### 5. Analyze Team Capacity
**POST** `/capacity/analyze`

**Description:** Analyze and predict team capacity.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "teamId": "team-uuid",
  "sprintId": "sprint-uuid",
  "timeframe": "next-sprint"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "totalCapacity": 50,
    "availableCapacity": 42,
    "utilized": 38,
    "remaining": 4,
    "recommendations": {
      "idealLoad": 45,
      "maxLoad": 50,
      "buffer": 5,
      "suggestion": "Team is slightly under-utilized. Can accept 4 more story points."
    },
    "members": [
      {
        "id": "user-uuid-1",
        "name": "John Doe",
        "capacity": 10,
        "assigned": 8,
        "available": 2,
        "efficiency": 95,
        "recommendation": "Can take 1-2 more story points"
      }
    ],
    "factors": [
      {
        "factor": "1 team member on vacation",
        "impact": -8
      },
      {
        "factor": "Historical velocity average",
        "impact": 0
      }
    ],
    "confidence": 0.85
  }
}
```

---

### 6. Generate Sprint Summary
**POST** `/summary/sprint`

**Description:** Generate AI summary of sprint.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "sprintId": "sprint-uuid"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "summary": "Sprint 24 achieved 90% completion with 38 story points delivered out of 42 planned. The team demonstrated strong collaboration with no major blockers. Key accomplishments include completion of the payment integration and API rate limiting improvements. Two low-priority tasks were moved to the next sprint.",
    "highlights": [
      "Payment gateway integration completed ahead of schedule",
      "Zero critical bugs reported",
      "All team members attended retrospective",
      "Velocity improved by 12% from previous sprint"
    ],
    "challenges": [
      "API documentation took longer than estimated",
      "Testing environment issues caused 1-day delay"
    ],
    "metrics": {
      "completion": 90,
      "velocity": 38,
      "quality": 94,
      "teamMorale": 85
    },
    "nextSteps": [
      "Address API documentation gap",
      "Improve testing environment stability",
      "Continue momentum into next sprint"
    ]
  }
}
```

---

### 7. Detect Code Patterns
**POST** `/code/analyze`

**Description:** Analyze code patterns and suggest improvements (via GitHub integration).

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "repositoryId": "repo-uuid",
  "branch": "main",
  "filePath": "src/api/auth.py"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "issues": [
      {
        "type": "security",
        "severity": "high",
        "line": 45,
        "message": "Hardcoded secret key detected",
        "suggestion": "Move to environment variable"
      },
      {
        "type": "performance",
        "severity": "medium",
        "line": 78,
        "message": "N+1 query detected",
        "suggestion": "Use eager loading or join"
      }
    ],
    "suggestions": [
      "Consider adding input validation",
      "Add error handling for database operations",
      "Improve test coverage (currently 65%)"
    ],
    "quality": {
      "score": 72,
      "maintainability": 68,
      "complexity": 7.2,
      "duplicates": 3
    }
  }
}
```

---

### 8. Get AI Insights
**GET** `/insights`

**Description:** Get personalized AI insights.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Query Parameters:**
- `context`: sprint, project, team, personal

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "insights": [
      {
        "type": "productivity",
        "title": "Velocity trending upward",
        "description": "Your team's velocity has increased by 15% over the last 3 sprints",
        "sentiment": "positive",
        "priority": "high",
        "actionable": false
      },
      {
        "type": "risk",
        "title": "Blocker count increasing",
        "description": "3 blockers detected in current sprint, up from average of 1.2",
        "sentiment": "warning",
        "priority": "high",
        "actionable": true,
        "actions": [
          "Schedule blocker resolution meeting",
          "Review blocker trends"
        ]
      },
      {
        "type": "recommendation",
        "title": "Consider adding automated testing",
        "description": "Manual testing consuming 18% of sprint time",
        "sentiment": "neutral",
        "priority": "medium",
        "actionable": true,
        "actions": [
          "Research automation tools",
          "Add testing tasks to backlog"
        ]
      }
    ]
  }
}
```

---

## Error Responses

### 429 Too Many Requests
```json
{
  "success": false,
  "message": "AI API rate limit exceeded. Please try again in 60 seconds."
}
```

### 503 Service Unavailable
```json
{
  "success": false,
  "message": "AI service temporarily unavailable"
}
```

---

## Notes
- AI features powered by OpenAI GPT-4
- Chat conversations retained for 30 days
- Task generation uses historical team data
- Risk predictions updated every 6 hours
- Capacity analysis considers PTO and holidays
- Rate limits: 100 requests per hour per user
