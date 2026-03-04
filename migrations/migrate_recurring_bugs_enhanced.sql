-- Migration: Enhanced recurring_bugs table for better bug detection
-- This migration drops and recreates the recurring_bugs table with enhanced structure

-- First, backup existing data if needed (optional)
-- CREATE TABLE recurring_bugs_backup AS SELECT * FROM recurring_bugs;

-- Drop existing table
DROP TABLE IF EXISTS recurring_bugs;

-- Create enhanced recurring_bugs table
CREATE TABLE IF NOT EXISTS recurring_bugs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id BIGINT NOT NULL COMMENT 'Project this bug belongs to',
    
    -- Bug identification
    bug_hash VARCHAR(64) NOT NULL COMMENT 'Hash of bug description for deduplication',
    bug_description VARCHAR(1000) NOT NULL,
    bug_category ENUM('performance', 'ui', 'api', 'database', 'integration', 'security', 'other') DEFAULT 'other',
    
    -- Recurrence tracking
    first_reported_date DATE NOT NULL,
    last_reported_date DATE NOT NULL,
    mention_count INT DEFAULT 1 COMMENT 'Number of times mentioned across meetings',
    
    -- Source tracking (JSON array of sources)
    sources JSON NOT NULL COMMENT '[{report_id, transcript_id, meeting_date, source_type}]',
    
    -- Severity assessment
    severity ENUM('low', 'medium', 'high', 'critical') DEFAULT 'medium',
    impact_description TEXT COMMENT 'Business impact of this recurring issue',
    
    -- Resolution tracking
    status ENUM('open', 'investigating', 'resolved', 'dismissed', 'wont_fix') DEFAULT 'open',
    resolution_notes TEXT,
    resolved_date DATE,
    resolved_by VARCHAR(255),
    
    -- Link to backlog if a ticket is created
    backlog_item_id VARCHAR(128) COMMENT 'Reference to project_backlog if ticket created',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_project_id (project_id),
    INDEX idx_bug_hash (bug_hash),
    INDEX idx_status (status),
    INDEX idx_severity (severity),
    INDEX idx_mention_count (mention_count),
    INDEX idx_last_reported (last_reported_date),
    INDEX idx_bug_category (bug_category),
    
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Recurring bugs detected across multiple meetings';
