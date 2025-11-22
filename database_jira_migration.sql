-- ============================================
-- Jira Integration Table
-- ============================================
-- Run this SQL to add Jira integration support

USE agilemind_db;

CREATE TABLE IF NOT EXISTS jira_integrations (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Auto-increment ID',
    tenant_id VARCHAR(50) NOT NULL COMMENT 'Tenant this integration belongs to',
    jira_url VARCHAR(255) NOT NULL COMMENT 'Jira Cloud URL (e.g., https://company.atlassian.net)',
    email VARCHAR(255) NOT NULL COMMENT 'Jira account email',
    api_token VARCHAR(500) NOT NULL COMMENT 'Jira API token (encrypted)',
    is_active BOOLEAN DEFAULT TRUE COMMENT 'Whether integration is active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    UNIQUE KEY unique_tenant_jira (tenant_id),
    INDEX idx_tenant (tenant_id),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Jira Cloud integration credentials';

-- ============================================
-- Jira Issue Sync Table (Optional - for tracking synced issues)
-- ============================================
CREATE TABLE IF NOT EXISTS jira_issue_sync (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Auto-increment ID',
    tenant_id VARCHAR(50) NOT NULL COMMENT 'Tenant ID',
    task_id VARCHAR(50) NULL COMMENT 'Internal task ID (if linked)',
    jira_issue_key VARCHAR(50) NOT NULL COMMENT 'Jira issue key (e.g., PROJ-123)',
    jira_issue_id VARCHAR(50) NOT NULL COMMENT 'Jira issue ID',
    project_key VARCHAR(50) NOT NULL COMMENT 'Jira project key',
    summary TEXT COMMENT 'Issue summary',
    status VARCHAR(50) COMMENT 'Issue status',
    issue_type VARCHAR(50) COMMENT 'Issue type (Task, Story, Bug, etc.)',
    last_synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last sync timestamp',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp',
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    UNIQUE KEY unique_jira_issue (tenant_id, jira_issue_key),
    INDEX idx_tenant (tenant_id),
    INDEX idx_task (task_id),
    INDEX idx_jira_key (jira_issue_key),
    INDEX idx_project (project_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Jira issue synchronization tracking';

-- ============================================
-- Verification
-- ============================================
SELECT 
    TABLE_NAME,
    TABLE_ROWS,
    CREATE_TIME,
    TABLE_COMMENT
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'agilemind_db'
    AND TABLE_NAME IN ('jira_integrations', 'jira_issue_sync')
ORDER BY TABLE_NAME;

SELECT 'Jira integration tables created successfully!' as message;
