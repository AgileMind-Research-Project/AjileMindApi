# Platform Authentication API Routes

## Overview
API endpoints for Platform Home registration, tenant creation, and authentication flow.

**Base URL**: `/api/v1/platform`

---

## Endpoints

### 1. Register Tenant (Platform Home)

**Endpoint**: `POST /api/v1/platform/register-tenant`

**Description**: Register a new tenant company from Platform Home. Creates tenant, super admin user, and sends welcome email.

**Authentication**: None (Public endpoint)

**Request Body**:
```json
{
  "company_name": "Acme Corporation",
  "email": "admin@acme.com",
  "password": "SecurePass123!",
  "password_confirmation": "SecurePass123!"
}
```

**Validation Rules**:
- `company_name`: Required, 3-100 characters
- `email`: Required, valid email format
- `password`: Required, must meet password policy (8+ chars, uppercase, lowercase, number, symbol)
- `password_confirmation`: Required, must match password

**Success Response** (201 Created):
```json
{
  "success": true,
  "message": "Tenant created successfully",
  "data": {
    "tenant_id": "tn-abc123-xyz789",
    "company_name": "Acme Corporation",
    "user": {
      "user_id": "usr-123456",
      "email": "admin@acme.com",
      "first_name": null,
      "last_name": null,
      "role": "SUPER_ADMIN"
    },
    "tokens": {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "Bearer",
      "expires_in": 86400
    },
    "redirect_url": "http://localhost:3001/dashboard"
  }
}
```

**Error Responses**:

400 Bad Request:
```json
{
  "success": false,
  "message": "Validation error",
  "errors": {
    "email": ["Email already exists"],
    "password": ["Password must contain at least one uppercase letter"]
  }
}
```

409 Conflict:
```json
{
  "success": false,
  "message": "Company email already registered"
}
```

---

### 2. Login

**Endpoint**: `POST /api/v1/auth/login`

**Description**: Authenticate user and return JWT tokens.

**Authentication**: None

**Request Body**:
```json
{
  "email": "john.doe@acme.com",
  "password": "MyPassword123!"
}
```

**Success Response** (200 OK):
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "user": {
      "user_id": "usr-789012",
      "email": "john.doe@acme.com",
      "first_name": "John",
      "last_name": "Doe",
      "role": "DEVELOPER",
      "tenant_id": "tn-abc123-xyz789",
      "tenant_name": "Acme Corporation"
    },
    "tokens": {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "Bearer",
      "expires_in": 86400
    },
    "password_change_required": false
  }
}
```

**Error Responses**:

401 Unauthorized:
```json
{
  "success": false,
  "message": "Invalid email or password"
}
```

423 Locked:
```json
{
  "success": false,
  "message": "Account locked due to too many failed attempts. Try again in 15 minutes."
}
```

---

### 3. Refresh Token

**Endpoint**: `POST /api/v1/auth/refresh`

**Description**: Get new access token using refresh token.

**Authentication**: None

**Request Body**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Success Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 86400
  }
}
```

---

### 4. Logout

**Endpoint**: `POST /api/v1/auth/logout`

**Description**: Invalidate current session and tokens.

**Authentication**: Required (Bearer Token)

**Headers**:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Success Response** (200 OK):
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

---

### 5. Get Current User

**Endpoint**: `GET /api/v1/auth/me`

**Description**: Get currently authenticated user details.

**Authentication**: Required (Bearer Token)

**Success Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "user_id": "usr-789012",
    "email": "john.doe@acme.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "DEVELOPER",
    "tenant_id": "tn-abc123-xyz789",
    "tenant_name": "Acme Corporation",
    "status": "ACTIVE",
    "last_login_at": "2024-01-20T10:30:45Z",
    "created_at": "2024-01-15T09:00:00Z"
  }
}
```

---

### 6. Change Password

**Endpoint**: `POST /api/v1/auth/change-password`

**Description**: Change user password (authenticated users).

**Authentication**: Required (Bearer Token)

**Request Body**:
```json
{
  "current_password": "OldPassword123!",
  "new_password": "NewPassword456!",
  "new_password_confirmation": "NewPassword456!"
}
```

**Success Response** (200 OK):
```json
{
  "success": true,
  "message": "Password changed successfully",
  "data": {
    "password_updated": true,
    "password_change_required": false
  }
}
```

**Error Responses**:

400 Bad Request:
```json
{
  "success": false,
  "message": "Validation error",
  "errors": {
    "current_password": ["Current password is incorrect"],
    "new_password": ["Password must be at least 8 characters"]
  }
}
```

---

### 7. Forgot Password

**Endpoint**: `POST /api/v1/auth/forgot-password`

**Description**: Request password reset link via email.

**Authentication**: None

**Request Body**:
```json
{
  "email": "john.doe@acme.com"
}
```

**Success Response** (200 OK):
```json
{
  "success": true,
  "message": "If an account exists with this email, a password reset link has been sent"
}
```

**Note**: Always returns success for security (don't reveal if email exists).

---

### 8. Reset Password

**Endpoint**: `POST /api/v1/auth/reset-password`

**Description**: Reset password using token from email.

**Authentication**: None

**Request Body**:
```json
{
  "token": "abc123xyz789reset",
  "new_password": "NewSecurePass123!",
  "new_password_confirmation": "NewSecurePass123!"
}
```

**Success Response** (200 OK):
```json
{
  "success": true,
  "message": "Password reset successful. You can now log in with your new password."
}
```

**Error Responses**:

400 Bad Request:
```json
{
  "success": false,
  "message": "Invalid or expired reset token"
}
```

---

### 9. Verify Email

**Endpoint**: `GET /api/v1/auth/verify-email?token={token}`

**Description**: Verify email address using token from email.

**Authentication**: None

**Query Parameters**:
- `token`: Email verification token

**Success Response** (200 OK):
```json
{
  "success": true,
  "message": "Email verified successfully"
}
```

---

## User Management API Routes

**Base URL**: `/api/v1/users`

### 10. Invite User (Super Admin/Admin)

**Endpoint**: `POST /api/v1/users/invite`

**Description**: Invite new user to tenant. Auto-generates password and sends welcome email.

**Authentication**: Required (SUPER_ADMIN or ADMIN role)

**Headers**:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
X-Tenant-ID: tn-abc123-xyz789
```

