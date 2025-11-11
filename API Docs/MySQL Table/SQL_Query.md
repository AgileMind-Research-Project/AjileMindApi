-- ============================================
-- AGILEMIND DATABASE SCHEMA
-- Direct execution in MySQL Workbench
-- ============================================

-- Create Database
-- CREATE DATABASE IF NOT EXISTS agile_mind_db
-- CHARACTER SET utf8mb4
-- COLLATE utf8mb4_unicode_ci;

-- USE agile_mind_db;

-- ============================================
-- AUTHENTICATION TABLES
-- ============================================

-- 1. Tenants Table
CREATE TABLE IF NOT EXISTS TENANTS (
    TENANT_ID VARCHAR(50) PRIMARY KEY COMMENT 'Unique tenant identifier',
    COMPANY_NAME VARCHAR(100) NOT NULL COMMENT 'Company/organization name',
    STATUS ENUM('ACTIVE', 'SUSPENDED', 'TRIAL') DEFAULT 'ACTIVE' COMMENT 'Tenant account status',
    AUDIT_LOGGING_ENABLED BOOLEAN DEFAULT TRUE COMMENT 'Enable audit logging',
    AUDIT_RETENTION_DAYS INT DEFAULT 90 COMMENT 'Audit log retention in days',
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp',
    UPDATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    
    INDEX IDX_STATUS (STATUS),
    INDEX IDX_CREATED_AT (CREATED_AT)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Tenant organizations';

-- 2. Users Table
CREATE TABLE IF NOT EXISTS USERS (
    USER_ID VARCHAR(50) PRIMARY KEY COMMENT 'Unique user identifier',
    TENANT_ID VARCHAR(50) NOT NULL COMMENT 'Tenant this user belongs to',
    EMAIL VARCHAR(255) NOT NULL COMMENT 'User email address',
    PASSWORD_HASH VARCHAR(255) NOT NULL COMMENT 'Bcrypt hashed password',
    FIRST_NAME VARCHAR(100) COMMENT 'User first name',
    LAST_NAME VARCHAR(100) COMMENT 'User last name',
    ROLE VARCHAR(50) NOT NULL COMMENT 'User role (SUPER_ADMIN, DEVELOPER, etc.)',
    STATUS ENUM('PENDING_ACTIVATION', 'ACTIVE', 'SUSPENDED') DEFAULT 'PENDING_ACTIVATION' COMMENT 'User account status',
    PASSWORD_CHANGE_REQUIRED BOOLEAN DEFAULT FALSE COMMENT 'Force password change on next login',
    LAST_LOGIN_AT TIMESTAMP NULL COMMENT 'Last successful login timestamp',
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp',
    UPDATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    
    FOREIGN KEY (TENANT_ID) REFERENCES TENANTS(TENANT_ID) ON DELETE CASCADE,
    UNIQUE KEY UNIQUE_EMAIL_PER_TENANT (TENANT_ID, EMAIL),
    INDEX IDX_EMAIL (EMAIL),
    INDEX IDX_TENANT (TENANT_ID),
    INDEX IDX_STATUS (STATUS),
    INDEX IDX_ROLE (ROLE)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='System users with multi-tenant isolation';

-- 3. Password Reset Tokens Table
CREATE TABLE IF NOT EXISTS PASSWORD_RESET_TOKENS (
    TOKEN_ID VARCHAR(50) PRIMARY KEY COMMENT 'Unique token identifier',
    USER_ID VARCHAR(50) NOT NULL COMMENT 'User requesting password reset',
    TOKEN VARCHAR(255) NOT NULL UNIQUE COMMENT 'Secure reset token',
    EXPIRES_AT TIMESTAMP NOT NULL COMMENT 'Token expiration timestamp',
    USED BOOLEAN DEFAULT FALSE COMMENT 'Whether token has been used',
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp',
    
    FOREIGN KEY (USER_ID) REFERENCES USERS(USER_ID) ON DELETE CASCADE,
    INDEX IDX_TOKEN (TOKEN),
    INDEX IDX_EXPIRES (EXPIRES_AT),
    INDEX IDX_USER (USER_ID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Password reset tokens with expiration';

-- 4. Audit Logs Table
CREATE TABLE IF NOT EXISTS AUDIT_LOGS (
    LOG_ID VARCHAR(50) PRIMARY KEY COMMENT 'Unique log identifier',
    TENANT_ID VARCHAR(50) NOT NULL COMMENT 'Tenant context',
    USER_ID VARCHAR(50) COMMENT 'User who performed action',
    EVENT_TYPE VARCHAR(100) NOT NULL COMMENT 'Type of event (login, password_change, etc.)',
    EVENT_DATA JSON COMMENT 'Additional event metadata',
    IP_ADDRESS VARCHAR(45) COMMENT 'IP address of user',
    USER_AGENT TEXT COMMENT 'Browser user agent string',
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Event timestamp',
    
    FOREIGN KEY (TENANT_ID) REFERENCES TENANTS(TENANT_ID) ON DELETE CASCADE,
    FOREIGN KEY (USER_ID) REFERENCES USERS(USER_ID) ON DELETE SET NULL,
    INDEX IDX_TENANT (TENANT_ID),
    INDEX IDX_USER (USER_ID),
    INDEX IDX_EVENT_TYPE (EVENT_TYPE),
    INDEX IDX_CREATED_AT (CREATED_AT)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Audit trail for security and compliance';

-- 5. Roles Table
CREATE TABLE IF NOT EXISTS ROLES (
    ROLE_ID VARCHAR(50) PRIMARY KEY COMMENT 'Unique role identifier',
    TENANT_ID VARCHAR(50) COMMENT 'Tenant (NULL for global roles)',
    NAME VARCHAR(100) NOT NULL COMMENT 'Role name',
    DESCRIPTION TEXT COMMENT 'Role description',
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (TENANT_ID) REFERENCES TENANTS(TENANT_ID) ON DELETE CASCADE,
    UNIQUE KEY UNIQUE_ROLE_PER_TENANT (TENANT_ID, NAME),
    INDEX IDX_TENANT (TENANT_ID),
    INDEX IDX_NAME (NAME)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Custom user roles';

-- ============================================
-- ADDITIONAL TABLES (Add as needed)
-- ============================================

-- Tenant Management Tables
-- User Management Tables
-- Sprint Management Tables
-- Task Management Tables
-- Meeting Management Tables
-- Retrospective Tables
-- Governance Tables
-- Integration Tables
-- AI/Analytics Tables
