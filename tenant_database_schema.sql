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

    -- Project Management Metadata
    `sprint_size` INT NULL COMMENT 'Sprint duration in weeks (typically 1-4)',
    `next_sprint_start_date` DATE NULL COMMENT 'Next sprint start date',
    `project_lead` VARCHAR(255) NULL COMMENT 'Project lead name or email',
    `project_manager` JSON DEFAULT NULL COMMENT 'Project manager email',

    -- Architecture and Stack Information
    `architecture_type` ENUM(
        'Monolithic', 'Microservices', 'Serverless',
        'Event-Driven', 'Layered', 'Modular', 'Other'
    ) NULL COMMENT 'Project architecture pattern',

    `stack_type` ENUM('Frontend', 'Backend', 'Fullstack') NULL COMMENT 'Application stack type',
    
    -- Technology Stack
    `frontend_technologies` JSON NULL COMMENT 'Frontend technologies (e.g., ["React","TypeScript"])',
    `backend_technologies` JSON NULL COMMENT 'Backend technologies (e.g., ["Node.js","Spring Boot"])',
    
    -- Infrastructure
    `cloud_host` VARCHAR(100) NULL COMMENT 'Cloud hosting provider',
    `budget` DECIMAL(12,2) NULL COMMENT 'Project budget',

    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    -- Unique constraints
    UNIQUE KEY `unique_project_key` (`key`),
    UNIQUE KEY `unique_project_name` (`project_name`),

    -- Indexes
    INDEX `idx_project_name` (`project_name`),
    INDEX `idx_project_key` (`key`),
    INDEX `idx_start_date` (`start_date`),
    INDEX `idx_end_date` (`end_date`),
    INDEX `idx_next_sprint_start_date` (`next_sprint_start_date`),
    INDEX `idx_project_lead` (`project_lead`),
    INDEX `idx_architecture_type` (`architecture_type`),
    INDEX `idx_stack_type` (`stack_type`),
    INDEX `idx_cloud_host` (`cloud_host`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Project records and timelines';

-- ============================================
-- DATABASE TRIGGER
-- ============================================
-- Automatically sets next_sprint_start_date to start_date on insert
CREATE TRIGGER IF NOT EXISTS trg_projects_before_insert
BEFORE INSERT ON projects
FOR EACH ROW
SET NEW.next_sprint_start_date = NEW.start_date;


-- ============================================ project_backlog TABLE
-- Stores backlog items for projects

  CREATE TABLE `project_backlog` (
  `id` VARCHAR(128) COLLATE utf8mb4_unicode_ci NOT NULL
    COMMENT 'Backlog unique ID created by jira',

  `project_id` BIGINT NOT NULL
    COMMENT 'Project ID this backlog item belongs to',

  `summary` VARCHAR(255) COLLATE utf8mb4_unicode_ci NOT NULL
    COMMENT 'Backlog item name / summary',

  `description` TEXT COLLATE utf8mb4_unicode_ci
    COMMENT 'Detailed description of the backlog item',

  `issue_type` VARCHAR(100) COLLATE utf8mb4_unicode_ci NOT NULL
    COMMENT 'Type: story, feature, change, bug',

  `status` VARCHAR(100) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'todo'
    COMMENT 'Current status: todo, in_progress, done',

  `priority` VARCHAR(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL
    COMMENT 'Priority: high, medium, low',

  `severity` VARCHAR(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL
    COMMENT 'Severity level if applicable',

  `assignee` VARCHAR(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL
    COMMENT 'Assigned user/person',

  `tags` JSON DEFAULT NULL
    COMMENT 'Tags associated with the backlog item',

  `estimated_hours` INT DEFAULT 0
    COMMENT 'Estimated effort in hours',

  `logged_hours` INT DEFAULT 0
    COMMENT 'Actual logged hours',

  `story_points` INT DEFAULT 0
    COMMENT 'Story point estimation',

  `sprint_id` INT DEFAULT NULL
    COMMENT 'Sprint ID if assigned to a sprint',

  `parent_task_id` VARCHAR(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Parent task ID for subtasks (supports Jira keys like TAM-48)',

  `start_date` DATE DEFAULT NULL
    COMMENT 'Planned start date',

  `actual_start_date` DATE DEFAULT NULL
    COMMENT 'Actual start date',

  `end_date` DATE DEFAULT NULL
    COMMENT 'Planned end date',

  `actual_end_date` DATE DEFAULT NULL
    COMMENT 'Actual end date',

  `is_jira` TINYINT(1) NOT NULL DEFAULT 1
    COMMENT 'Is this backlog item created from Jira?',

  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    COMMENT 'Record creation time',

  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP
    COMMENT 'Last update time',

  PRIMARY KEY (`id`),

  KEY `idx_project_id` (`project_id`),
  KEY `idx_issue_type` (`issue_type`),
  KEY `idx_status` (`status`),
  KEY `idx_priority` (`priority`),
  KEY `idx_sprint_id` (`sprint_id`),
  KEY `idx_parent_task_id` (`parent_task_id`),

  CONSTRAINT `fk_backlog_project`
    FOREIGN KEY (`project_id`)
    REFERENCES `projects` (`project_id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE

) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_unicode_ci
COMMENT='Backlog items before project start and future changes/features';


-- ============================================ sprint TABLE
-- Stores sprint information for projects
CREATE TABLE IF NOT EXISTS `sprint` (
    `sprint_id` INT NOT NULL  
        COMMENT 'Unique sprint identifier',

    `project_id` BIGINT NOT NULL
        COMMENT 'Project this sprint belongs to',

    `sprint_name` VARCHAR(255) NOT NULL
        COMMENT 'Sprint name/identifier',

    `start_date` DATE NOT NULL
        COMMENT 'Sprint start date',

    `end_date` DATE NOT NULL
        COMMENT 'Sprint end date',

    `status` ENUM('PLANNED', 'ACTIVE', 'COMPLETED') DEFAULT 'PLANNED'
        COMMENT 'Sprint status',

    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        COMMENT 'Record creation time',

    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
        COMMENT 'Last update time',

    -- Indexes
    INDEX `idx_project_id` (`project_id`),
    INDEX `idx_status` (`status`),
    INDEX `idx_start_date` (`start_date`),
    INDEX `idx_end_date` (`end_date`),

    -- Primary Key
    PRIMARY KEY (`sprint_id`, `project_id`),

    -- Foreign Keys
    CONSTRAINT `fk_sprint_project`
        FOREIGN KEY (`project_id`)
        REFERENCES `projects` (`project_id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE

) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Sprint management for projects';


-- ============================================ project_backlog_priority TABLE
-- Stores priority ranking of backlog items
CREATE TABLE IF NOT EXISTS `project_backlog_priority` (
    `project_id` BIGINT NOT NULL
        COMMENT 'Project ID this backlog item belongs to',

    `backlog_id` VARCHAR(128) NOT NULL
        COMMENT 'Backlog item ID (from project_backlog)',

    `rank` INT NOT NULL
        COMMENT 'Priority rank (1 = highest priority)',
    `sprint_id` INT DEFAULT NULL
        COMMENT 'Sprint ID this backlog item belongs to',    

    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        COMMENT 'Record creation time',

    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
        COMMENT 'Last update time',

    -- Primary Key (Composite)
    PRIMARY KEY (`project_id`, `backlog_id`),

    -- Indexes
    INDEX `idx_project_rank` (`project_id`, `rank`),

    -- Foreign Keys
    CONSTRAINT `fk_priority_project`
        FOREIGN KEY (`project_id`)
        REFERENCES `projects` (`project_id`)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT `fk_priority_backlog`
        FOREIGN KEY (`backlog_id`)
        REFERENCES `project_backlog` (`id`)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT `fk_priority_sprint`
        FOREIGN KEY (`sprint_id`)
        REFERENCES `sprint` (`sprint_id`)
        ON UPDATE CASCADE
        ON DELETE CASCADE

) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Priority ranking of backlog items per project';


-- ============================================
-- NOTIFICATIONS TABLE
-- ============================================
-- Stores notifications for users
-- ============================================
CREATE TABLE IF NOT EXISTS `notifications` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT 'Notification ID',
    `header` VARCHAR(255) NOT NULL COMMENT 'Notification header/title',
    `description` TEXT NOT NULL COMMENT 'Notification description/message',
    `related_users` JSON NOT NULL COMMENT 'List of user emails who should see this notification',
    `is_read` BOOLEAN DEFAULT FALSE COMMENT 'Whether notification has been read',
    `notification_type` ENUM('INFO', 'WARNING', 'SUCCESS', 'ERROR') DEFAULT 'INFO' COMMENT 'Type of notification',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX `idx_created_at` (`created_at`),
    INDEX `idx_notification_type` (`notification_type`)
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci
  COMMENT='User notifications';



