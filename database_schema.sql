-- ============================================
-- AgileMind Database Schema
-- Domain-Based Multi-Tenant SaaS Platform
-- ============================================
-- 
-- ARCHITECTURE OVERVIEW:
-- - Each tenant (company) is identified by domain extracted from email
-- - User tables are created dynamically: {domain} table in centralized DB
-- - Each tenant gets its own database: {domain}_db for metadata
-- - NO centralized tenants or users table
-- - Table discovery via information_schema.TABLES
-- 
-- Example: lahiruk@visionexdigital.com.au
--   → Domain: visionexdigital
--   → Users table: visionexdigital (in agilemind_db)
--   → Metadata DB: visionexdigital_db
-- ============================================

-- Create centralized database
CREATE DATABASE IF NOT EXISTS agilemind_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE agilemind_db;

-- ============================================
-- 1. PASSWORD RESET TOKENS TABLE
-- ============================================
-- Shared table for password reset tokens across all tenants
-- Stores email to extract domain during password reset
-- ============================================
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    token_id VARCHAR(50) PRIMARY KEY COMMENT 'Unique token identifier',
    user_id VARCHAR(50) NOT NULL COMMENT 'User requesting password reset',
    email VARCHAR(255) NOT NULL COMMENT 'User email for domain extraction during reset',
    token VARCHAR(255) NOT NULL UNIQUE COMMENT 'Secure reset token',
    expires_at TIMESTAMP NOT NULL COMMENT 'Token expiration timestamp',
    used BOOLEAN DEFAULT FALSE COMMENT 'Whether token has been used',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp',
    
    INDEX idx_token (token),
    INDEX idx_expires (expires_at),
    INDEX idx_user (user_id),
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Password reset tokens (shared across tenants)';

-- ============================================
-- 2. ROLES TABLE
-- ============================================
-- Shared roles definitions across all tenants
-- Note: Role assignments are stored in tenant-specific user tables
-- ============================================
CREATE TABLE IF NOT EXISTS roles (
    role_id VARCHAR(50) PRIMARY KEY COMMENT 'Unique role identifier',
    name VARCHAR(50) NOT NULL UNIQUE COMMENT 'Role name (UPPERCASE_SNAKE_CASE)',
    display_name VARCHAR(100) NOT NULL COMMENT 'Human-readable role name',
    description TEXT COMMENT 'Role description',
    permissions JSON COMMENT 'Array of permission strings',
    is_system_role BOOLEAN DEFAULT TRUE COMMENT 'System default role',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Shared role definitions';

-- ============================================
-- INSERT DEFAULT SYSTEM ROLES
-- ============================================
INSERT INTO roles (role_id, name, display_name, description, permissions, is_system_role)
VALUES
    ('role-super-admin', 'SUPER_ADMIN', 'Super Administrator', 'Full system access with all permissions', JSON_ARRAY('*'), TRUE),
    ('role-admin', 'ADMIN', 'Administrator', 'Tenant administration and user management', JSON_ARRAY('users.*', 'roles.*', 'settings.*'), TRUE),
    ('role-project-manager', 'PROJECT_MANAGER', 'Project Manager', 'Manage projects, sprints, and teams', JSON_ARRAY('sprints.*', 'tasks.*', 'meetings.read', 'users.read'), TRUE),
    ('role-scrum-master', 'SCRUM_MASTER', 'Scrum Master', 'Facilitate Scrum ceremonies and meetings', JSON_ARRAY('sprints.read', 'tasks.read', 'meetings.*', 'retrospectives.*'), TRUE),
    ('role-developer', 'DEVELOPER', 'Developer', 'Work on tasks and participate in sprints', JSON_ARRAY('sprints.read', 'tasks.*', 'meetings.read'), TRUE),
    ('role-viewer', 'VIEWER', 'Viewer', 'Read-only access to view content', JSON_ARRAY('*.read'), TRUE)
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

-- ============================================
-- STORED PROCEDURES
-- ============================================
DELIMITER //

-- Procedure to clean expired reset tokens
CREATE PROCEDURE sp_clean_expired_tokens()
BEGIN
    DELETE FROM password_reset_tokens
    WHERE expires_at < NOW()
       OR (used = TRUE AND created_at < DATE_SUB(NOW(), INTERVAL 7 DAY));
    
    SELECT ROW_COUNT() as deleted_count;
END //

DELIMITER ;

-- ============================================
-- SCHEDULED CLEANUP (Optional - Run daily)
-- ============================================
-- Uncomment to enable automatic cleanup of expired tokens
-- CREATE EVENT IF NOT EXISTS evt_clean_expired_tokens
-- ON SCHEDULE EVERY 1 DAY
-- STARTS CURRENT_TIMESTAMP
-- DO CALL sp_clean_expired_tokens();

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- Check if all tables were created
SELECT 
    TABLE_NAME,
    TABLE_ROWS,
    CREATE_TIME,
    UPDATE_TIME,
    TABLE_COMMENT
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'agilemind_db'
ORDER BY TABLE_NAME;

-- Check system roles
SELECT 'Roles' as table_name, COUNT(*) as row_count FROM roles;

-- ============================================
-- NOTES
-- ============================================
-- 1. Domain-based isolation: Each tenant gets {domain} table and {domain}_db database
-- 2. Table discovery: Query information_schema.TABLES to find tenant tables
-- 3. Password hashing: Use bcrypt with cost factor 12
-- 4. JWT tokens: 24h access token, 7d refresh token (contains tenant_name)
-- 5. Duplicate prevention: Check table existence before registration
-- 6. Clean expired reset tokens regularly using sp_clean_expired_tokens
-- 7. Backup tenant databases individually
-- 8. Domain extraction: Remove subdomains (my, mail) and TLDs (.com, .au, etc.)

-- ============================================
-- DYNAMIC TABLE STRUCTURE (Created per tenant)
-- ============================================
-- Each tenant gets a table in centralized DB named: {domain}
-- Example: visionexdigital for lahiruk@visionexdigital.com.au
-- 
-- CREATE TABLE `{domain}` (
--     user_id VARCHAR(50) PRIMARY KEY,
--     email VARCHAR(255) NOT NULL UNIQUE,
--     password_hash VARCHAR(255) NOT NULL,
--     first_name VARCHAR(100),
--     last_name VARCHAR(100),
--     role VARCHAR(50) NOT NULL,
--     status ENUM('PENDING_ACTIVATION', 'ACTIVE', 'SUSPENDED') DEFAULT 'PENDING_ACTIVATION',
--     password_change_required BOOLEAN DEFAULT FALSE,
--     last_login_at TIMESTAMP NULL,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
--     INDEX idx_email (email),
--     INDEX idx_status (status)
-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
--
-- Each tenant also gets a separate database: {domain}_db
-- Contains tenant_info table with metadata

-- ============================================
-- SUCCESS MESSAGE
-- ============================================
SELECT 'Database schema created successfully!' as message,
       'Domain-based multi-tenant architecture' as architecture,
       DATABASE() as current_database,
       NOW() as created_at;
