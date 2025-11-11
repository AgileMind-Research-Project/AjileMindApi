# Authentication API Routes

## Base URL
```
/api/v1/auth
```

---

## Endpoints

### 1. Register User
**POST** `/register`

**Description:** Register a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "firstName": "John",
  "lastName": "Doe",
  "tenantId": "tenant-uuid"
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "message": "User registered successfully",
  "data": {
    "id": "user-uuid",
    "email": "user@example.com",
    "firstName": "John",
    "lastName": "Doe",
    "role": "developer",
    "tenantId": "tenant-uuid",
    "createdAt": "2024-01-15T10:30:00Z"
  }
}
```

---

### 2. Login
**POST** `/login`

**Description:** Authenticate user and receive JWT token.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refreshToken": "refresh-token-here",
    "user": {
      "id": "user-uuid",
      "email": "user@example.com",
      "firstName": "John",
      "lastName": "Doe",
      "role": "developer",
      "tenantId": "tenant-uuid"
    }
  }
}
```

---

### 3. Refresh Token
**POST** `/refresh`

**Description:** Refresh expired JWT token.

**Request Body:**
```json
{
  "refreshToken": "refresh-token-here"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "token": "new-jwt-token",
    "refreshToken": "new-refresh-token"
  }
}
```

---

### 4. Logout
**POST** `/logout`

**Description:** Invalidate user session.

**Headers:**
```
Authorization: Bearer <token>
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

---

### 5. Forgot Password
**POST** `/forgot-password`

**Description:** Request password reset email.

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Password reset email sent"
}
```

---

### 6. Reset Password
**POST** `/reset-password`

**Description:** Reset password using token from email.

**Request Body:**
```json
{
  "token": "reset-token-from-email",
  "newPassword": "NewSecurePass123!"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Password reset successfully"
}
```

---

### 7. Verify Email
**GET** `/verify-email?token=<token>`

**Description:** Verify user email address.

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Email verified successfully"
}
```

---

### 8. Get Current User
**GET** `/me`

**Description:** Get authenticated user profile.

**Headers:**
```
Authorization: Bearer <token>
```

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "id": "user-uuid",
    "email": "user@example.com",
    "firstName": "John",
    "lastName": "Doe",
    "role": "developer",
    "tenantId": "tenant-uuid",
    "avatar": "https://example.com/avatar.jpg",
    "createdAt": "2024-01-15T10:30:00Z"
  }
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "success": false,
  "message": "Validation error",
  "errors": {
    "email": ["Invalid email format"],
    "password": ["Password must be at least 8 characters"]
  }
}
```

### 401 Unauthorized
```json
{
  "success": false,
  "message": "Invalid credentials"
}
```

### 409 Conflict
```json
{
  "success": false,
  "message": "Email already registered"
}
```

---

## Notes
- All passwords are hashed using bcrypt
- JWT tokens expire in 24 hours
- Refresh tokens expire in 30 days
- Rate limiting: 5 login attempts per 15 minutes
