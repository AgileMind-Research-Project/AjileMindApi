# Domain-Based Multi-Tenant Architecture

## Core Principle
**Table name = Domain extracted from email**
- NO tenant_id generation
- NO centralized tenants registry table
- Domain is the unique identifier

## Domain Extraction Examples

| Email | Domain Extracted | Table/DB Name |
|-------|------------------|---------------|
| `admin@sliit.lk` | `sliit` | `sliit` |
| `user@my.sliit.lk` | `sliit` | `sliit` |
| `lahiruk@visionexdigital.com.au` | `visionexdigital` | `visionexdigital` |
| `dev@mail.company.com` | `company` | `company` |
| `test@axixtadigitalalabs.com` | `axixtadigitalalabs` | `axixtadigitalalabs` |

### Domain Extraction Logic
1. Split email at `@`: `lahiruk@visionexdigital.com.au` → `visionexdigital.com.au`
2. Split domain by dots: `['visionexdigital', 'com', 'au']`
3. Remove TLDs (com, org, net, au, lk, uk, etc.)
4. Remove subdomains (my, mail, webmail, www, smtp)
5. Keep the main domain: `visionexdigital`
6. Sanitize (alphanumeric only): `visionexdigital`

## Registration Flow

### Step 1: Validate Email & Extract Domain
```python
Email: lahiruk@visionexdigital.com.au
↓
Domain: visionexdigital
```

### Step 2: Check for Duplicate Tenant
```sql
-- Prevent multiple registrations for same domain
SELECT COUNT(*) as count
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'visionexdigital';

-- If count > 0: Throw error "Tenant already exists"
```

### Step 3: Create Users Table in Centralized DB
```sql
-- Table name = domain
CREATE TABLE visionexdigital (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role VARCHAR(50) NOT NULL DEFAULT 'USER',
    status ENUM('ACTIVE', 'SUSPENDED', 'PENDING_ACTIVATION') DEFAULT 'PENDING_ACTIVATION',
    password_change_required BOOLEAN DEFAULT TRUE,
    last_login_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status)
);
```

### Step 4: Create Tenant Database
```sql
-- Database name = domain
CREATE DATABASE visionexdigital;

-- Create tenant_info table
CREATE TABLE visionexdigital.tenant_info (
    id INT AUTO_INCREMENT PRIMARY KEY,
    domain VARCHAR(100) UNIQUE NOT NULL,
    tenant_name VARCHAR(255) NOT NULL,
    tenant_email VARCHAR(255) NOT NULL,
    tenant_status ENUM('ACTIVE', 'SUSPENDED', 'INACTIVE') DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Insert tenant info
INSERT INTO visionexdigital.tenant_info (domain, tenant_name, tenant_email)
VALUES ('visionexdigital', 'Vision Ex Digital', 'lahiruk@visionexdigital.com.au');
```

### Step 5: Add User to Users Table
```sql
INSERT INTO visionexdigital (
    user_id, email, password_hash, 
    first_name, last_name, role, status, 
    password_change_required
)
VALUES (
    'usr-1234567890abcdef', 
    'lahiruk@visionexdigital.com.au', 
    '$2b$12$...',
    'Lahiru', 'K', 'SUPER_ADMIN', 'ACTIVE', FALSE
);
```

## Login Flow

### Step 1: Extract Domain
```python
Email: lahiruk@visionexdigital.com.au
↓
Domain: visionexdigital
```

### Step 2: Check if Table Exists
```sql
SELECT COUNT(*) as count
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'visionexdigital';

-- If count = 0: Invalid credentials
```

### Step 3: Query User
```sql
SELECT * FROM visionexdigital WHERE email = 'lahiruk@visionexdigital.com.au';
```

### Step 4: Verify & Generate Token
```python
# Verify password
verify_password(input_password, user.password_hash)

# Generate JWT
{
    "sub": "usr-1234567890abcdef",
    "email": "lahiruk@visionexdigital.com.au",
    "tenant_name": "visionexdigital",
    "role": "SUPER_ADMIN"
}
```

## Database Structure

### Centralized DB (`agilemind_db`)
```
agilemind_db/
├── sliit (table)                    ← SLIIT users
│   ├── usr-001 (admin@sliit.lk)
│   └── usr-002 (dev@sliit.lk)
├── visionexdigital (table)          ← Vision Ex Digital users
│   └── usr-003 (lahiruk@visionexdigital.com.au)
└── axixtadigitalalabs (table)       ← Axixta Digital Labs users
    └── usr-004 (admin@axixtadigitalalabs.com)
```

