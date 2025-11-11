-- ============================================
-- AgileMind Database Schema
-- Multi-Tenant SaaS Platform
-- ============================================

-- Create database
CREATE DATABASE IF NOT EXISTS agile_mind_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE agile_mind_db;

-- ============================================
-- 1. TENANTS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS tenants (
    tenant_id VARCHAR(50) PRIMARY KEY COMMENT 'Unique tenant identifier',
    company_name VARCHAR(100) NOT NULL COMMENT 'Company/organization name',
    status ENUM('ACTIVE', 'SUSPENDED', 'TRIAL') DEFAULT 'ACTIVE' COMMENT 'Tenant account status',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Tenant organizations';

-- ============================================
-- 2. USERS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(50) PRIMARY KEY COMMENT 'Unique user identifier',
    tenant_id VARCHAR(50) NOT NULL COMMENT 'Tenant this user belongs to',
    email VARCHAR(255) NOT NULL COMMENT 'User email address',
    password_hash VARCHAR(255) NOT NULL COMMENT 'Bcrypt hashed password',
    first_name VARCHAR(100) COMMENT 'User first name',
    last_name VARCHAR(100) COMMENT 'User last name',
    role VARCHAR(50) NOT NULL COMMENT 'User role (SUPER_ADMIN, DEVELOPER, etc.)',
    status ENUM('PENDING_ACTIVATION', 'ACTIVE', 'SUSPENDED') DEFAULT 'PENDING_ACTIVATION' COMMENT 'User account status',
    password_change_required BOOLEAN DEFAULT FALSE COMMENT 'Force password change on next login',
    last_login_at TIMESTAMP NULL COMMENT 'Last successful login timestamp',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    UNIQUE KEY unique_email_per_tenant (tenant_id, email),
    INDEX idx_email (email),
    INDEX idx_tenant (tenant_id),
    INDEX idx_status (status),
    INDEX idx_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='System users with multi-tenant isolation';

-- ============================================
-- 3. PASSWORD RESET TOKENS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    token_id VARCHAR(50) PRIMARY KEY COMMENT 'Unique token identifier',
    user_id VARCHAR(50) NOT NULL COMMENT 'User requesting password reset',
    token VARCHAR(255) NOT NULL UNIQUE COMMENT 'Secure reset token',
    expires_at TIMESTAMP NOT NULL COMMENT 'Token expiration timestamp',
    used BOOLEAN DEFAULT FALSE COMMENT 'Whether token has been used',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp',
    
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_token (token),
    INDEX idx_expires (expires_at),
    INDEX idx_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Password reset tokens with expiration';

-- ============================================
-- 4. AUDIT LOGS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id VARCHAR(50) PRIMARY KEY COMMENT 'Unique log identifier',
    tenant_id VARCHAR(50) NOT NULL COMMENT 'Tenant context',
    user_id VARCHAR(50) COMMENT 'User who performed action',
    event_type VARCHAR(100) NOT NULL COMMENT 'Type of event (login, password_change, etc.)',
    event_data JSON COMMENT 'Additional event metadata',
    ip_address VARCHAR(45) COMMENT 'IP address of user',
    user_agent TEXT COMMENT 'Browser user agent string',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Event timestamp',
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL,
    INDEX idx_tenant (tenant_id),
    INDEX idx_user (user_id),
    INDEX idx_event_type (event_type),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Audit trail for security and compliance';

-- ============================================
-- 5. ROLES TABLE (Optional - for custom roles)
-- ============================================
CREATE TABLE IF NOT EXISTS roles (
    role_id VARCHAR(50) PRIMARY KEY COMMENT 'Unique role identifier',
    tenant_id VARCHAR(50) COMMENT 'Tenant (NULL for system roles)',
    name VARCHAR(50) NOT NULL COMMENT 'Role name (UPPERCASE_SNAKE_CASE)',
    display_name VARCHAR(100) NOT NULL COMMENT 'Human-readable role name',
    description TEXT COMMENT 'Role description',
    permissions JSON COMMENT 'Array of permission strings',
    is_system_role BOOLEAN DEFAULT FALSE COMMENT 'Whether this is a system default role',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    UNIQUE KEY unique_role_per_tenant (tenant_id, name),
    INDEX idx_tenant (tenant_id),
    INDEX idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='User roles and permissions';

-- ============================================
-- INSERT DEFAULT SYSTEM ROLES
-- ============================================
INSERT INTO roles (role_id, tenant_id, name, display_name, description, permissions, is_system_role)
VALUES
    ('role-super-admin', NULL, 'SUPER_ADMIN', 'Super Administrator', 'Full system access with all permissions', JSON_ARRAY('*'), TRUE),
    ('role-admin', NULL, 'ADMIN', 'Administrator', 'Tenant administration and user management', JSON_ARRAY('users.*', 'roles.*', 'settings.*'), TRUE),
    ('role-project-manager', NULL, 'PROJECT_MANAGER', 'Project Manager', 'Manage projects, sprints, and teams', JSON_ARRAY('sprints.*', 'tasks.*', 'meetings.read', 'users.read'), TRUE),
    ('role-scrum-master', NULL, 'SCRUM_MASTER', 'Scrum Master', 'Facilitate Scrum ceremonies and meetings', JSON_ARRAY('sprints.read', 'tasks.read', 'meetings.*', 'retrospectives.*'), TRUE),
    ('role-developer', NULL, 'DEVELOPER', 'Developer', 'Work on tasks and participate in sprints', JSON_ARRAY('sprints.read', 'tasks.*', 'meetings.read'), TRUE),
    ('role-viewer', NULL, 'VIEWER', 'Viewer', 'Read-only access to view content', JSON_ARRAY('*.read'), TRUE)
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

-- ============================================
-- SAMPLE DATA FOR TESTING (Optional)
-- ============================================

-- Insert sample tenant
INSERT INTO tenants (tenant_id, company_name, status) 
VALUES ('tn-sample-001', 'Sample Company', 'ACTIVE')
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

-- Insert sample super admin user
-- Password: Admin123! (hashed)
INSERT INTO users (
    user_id, tenant_id, email, password_hash, first_name, last_name, 
    role, status, password_change_required
) VALUES (
    'usr-sample-001', 
    'tn-sample-001', 
    'admin@sample.com', 
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU7xqC8GBHOS', -- Admin123!
    'Admin', 
    'User',
    'SUPER_ADMIN', 
    'ACTIVE', 
    FALSE
)
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

-- ============================================
-- VIEWS FOR COMMON QUERIES
-- ============================================

-- Active users per tenant
CREATE OR REPLACE VIEW v_active_users AS
SELECT 
    t.tenant_id,
    t.company_name,
    COUNT(u.user_id) as active_user_count
FROM tenants t
LEFT JOIN users u ON t.tenant_id = u.tenant_id AND u.status = 'ACTIVE'
GROUP BY t.tenant_id, t.company_name;

-- Recent login activity
CREATE OR REPLACE VIEW v_recent_logins AS
SELECT 
    u.user_id,
    u.email,
    u.first_name,
    u.last_name,
    u.tenant_id,
    t.company_name,
    u.last_login_at,
    TIMESTAMPDIFF(MINUTE, u.last_login_at, NOW()) as minutes_since_login
FROM users u
JOIN tenants t ON u.tenant_id = t.tenant_id
WHERE u.last_login_at IS NOT NULL
ORDER BY u.last_login_at DESC;

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

-- Procedure to get user statistics
CREATE PROCEDURE sp_get_tenant_stats(IN p_tenant_id VARCHAR(50))
BEGIN
    SELECT 
        COUNT(*) as total_users,
        SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END) as active_users,
        SUM(CASE WHEN status = 'PENDING_ACTIVATION' THEN 1 ELSE 0 END) as pending_users,
        SUM(CASE WHEN status = 'SUSPENDED' THEN 1 ELSE 0 END) as suspended_users,
        SUM(CASE WHEN last_login_at > DATE_SUB(NOW(), INTERVAL 7 DAY) THEN 1 ELSE 0 END) as active_last_7_days
    FROM users
    WHERE tenant_id = p_tenant_id;
END //

DELIMITER ;

-- ============================================
-- SCHEDULED CLEANUP (Run daily)
-- ============================================
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
WHERE TABLE_SCHEMA = 'agile_mind_db'
ORDER BY TABLE_NAME;

-- Check if sample data was inserted
SELECT 'Tenants' as table_name, COUNT(*) as row_count FROM tenants
UNION ALL
SELECT 'Users', COUNT(*) FROM users
UNION ALL
SELECT 'Roles', COUNT(*) FROM roles;

-- ============================================
-- GRANTS (Adjust username/password as needed)
-- ============================================
-- CREATE USER IF NOT EXISTS 'agile_mind_user'@'%' IDENTIFIED BY 'your_password_here';
-- GRANT SELECT, INSERT, UPDATE, DELETE ON agile_mind_db.* TO 'agile_mind_user'@'%';
-- FLUSH PRIVILEGES;

-- ============================================
-- BACKUP RECOMMENDATION
-- ============================================
-- mysqldump -u root -p agile_mind_db > agile_mind_backup_$(date +%Y%m%d_%H%M%S).sql

-- ============================================
-- NOTES
-- ============================================
-- 1. Multi-tenant isolation: All queries must filter by tenant_id
-- 2. Password hashing: Use bcrypt with cost factor 12
-- 3. JWT tokens: 24h access token, 30d refresh token
-- 4. Audit logs: Log all authentication events
-- 5. Clean expired tokens regularly
-- 6. Backup database daily
-- 7. Monitor active user counts
-- 8. Review audit logs for security

-- ============================================
-- SUCCESS MESSAGE
-- ============================================
SELECT 'Database schema created successfully!' as message,
       DATABASE() as current_database,
       NOW() as created_at;
