# User Management API Routes

## Base URL
```
/api/v1/users
```

---

## Endpoints

### 1. List Users
**GET** `/`

**Description:** Get all users in tenant.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Query Parameters:**
- `page`: Page number (default: 1)
- `pageSize`: Items per page (default: 20)
- `role`: Filter by role (admin, manager, developer, viewer)
- `status`: Filter by status (active, inactive)
- `search`: Search by name or email

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "users": [
      {
        "id": "user-uuid",
        "email": "john@acme.com",
        "firstName": "John",
        "lastName": "Doe",
        "role": "developer",
        "avatar": "https://example.com/avatar.jpg",
        "status": "active",
        "lastLogin": "2024-01-20T09:15:00Z",
        "createdAt": "2024-01-15T10:30:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "pageSize": 20,
      "total": 42,
      "totalPages": 3
    }
  }
}
```

---

### 2. Get User by ID
**GET** `/:userId`

**Description:** Get specific user details.

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
    "id": "user-uuid",
    "email": "john@acme.com",
    "firstName": "John",
    "lastName": "Doe",
    "role": "developer",
    "avatar": "https://example.com/avatar.jpg",
    "bio": "Full-stack developer",
    "timezone": "America/New_York",
    "preferences": {
      "theme": "dark",
      "notifications": true,
      "emailDigest": true
    },
    "stats": {
      "tasksCompleted": 145,
      "sprintsParticipated": 23,
      "meetingsAttended": 89
    },
    "status": "active",
    "lastLogin": "2024-01-20T09:15:00Z",
    "createdAt": "2024-01-15T10:30:00Z"
  }
}
```

---

### 3. Create User
**POST** `/`

**Description:** Create new user (Admin only).

**Headers:**
```
Authorization: Bearer <admin-token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "email": "newuser@acme.com",
  "password": "SecurePass123!",
  "firstName": "Jane",
  "lastName": "Smith",
  "role": "developer"
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "message": "User created successfully",
  "data": {
    "id": "user-uuid",
    "email": "newuser@acme.com",
    "firstName": "Jane",
    "lastName": "Smith",
    "role": "developer",
    "createdAt": "2024-01-20T10:30:00Z"
  }
}
```

---

### 4. Update User
**PUT** `/:userId`

**Description:** Update user information.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "firstName": "John",
  "lastName": "Doe Jr.",
  "bio": "Senior full-stack developer",
  "timezone": "America/Los_Angeles",
  "preferences": {
    "theme": "light",
    "notifications": true
  }
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "User updated successfully",
  "data": {
    "id": "user-uuid",
    "firstName": "John",
    "lastName": "Doe Jr.",
    "updatedAt": "2024-01-20T14:30:00Z"
  }
}
```

---

### 5. Update User Role
**PATCH** `/:userId/role`

**Description:** Update user role (Admin only).

**Headers:**
```
Authorization: Bearer <admin-token>
X-Tenant-ID: <tenant-uuid>
```

**Request Body:**
```json
{
  "role": "manager"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "User role updated successfully"
}
```

---

### 6. Deactivate User
**POST** `/:userId/deactivate`

**Description:** Deactivate user account (Admin only).

**Headers:**
```
Authorization: Bearer <admin-token>
X-Tenant-ID: <tenant-uuid>
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "User deactivated successfully"
}
```

---

### 7. Reactivate User
**POST** `/:userId/activate`

**Description:** Reactivate user account (Admin only).

**Headers:**
```
Authorization: Bearer <admin-token>
X-Tenant-ID: <tenant-uuid>
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "User reactivated successfully"
}
```

---

### 8. Delete User
**DELETE** `/:userId`

**Description:** Delete user (Admin only).

**Headers:**
```
Authorization: Bearer <admin-token>
X-Tenant-ID: <tenant-uuid>
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "User deleted successfully"
}
```

---

### 9. Update User Avatar
**POST** `/:userId/avatar`

**Description:** Upload user avatar image.

**Headers:**
```
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
Content-Type: multipart/form-data
```

**Request Body:**
```
Form Data:
- avatar: [image file]
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Avatar updated successfully",
  "data": {
    "avatarUrl": "https://example.com/avatars/user-uuid.jpg"
  }
}
```

---

### 10. Get User Permissions
**GET** `/:userId/permissions`

**Description:** Get user's permissions.

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
    "permissions": [
      "sprints.view",
      "sprints.create",
      "sprints.edit",
      "tasks.view",
      "tasks.create",
      "tasks.edit",
      "tasks.delete",
      "meetings.view",
      "meetings.create"
    ],
    "role": "developer"
  }
}
```

---

## Error Responses

### 403 Forbidden
```json
{
  "success": false,
  "message": "Insufficient permissions"
}
```

### 409 Conflict
```json
{
  "success": false,
  "message": "Email already exists"
}
```

---

## Notes
- Users can only update their own profile unless they are admin
- Admin can manage all users in their tenant
- Role hierarchy: viewer < developer < manager < admin
- Avatar images are automatically resized and optimized
