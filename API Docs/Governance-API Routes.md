# Governance & Metrics API Routes

## Base URL
```
/api/v1/governance
```

---

## Endpoints

### 1. Get Project Metrics
**GET** `/metrics`

**Description:** Get overall project metrics and KPIs.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Query Parameters:**
- `projectId`: Filter by project
- `timeframe`: last-30-days, last-quarter, last-year

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "velocity": {
      "current": 42,
      "average": 38,
      "trend": "increasing",
      "change": "+10.5%"
    },
    "leadTime": {
      "average": 4.2,
      "trend": "decreasing",
      "unit": "days"
    },
    "cycleTime": {
      "average": 2.8,
      "trend": "stable",
      "unit": "days"
    },
    "deploymentFrequency": {
      "count": 23,
      "perWeek": 5.75,
      "trend": "increasing"
    },
    "bugRate": {
      "current": 0.08,
      "average": 0.12,
      "trend": "decreasing",
      "unit": "bugs per story point"
    },
    "teamProductivity": {
      "score": 85,
      "tasksCompleted": 234,
      "sprintsCompleted": 12
    }
  }
}
```

---

### 2. Get Risk Dashboard
**GET** `/risks`

**Description:** Get all project risks.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Query Parameters:**
- `projectId`: Filter by project
- `severity`: Filter by severity (low, medium, high, critical)
- `status`: Filter by status (active, mitigated, resolved)

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "risks": [
      {
        "id": "risk-uuid",
        "title": "Sprint velocity declining",
        "description": "Team velocity has decreased by 15% over last 3 sprints",
        "severity": "high",
        "probability": 0.75,
        "impact": 0.80,
        "riskScore": 60,
        "category": "performance",
        "detectedBy": "ai",
        "detectedAt": "2024-01-20T10:30:00Z",
        "mitigationPlan": "Review team capacity and workload distribution",
        "status": "active",
        "assigneeId": "user-uuid"
      }
    ],
    "summary": {
      "total": 12,
      "critical": 1,
      "high": 4,
      "medium": 5,
      "low": 2,
      "aiDetected": 7,
      "manuallyAdded": 5
    }
  }
}
```

---

### 3. Create Risk
**POST** `/risks`

**Description:** Create new risk manually.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "title": "Key developer leaving",
  "description": "Senior developer planning to leave in 2 months",
  "severity": "high",
  "probability": 0.90,
  "impact": 0.70,
  "category": "resource",
  "mitigationPlan": "Knowledge transfer and hiring replacement"
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "message": "Risk created successfully",
  "data": {
    "id": "risk-uuid",
    "riskScore": 63,
    "createdAt": "2024-01-20T10:30:00Z"
  }
}
```

---

### 4. Update Risk
**PUT** `/risks/:riskId`

**Description:** Update risk details.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "status": "mitigated",
  "mitigationNotes": "Hired replacement developer, handover in progress"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Risk updated successfully"
}
```

---

### 5. Get CI/CD Status
**GET** `/cicd`

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
    "repositories": [
      {
        "id": "repo-uuid",
        "name": "agile-mind-backend",
        "provider": "github",
        "pipelines": [
          {
            "id": "pipeline-uuid",
            "name": "Build & Test",
            "status": "success",
            "lastRun": "2024-01-20T14:30:00Z",
            "duration": 180,
            "branch": "main"
          }
        ],
        "deployments": [
          {
            "id": "deploy-uuid",
            "environment": "production",
            "status": "success",
            "version": "v2.5.3",
            "deployedAt": "2024-01-20T15:00:00Z"
          }
        ],
        "metrics": {
          "successRate": 94.5,
          "avgDuration": 165,
          "failureCount": 3,
          "totalRuns": 54
        }
      }
    ]
  }
}
```

---

### 6. Get Delay Analytics
**GET** `/delays`

**Description:** Analyze project delays and predictions.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Query Parameters:**
- `projectId`: Filter by project
- `sprintId`: Filter by sprint

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "current": {
      "delayedTasks": 5,
      "delayedSprints": 1,
      "avgDelayDays": 2.4
    },
    "predictions": {
      "sprintCompletion": {
        "estimated": "2024-01-31",
        "original": "2024-01-29",
        "confidence": 0.82,
        "delayDays": 2
      },
      "riskFactors": [
        {
          "factor": "Blocker count increasing",
          "impact": "high",
          "contribution": 0.45
        },
        {
          "factor": "Team capacity reduced",
          "impact": "medium",
          "contribution": 0.30
        }
      ]
    },
    "rootCauses": [
      {
        "cause": "Technical blockers",
        "frequency": 8,
        "avgDelayDays": 3.5
      },
      {
        "cause": "Scope creep",
        "frequency": 5,
        "avgDelayDays": 2.1
      }
    ],
    "recommendations": [
      "Address blocking issues in daily standups",
      "Review sprint scope and remove low-priority items",
      "Increase team capacity or extend sprint by 2 days"
    ]
  }
}
```