**Request Body**:
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@acme.com",
  "role": "DEVELOPER"
}
```

**Success Response** (201 Created):
```json
{
  "success": true,
  "message": "User invited successfully",
  "data": {
    "user_id": "usr-789012",
    "email": "john.doe@acme.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "DEVELOPER",
    "status": "PENDING_ACTIVATION",
    "temporary_password": "Johnjohn.doe@123",
    "welcome_email_sent": true,
    "created_at": "2024-01-20T10:30:45Z"
  }
}
```

**Auto-Generated Password Logic**:
- Format: `{FirstName}{EmailLocalPart}@123`
- Example: John Doe with john.doe@acme.com → `Johnjohn.doe@123`
- If doesn't meet policy, add symbol: `Johnjohn.doe@123!`

**Error Responses**:

403 Forbidden:
```json
{
  "success": false,
  "message": "Insufficient permissions. Only SUPER_ADMIN or ADMIN can invite users."
}
```

409 Conflict:
```json
{
  "success": false,
  "message": "User with this email already exists in this tenant"
}
```

---

### 11. List Users

**Endpoint**: `GET /api/v1/users`

**Description**: Get list of users in tenant.

**Authentication**: Required

**Query Parameters**:
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20)
- `role`: Filter by role
- `status`: Filter by status

**Success Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "users": [
      {
        "user_id": "usr-123456",
        "email": "admin@acme.com",
        "first_name": null,
        "last_name": null,
        "role": "SUPER_ADMIN",
        "status": "ACTIVE",
        "last_login_at": "2024-01-20T10:30:45Z",
        "created_at": "2024-01-15T09:00:00Z"
      },
      {
        "user_id": "usr-789012",
        "email": "john.doe@acme.com",
        "first_name": "John",
        "last_name": "Doe",
        "role": "DEVELOPER",
        "status": "ACTIVE",
        "last_login_at": "2024-01-20T08:15:30Z",
        "created_at": "2024-01-16T10:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 2,
      "total_pages": 1
    }
  }
}
```

---

### 12. Get User by ID

**Endpoint**: `GET /api/v1/users/{user_id}`

**Description**: Get specific user details.

**Authentication**: Required

**Success Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "user_id": "usr-789012",
    "email": "john.doe@acme.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "DEVELOPER",
    "status": "ACTIVE",
    "tenant_id": "tn-abc123-xyz789",
    "last_login_at": "2024-01-20T08:15:30Z",
    "created_at": "2024-01-16T10:00:00Z",
    "updated_at": "2024-01-20T08:15:30Z"
  }
}
```

---

### 13. Update User

**Endpoint**: `PUT /api/v1/users/{user_id}`

**Description**: Update user details.

**Authentication**: Required (SUPER_ADMIN or own profile)

**Request Body**:
```json
{
  "first_name": "John",
  "last_name": "Doe Updated",
  "role": "SCRUM_MASTER"
}
```

**Success Response** (200 OK):
```json
{
  "success": true,
  "message": "User updated successfully",
  "data": {
    "user_id": "usr-789012",
    "email": "john.doe@acme.com",
    "first_name": "John",
    "last_name": "Doe Updated",
    "role": "SCRUM_MASTER",
    "status": "ACTIVE",
    "updated_at": "2024-01-20T11:00:00Z"
  }
}
```

---

### 14. Delete User

**Endpoint**: `DELETE /api/v1/users/{user_id}`

**Description**: Delete/deactivate user.

**Authentication**: Required (SUPER_ADMIN only)

**Success Response** (200 OK):
```json
{
  "success": true,
  "message": "User deleted successfully"
}
```

---

## Role Management API Routes

**Base URL**: `/api/v1/roles`

### 15. List Roles

**Endpoint**: `GET /api/v1/roles`

**Description**: Get list of available roles.

**Authentication**: Required

**Success Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "roles": [
      {
        "role_id": "role-1",
        "name": "SUPER_ADMIN",
        "display_name": "Super Administrator",
        "description": "Full system access",
        "is_system_role": true,
        "permissions": ["*"]
      },
      {
        "role_id": "role-2",
        "name": "PROJECT_MANAGER",
        "display_name": "Project Manager",
        "description": "Manage projects, sprints, and teams",
        "is_system_role": true,
        "permissions": [
          "sprints.read",
          "sprints.write",
          "tasks.read",
          "tasks.write",
          "users.read"
        ]
      },
      {
        "role_id": "role-3",
        "name": "DEVELOPER",
        "display_name": "Developer",
        "description": "Work on tasks and sprints",
        "is_system_role": true,
        "permissions": [
          "sprints.read",
          "tasks.read",
          "tasks.write"
        ]
      }
    ]
  }
}
```

