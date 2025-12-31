-- ============================================
-- Tenant Database Schema
-- Domain-Based Multi-Tenant Architecture
-- ============================================
-- 
-- This schema is applied to EACH tenant's separate database
-- Database naming: {domain} (e.g., visionexdigital, sliit, company)
-- 
-- Tables created:
-- 1. tenant_info - Tenant metadata and configuration
-- 2. sprints - Sprint management
-- 3. tasks - Task/issue tracking
-- 4. meetings - Meeting records
-- 5. retrospectives - Retrospective data
-- ============================================

-- NOTE: Replace {TENANT_DB} with actual tenant database name
-- Example: visionexdigital, sliit, etc.

USE `{TENANT_DB}`;

-- ============================================
-- 1. TENANT_INFO TABLE
-- ============================================
-- Stores tenant configuration and metadata
-- ============================================
CREATE TABLE IF NOT EXISTS `tenant_info` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `domain` VARCHAR(100) UNIQUE NOT NULL COMMENT 'Tenant domain identifier',
    `tenant_name` VARCHAR(255) NOT NULL COMMENT 'Company/Organization name',
    `tenant_email` VARCHAR(255) NOT NULL COMMENT 'Primary contact email',
    `tenant_status` ENUM('ACTIVE', 'SUSPENDED', 'INACTIVE') DEFAULT 'ACTIVE' COMMENT 'Tenant account status',
    `subscription_plan` VARCHAR(50) DEFAULT 'FREE' COMMENT 'Subscription plan type',
    `max_users` INT DEFAULT 10 COMMENT 'Maximum allowed users',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX `idx_domain` (`domain`),
    INDEX `idx_status` (`tenant_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='Tenant configuration and metadata';

-- ============================================ jira_integrations TABLE
-- Stores Jira account integration details for the tenant

CREATE TABLE IF NOT EXISTS `jira_integrations` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `jira_url` VARCHAR(255) NOT NULL COMMENT 'Base URL of Jira instance',
    `email` VARCHAR(255) NOT NULL COMMENT 'Jira account email',
    `api_token` BOOLEAN DEFAULT FALSE COMMENT 'Whether token is validated and active',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY `uq_jira_account` (`jira_url`, `email`),
    INDEX `idx_jira_url` (`jira_url`),
    INDEX `idx_api_token` (`api_token`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='Jira account records and API token validation state';

-- ============================================ projects TABLE
-- Stores project details for the tenant
CREATE TABLE IF NOT EXISTS `projects` (
    `project_id` BIGINT NOT NULL PRIMARY KEY COMMENT 'Project ID provided by jira or system',

    `project_name` VARCHAR(255) NOT NULL COMMENT 'Name of the project',
    `key` VARCHAR(255) NOT NULL COMMENT 'Project key provided by system',
    `project_type` VARCHAR(100) NOT NULL COMMENT 'Type/category of the project',
    `start_date` DATE NOT NULL COMMENT 'Project start date',
    `end_date` DATE NOT NULL COMMENT 'Project end date',

    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP 
        ON UPDATE CURRENT_TIMESTAMP,

    -- Unique constraints
    UNIQUE KEY `unique_project_key` (`key`),
    UNIQUE KEY `unique_project_name` (`project_name`),

    -- Additional index for faster search on project_name
    INDEX `idx_project_name` (`project_name`),
    INDEX `idx_project_key` (`key`),
    INDEX `idx_start_date` (`start_date`),
    INDEX `idx_end_date` (`end_date`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Project records and timelines';

-- ============================================ project_backlog TABLE
-- Stores backlog items for projects

  CREATE TABLE IF NOT EXISTS `project_backlog` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY
        COMMENT 'Backlog unique ID created by system',

    `project_id` BIGINT NOT NULL
        COMMENT 'Project ID this backlog item belongs to',

    `summary` VARCHAR(255) NOT NULL
        COMMENT 'Backlog item name / summary',

    `description` TEXT NULL
        COMMENT 'Detailed description of the backlog item',

    `issue_type` VARCHAR(100) NOT NULL
        COMMENT 'Type: story, feature, change, bug',

    `status` VARCHAR(100) NOT NULL DEFAULT 'todo'
        COMMENT 'Current status: todo, in_progress, done',

    `priority` VARCHAR(100) NULL
        COMMENT 'Priority: high, medium, low',

    `assignee` VARCHAR(255) NULL
        COMMENT 'Assigned user/person',

    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        COMMENT 'Record creation time',

    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
        COMMENT 'Last update time',

    -- Indexes
    INDEX `idx_project_id` (`project_id`),
    INDEX `idx_issue_type` (`issue_type`),
    INDEX `idx_status` (`status`),
    INDEX `idx_priority` (`priority`),

    -- Foreign Key
    CONSTRAINT `fk_backlog_project`
        FOREIGN KEY (`project_id`)
        REFERENCES `projects` (`project_id`)
        ON UPDATE CASCADE
        ON DELETE CASCADE

) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Backlog items before project start and future changes/features';




