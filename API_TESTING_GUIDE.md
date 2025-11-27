# API Testing Guide

## Quick Start

### 1. Start the API Server

```bash
cd D:\Research\AjileMindApi
uvicorn main:app --reload
```

Server will run at: `http://localhost:8000`

### 2. Test Registration

#### Register SLIIT Company

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"company_name\": \"SLIIT\", \"email\": \"admin@my.sliit.lk\", \"password\": \"SecurePass123!\", \"password_confirmation\": \"SecurePass123!\"}"
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Tenant registered successfully",
  "data": {
    "tenant_id": "tenant_sliit_abc123",
    "tenant_name": "sliit",
    "company_name": "SLIIT",
    "user": {
      "user_id": "usr-...",
      "email": "admin@my.sliit.lk",
      "role": "SUPER_ADMIN"
    },
    "tokens": {
      "access_token": "eyJhbGc...",
      "refresh_token": "eyJhbGc...",
      "token_type": "Bearer",
      "expires_in": 3600
    }
  }
}
```

**Database Check:**
```sql
-- Check table created
SHOW TABLES LIKE 'tenant_sliit_users';

-- View user
SELECT * FROM tenant_sliit_users;
```

#### Register Another Company

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"company_name\": \"Axiata Digital Labs\", \"email\": \"admin@axixtadigitalalabs.com\", \"password\": \"SecurePass123!\", \"password_confirmation\": \"SecurePass123!\"}"
```

**Database Check:**
```sql
SHOW TABLES LIKE 'tenant_%_users';
-- Should show:
-- tenant_sliit_users
-- tenant_axixtadigitalalabs_users
```

### 3. Test Login

#### Login as SLIIT Admin

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"admin@my.sliit.lk\", \"password\": \"SecurePass123!\"}"
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "user": {
      "user_id": "usr-...",
      "email": "admin@my.sliit.lk",
      "role": "SUPER_ADMIN",
      "tenant_id": "tenant_sliit",
      "tenant_name": "sliit"
    },
    "tokens": {
      "access_token": "eyJhbGc...",
      "refresh_token": "eyJhbGc...",
      "token_type": "Bearer",
      "expires_in": 3600
    },
    "password_change_required": false
  }
}
```

**Save the access_token for next requests!**

### 4. Test Get Current User

```bash
# Replace YOUR_ACCESS_TOKEN with actual token from login
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Expected Response:**
```json
{
  "success": true,
  "message": "User retrieved successfully",
  "data": {
    "user_id": "usr-...",
    "email": "admin@my.sliit.lk",
    "tenant_id": "tenant_sliit",
    "tenant_name": "sliit",
    "role": "SUPER_ADMIN"
  }
}
```

### 5. Test Invite User

```bash
# Replace YOUR_ACCESS_TOKEN with actual token
curl -X POST http://localhost:8000/api/v1/auth/invite \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"first_name\": \"John\", \"last_name\": \"Doe\", \"email\": \"john@my.sliit.lk\", \"role\": \"DEVELOPER\"}"
```

**Expected Response:**
```json
{
  "success": true,
  "message": "User invited successfully",
  "data": {
    "user_id": "usr-...",
    "email": "john@my.sliit.lk",
    "role": "DEVELOPER",
    "temporary_password": "...",
    "welcome_email_sent": true
  }
}
```

**Database Check:**
```sql
SELECT * FROM tenant_sliit_users;
-- Should show both admin and john
```

### 6. Test Login as Invited User

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"john@my.sliit.lk\", \"password\": \"TEMPORARY_PASSWORD_FROM_INVITE\"}"
```

### 7. Test Change Password

```bash
# Replace YOUR_ACCESS_TOKEN with john's token
curl -X POST http://localhost:8000/api/v1/auth/change-password \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"current_password\": \"TEMPORARY_PASSWORD\", \"new_password\": \"MyNewPass123!\", \"new_password_confirmation\": \"MyNewPass123!\"}"
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Password changed successfully",
  "data": {
    "password_change_required": false
  }
}
```

## Using Postman

### Setup

1. **Create Collection**: "Multi-Tenant API"
2. **Set Variables**:
   - `base_url`: `http://localhost:8000`
   - `access_token`: (will be set after login)

### Requests

#### 1. Register Tenant

```
POST {{base_url}}/api/v1/auth/register
Content-Type: application/json

{
  "company_name": "Test Company",
  "email": "admin@testcompany.com",
  "password": "SecurePass123!",
  "password_confirmation": "SecurePass123!"
}
```

**Tests Script:**
```javascript
if (pm.response.code === 201) {
    const response = pm.response.json();
    pm.environment.set("access_token", response.data.tokens.access_token);
    pm.environment.set("tenant_name", response.data.tenant_name);
}
```

#### 2. Login

```
POST {{base_url}}/api/v1/auth/login
Content-Type: application/json

{
  "email": "admin@testcompany.com",
  "password": "SecurePass123!"
}
```

**Tests Script:**
```javascript
if (pm.response.code === 200) {
    const response = pm.response.json();
    pm.environment.set("access_token", response.data.tokens.access_token);
}
```