---

### 16. Create Custom Role

**Endpoint**: `POST /api/v1/roles`

**Description**: Create custom role with specific permissions.

**Authentication**: Required (SUPER_ADMIN only)

**Request Body**:
```json
{
  "name": "QA_ENGINEER",
  "display_name": "QA Engineer",
  "description": "Quality assurance and testing",
  "permissions": [
    "sprints.read",
    "tasks.read",
    "tasks.write",
    "meetings.read"
  ]
}
```

**Success Response** (201 Created):
```json
{
  "success": true,
  "message": "Role created successfully",
  "data": {
    "role_id": "role-custom-1",
    "name": "QA_ENGINEER",
    "display_name": "QA Engineer",
    "description": "Quality assurance and testing",
    "is_system_role": false,
    "permissions": [
      "sprints.read",
      "tasks.read",
      "tasks.write",
      "meetings.read"
    ],
    "created_at": "2024-01-20T11:00:00Z"
  }
}
```

---

## Password Policy Validation

**Endpoint**: `POST /api/v1/auth/validate-password`

**Description**: Validate password against policy (used by frontend).

**Authentication**: None

**Request Body**:
```json
{
  "password": "TestPass123!"
}
```

**Success Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "is_valid": true,
    "requirements": {
      "min_length": true,
      "has_uppercase": true,
      "has_lowercase": true,
      "has_number": true,
      "has_symbol": true
    }
  }
}
```

**Failure Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "is_valid": false,
    "requirements": {
      "min_length": true,
      "has_uppercase": false,
      "has_lowercase": true,
      "has_number": true,
      "has_symbol": false
    },
    "errors": [
      "Password must contain at least one uppercase letter",
      "Password must contain at least one symbol"
    ]
  }
}
```

---

## Common Error Responses

### 401 Unauthorized
```json
{
  "success": false,
  "message": "Authentication required",
  "error_code": "UNAUTHORIZED"
}
```

### 403 Forbidden
```json
{
  "success": false,
  "message": "Insufficient permissions",
  "error_code": "FORBIDDEN"
}
```

### 404 Not Found
```json
{
  "success": false,
  "message": "Resource not found",
  "error_code": "NOT_FOUND"
}
```

### 422 Validation Error
```json
{
  "success": false,
  "message": "Validation error",
  "errors": {
    "field_name": ["Error message 1", "Error message 2"]
  },
  "error_code": "VALIDATION_ERROR"
}
```

### 429 Too Many Requests
```json
{
  "success": false,
  "message": "Too many requests. Please try again later.",
  "retry_after": 900,
  "error_code": "RATE_LIMIT_EXCEEDED"
}
```

### 500 Internal Server Error
```json
{
  "success": false,
  "message": "An unexpected error occurred",
  "error_code": "INTERNAL_SERVER_ERROR"
}
```

---

## JWT Token Structure

**Access Token Claims**:
```json
{
  "sub": "usr-789012",
  "email": "john.doe@acme.com",
  "tenant_id": "tn-abc123-xyz789",
  "role": "DEVELOPER",
  "type": "access",
  "iat": 1705747200,
  "exp": 1705833600
}
```

**Refresh Token Claims**:
```json
{
  "sub": "usr-789012",
  "tenant_id": "tn-abc123-xyz789",
  "type": "refresh",
  "iat": 1705747200,
  "exp": 1708339200
}
```

---

## Rate Limiting

- **Login**: 5 attempts per 15 minutes per IP
- **Password Reset**: 3 requests per hour per email
- **User Invitation**: 20 invites per hour per tenant
- **General API**: 60 requests per minute per user

---

## Audit Logging

All authentication and user management actions are logged:
- User registration
- Login attempts (success/failure)
- Password changes
- Password resets
- User invitations
- Role changes
- Permission modifications

Log format:
```json
{
  "log_id": "log-123456",
  "tenant_id": "tn-abc123-xyz789",
  "user_id": "usr-789012",
  "event_type": "user.login.success",
  "event_data": {
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0...",
    "method": "password"
  },
  "created_at": "2024-01-20T10:30:45Z"
}
```