### Tenant Databases
```
Database: sliit/
└── tenant_info
    └── domain: sliit, tenant_name: SLIIT

Database: visionexdigital/
└── tenant_info
    └── domain: visionexdigital, tenant_name: Vision Ex Digital

Database: axixtadigitalalabs/
└── tenant_info
    └── domain: axixtadigitalalabs, tenant_name: Axixta Digital Labs
```

## Duplicate Prevention

### Scenario: Second Registration Attempt
```
First: admin@visionexdigital.com.au → Creates visionexdigital table
Second: lahiru@visionexdigital.com.au → REJECTED

Error: "A tenant for domain 'visionexdigital' already exists. Please contact your administrator."
```

### Solution for Existing Tenants
If table exists, users should:
1. Contact their company administrator
2. Get invited to existing tenant
3. Use "Forgot Password" if they already have an account

## Benefits

1. **Simplicity** - Domain is the identifier, no extra IDs
2. **Duplicate Prevention** - Automatic via table existence check
3. **Self-Contained** - No dependency on registry tables
4. **Human-Readable** - Table name = company domain
5. **Scalable** - Easy to discover tenants via information_schema
6. **Fast** - Direct table lookup by domain

## JWT Token Structure

```json
{
  "sub": "usr-1234567890abcdef",
  "email": "lahiruk@visionexdigital.com.au",
  "tenant_name": "visionexdigital",
  "role": "SUPER_ADMIN",
  "exp": 1234567890
}
```

## Complex Domain Examples

### Multi-Level TLDs
```
lahiruk@visionexdigital.com.au
→ Parts: ['visionexdigital', 'com', 'au']
→ Remove TLDs: com, au
→ Result: visionexdigital
```

### Subdomains
```
admin@my.sliit.lk
→ Parts: ['my', 'sliit', 'lk']
→ Remove subdomain: my
→ Remove TLD: lk
→ Result: sliit
```

### Company Email Servers
```
user@mail.company.com
→ Parts: ['mail', 'company', 'com']
→ Remove subdomain: mail
→ Remove TLD: com
→ Result: company
```

## API Responses

### Registration Success
```json
{
  "tenant_name": "visionexdigital",
  "company_name": "Vision Ex Digital",
  "user": {
    "user_id": "usr-1234567890abcdef",
    "email": "lahiruk@visionexdigital.com.au",
    "first_name": null,
    "last_name": null,
    "role": "SUPER_ADMIN"
  },
  "tokens": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "Bearer"
  },
  "redirect_url": "http://localhost:3000/dashboard"
}
```

### Registration Error (Duplicate)
```json
{
  "detail": "A tenant for domain 'visionexdigital' already exists. Please contact your administrator."
}
```
HTTP Status: 409 Conflict

### Login Success
```json
{
  "user": {
    "user_id": "usr-1234567890abcdef",
    "email": "lahiruk@visionexdigital.com.au",
    "first_name": "Lahiru",
    "last_name": "K",
    "role": "SUPER_ADMIN",
    "tenant_name": "visionexdigital"
  },
  "tokens": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "Bearer"
  },
  "password_change_required": false
}
```

## Verification Queries

### Check All Tenants
```sql
-- List all tenant tables
SELECT TABLE_NAME 
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'agilemind_db' 
AND TABLE_TYPE = 'BASE TABLE'
AND TABLE_NAME NOT IN ('roles', 'password_reset_tokens', 'audit_logs');
```

### Check Specific Tenant
```sql
-- Check if visionexdigital tenant exists
SELECT COUNT(*) FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'agilemind_db' 
AND TABLE_NAME = 'visionexdigital';

-- View visionexdigital users
SELECT * FROM agilemind_db.visionexdigital;

-- View visionexdigital tenant info
SELECT * FROM visionexdigital.tenant_info;
```

### Check User Count Per Tenant
```sql
-- Get user count for each tenant
SELECT 
    TABLE_NAME as tenant_domain,
    TABLE_ROWS as user_count
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'agilemind_db' 
AND TABLE_TYPE = 'BASE TABLE'
AND TABLE_NAME NOT IN ('roles', 'password_reset_tokens', 'audit_logs')
ORDER BY TABLE_NAME;
```

## Implementation Files

- `app/services/auth_service.py` - Registration & login with duplicate check
- `app/db/repositories/tenant_user_repository.py` - Database operations
- `app/utils/domain_extractor.py` - Domain extraction logic
- `DOMAIN_BASED_ARCHITECTURE.md` - This documentation