#### 3. Get Current User

```
GET {{base_url}}/api/v1/auth/me
Authorization: Bearer {{access_token}}
```

#### 4. Invite User

```
POST {{base_url}}/api/v1/auth/invite
Authorization: Bearer {{access_token}}
Content-Type: application/json

{
  "first_name": "Jane",
  "last_name": "Smith",
  "email": "jane@testcompany.com",
  "role": "DEVELOPER"
}
```

## Database Verification

### View All Tenant Tables

```sql
SHOW TABLES LIKE 'tenant_%_users';
```

### View Specific Tenant Users

```sql
-- SLIIT users
SELECT 
    user_id,
    email,
    role,
    JSON_EXTRACT(user_data, '$.first_name') as first_name,
    JSON_EXTRACT(user_data, '$.last_name') as last_name,
    status,
    created_at
FROM tenant_sliit_users;
```

### Count Users Per Tenant

```sql
-- For SLIIT
SELECT COUNT(*) as user_count FROM tenant_sliit_users;

-- For Axiata
SELECT COUNT(*) as user_count FROM tenant_axixtadigitalalabs_users;
```

### View User Details with JSON

```sql
SELECT 
    email,
    role,
    user_data,
    JSON_EXTRACT(user_data, '$.first_name') as first_name,
    JSON_EXTRACT(user_data, '$.last_name') as last_name,
    JSON_EXTRACT(user_data, '$.phone') as phone,
    created_at
FROM tenant_sliit_users
WHERE email = 'admin@my.sliit.lk';
```

## Testing Scenarios

### Scenario 1: Multi-Company Registration

```bash
# Company 1: SLIIT
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"company_name\": \"SLIIT\", \"email\": \"admin@my.sliit.lk\", \"password\": \"Pass123!\", \"password_confirmation\": \"Pass123!\"}"

# Company 2: Axiata
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"company_name\": \"Axiata\", \"email\": \"admin@axixtadigitalalabs.com\", \"password\": \"Pass123!\", \"password_confirmation\": \"Pass123!\"}"

# Company 3: Test Corp
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"company_name\": \"TestCorp\", \"email\": \"admin@testcorp.com\", \"password\": \"Pass123!\", \"password_confirmation\": \"Pass123!\"}"
```

**Database Check:**
```sql
SHOW TABLES LIKE 'tenant_%_users';
-- Should show 3 tables
```

### Scenario 2: Tenant Isolation Test

1. Register as SLIIT admin
2. Login as SLIIT admin (get token A)
3. Register as Axiata admin
4. Login as Axiata admin (get token B)
5. Try to access SLIIT data with Axiata token (should fail)

### Scenario 3: User Workflow

1. **Admin registers company**
2. **Admin logs in** (gets access token)
3. **Admin invites team member**
4. **Team member logs in** with temporary password
5. **Team member changes password**
6. **Team member performs work**

## Expected Database State

After testing, you should see:

```sql
mysql> SHOW TABLES LIKE 'tenant_%_users';
+---------------------------------------+
| Tables_in_database (tenant_%_users)   |
+---------------------------------------+
| tenant_sliit_users                    |
| tenant_axixtadigitalalabs_users       |
| tenant_testcorp_users                 |
+---------------------------------------+
```

Each table should have the structure:
```sql
mysql> DESCRIBE tenant_sliit_users;
+---------------------------+--------------------------------------------------+
| Field                     | Type                                             |
+---------------------------+--------------------------------------------------+
| id                        | int(11)                                          |
| user_id                   | varchar(50)                                      |
| email                     | varchar(255)                                     |
| password_hash             | varchar(255)                                     |
| role                      | varchar(50)                                      |
| user_data                 | json                                             |
| status                    | enum('ACTIVE','SUSPENDED','PENDING_ACTIVATION')  |
| password_change_required  | tinyint(1)                                       |
| last_login_at             | datetime                                         |
| created_at                | datetime                                         |
| updated_at                | datetime                                         |
+---------------------------+--------------------------------------------------+
```

## Troubleshooting

### Issue: 401 Unauthorized

**Cause:** Token expired or invalid

**Fix:** Login again to get new token

### Issue: 409 Conflict - Email already exists

**Cause:** User with same email already registered in that tenant

**Fix:** Use different email or delete existing user

### Issue: Table not found

**Cause:** Company not registered yet

**Fix:** Register company first through `/register` endpoint

### Issue: Invalid domain extraction

**Cause:** Unusual email format

**Fix:** Check email format, domain should be extractable

## Summary

✅ **Implemented Features:**
- Registration creates tenant-specific tables
- Login queries correct tenant table based on email domain
- JWT includes tenant_id and tenant_name
- Invite users to tenant tables
- Password management per tenant
- User data stored in JSON field

🎯 **Testing Complete When:**
- Multiple companies registered (3+ tables)
- Users can login to their respective tenants
- Cross-tenant isolation verified
- JWT tokens contain tenant_name
- Database shows tenant-specific tables