---

### 7. Get Budget Tracking
**GET** `/budget`

**Description:** Get project budget and cost tracking.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Query Parameters:**
- `projectId`: Filter by project

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "budget": {
      "total": 500000,
      "spent": 285000,
      "remaining": 215000,
      "percentUsed": 57
    },
    "burnRate": {
      "monthly": 47500,
      "estimated": "2024-08-15"
    },
    "breakdown": {
      "personnel": 220000,
      "infrastructure": 35000,
      "tools": 15000,
      "other": 15000
    },
    "forecast": {
      "projectedTotal": 525000,
      "overbudget": 25000,
      "confidence": 0.75
    },
    "costByFeature": [
      {
        "feature": "Authentication System",
        "cost": 45000,
        "storyPoints": 89,
        "costPerPoint": 505.62
      }
    ]
  }
}
```

---

### 8. Get Team Performance
**GET** `/team-performance`

**Description:** Get team performance analytics.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Query Parameters:**
- `teamId`: Filter by team
- `timeframe`: last-30-days, last-quarter

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "team": {
      "id": "team-uuid",
      "name": "Backend Team",
      "memberCount": 8
    },
    "metrics": {
      "velocity": {
        "current": 42,
        "average": 38,
        "trend": "increasing"
      },
      "quality": {
        "bugRate": 0.08,
        "codeReviewScore": 87,
        "testCoverage": 82
      },
      "collaboration": {
        "meetingAttendance": 95,
        "codeReviews": 156,
        "pairProgramming": 34
      },
      "morale": {
        "sentimentScore": 0.75,
        "retrospectiveParticipation": 100,
        "trend": "stable"
      }
    },
    "members": [
      {
        "id": "user-uuid-1",
        "name": "John Doe",
        "tasksCompleted": 23,
        "velocity": 12,
        "codeReviews": 34,
        "performance": "above-average"
      }
    ]
  }
}
```

---

### 9. Export Report
**POST** `/reports/export`

**Description:** Generate and export governance report.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "reportType": "executive-summary",
  "format": "pdf",
  "timeframe": "last-quarter",
  "includeSections": ["metrics", "risks", "budget", "team-performance"]
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Report generated successfully",
  "data": {
    "reportId": "report-uuid",
    "downloadUrl": "https://example.com/reports/executive-summary-q1-2024.pdf",
    "expiresAt": "2024-01-27T10:30:00Z"
  }
}
```

---

### 10. Get Anomalies
**GET** `/anomalies`

**Description:** Get detected anomalies and unusual patterns.

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
    "anomalies": [
      {
        "id": "anomaly-uuid",
        "type": "velocity-drop",
        "severity": "medium",
        "description": "Velocity dropped by 20% in current sprint",
        "detectedAt": "2024-01-18T10:30:00Z",
        "metric": "velocity",
        "expectedValue": 42,
        "actualValue": 33,
        "deviation": -21.4,
        "possibleCauses": [
          "Team member on leave",
          "Increased blocker count",
          "Complex tasks underestimated"
        ]
      }
    ]
  }
}
```

---

## Error Responses

### 403 Forbidden
```json
{
  "success": false,
  "message": "Insufficient permissions. Manager role required."
}
```

---

## Notes
- Governance metrics updated daily
- AI-powered risk detection runs every 6 hours
- Budget tracking requires finance integration
- CI/CD integration with GitHub, GitLab, Bitbucket
- Reports retained for 1 year
