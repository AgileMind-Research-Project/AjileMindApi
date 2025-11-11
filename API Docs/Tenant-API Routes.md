# Tenant Management API Routes

## Base URL
```
/api/v1/tenants
```

---

## Endpoints

### 1. Create Tenant
**POST** `/`

**Description:** Create a new tenant organization.

**Headers:**
```
Authorization: Bearer <admin-token>
```

**Request Body:**
```json
{
  "name": "Acme Corporation",
  "subdomain": "acme",
  "plan": "professional",
  "adminEmail": "admin@acme.com",
  "adminPassword": "SecurePass123!",
  "settings": {
    "allowSignups": true,
    "requireApproval": false,
    "maxUsers": 50
  }
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "message": "Tenant created successfully",
  "data": {
    "id": "tenant-uuid",
    "name": "Acme Corporation",
    "subdomain": "acme",
    "plan": "professional",
    "status": "active",
    "createdAt": "2024-01-15T10:30:00Z"
  }
}
```

---

### 2. Get Tenant Details
**GET** `/:tenantId`

**Description:** Get tenant information.

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
    "id": "tenant-uuid",
    "name": "Acme Corporation",
    "subdomain": "acme",
    "plan": "professional",
    "status": "active",
    "settings": {
      "allowSignups": true,
      "requireApproval": false,
      "maxUsers": 50,
      "features": ["sprints", "meetings", "retrospectives", "ai-insights"]
    },
    "usage": {
      "activeUsers": 23,
      "storageUsed": "2.5GB",
      "apiCallsThisMonth": 15230
    },
    "createdAt": "2024-01-15T10:30:00Z"
  }
}
```

---

### 3. Update Tenant
**PUT** `/:tenantId`

**Description:** Update tenant settings.

**Headers:**
```
Authorization: Bearer <admin-token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "name": "Acme Corp Ltd",
  "settings": {
    "maxUsers": 100,
    "allowSignups": false
  }
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Tenant updated successfully",
  "data": {
    "id": "tenant-uuid",
    "name": "Acme Corp Ltd",
    "updatedAt": "2024-01-20T14:30:00Z"
  }
}
```

---

### 4. List All Tenants
**GET** `/`

**Description:** List all tenants (Super Admin only).

**Headers:**
```
Authorization: Bearer <super-admin-token>
```

**Query Parameters:**
- `page`: Page number (default: 1)
- `pageSize`: Items per page (default: 20)
- `status`: Filter by status (active, suspended, deleted)
- `plan`: Filter by plan (free, starter, professional, enterprise)

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "tenants": [
      {
        "id": "tenant-uuid-1",
        "name": "Acme Corporation",
        "subdomain": "acme",
        "plan": "professional",
        "status": "active",
        "activeUsers": 23,
        "createdAt": "2024-01-15T10:30:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "pageSize": 20,
      "total": 45,
      "totalPages": 3
    }
  }
}
```

---

### 5. Suspend Tenant
**POST** `/:tenantId/suspend`

**Description:** Suspend tenant access.

**Headers:**
```
Authorization: Bearer <super-admin-token>
```

**Request Body:**
```json
{
  "reason": "Payment overdue"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Tenant suspended successfully"
}
```

---

### 6. Activate Tenant
**POST** `/:tenantId/activate`

**Description:** Reactivate suspended tenant.

**Headers:**
```
Authorization: Bearer <super-admin-token>
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Tenant activated successfully"
}
```

---

### 7. Delete Tenant
**DELETE** `/:tenantId`

**Description:** Soft delete tenant (marks as deleted, data retained for 30 days).

**Headers:**
```
Authorization: Bearer <super-admin-token>
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Tenant deleted successfully. Data will be permanently removed after 30 days."
}
```

---

### 8. Get Tenant Usage Statistics
**GET** `/:tenantId/usage`

**Description:** Get tenant usage metrics.

**Headers:**
```
Authorization: Bearer <admin-token>
X-Tenant-ID: <tenant-uuid>
```

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "users": {
      "total": 50,
      "active": 42,
      "limit": 50
    },
    "storage": {
      "used": "2.5GB",
      "limit": "10GB"
    },
    "apiCalls": {
      "thisMonth": 15230,
      "limit": 50000
    },
    "features": {
      "sprints": 24,
      "meetings": 156,
      "retrospectives": 12,
      "aiQueries": 340
    }
  }
}
```

---

## Error Responses

### 403 Forbidden
```json
{
  "success": false,
  "message": "Insufficient permissions. Admin access required."
}
```

### 409 Conflict
```json
{
  "success": false,
  "message": "Subdomain already taken"
}
```

### 402 Payment Required
```json
{
  "success": false,
  "message": "Tenant usage limit exceeded. Please upgrade plan."
}
```

---

## Notes
- Subdomain must be unique and lowercase
- Tenant ID is automatically included in JWT claims
- Multi-tenant isolation enforced at middleware level
- Super admin can access all tenants
