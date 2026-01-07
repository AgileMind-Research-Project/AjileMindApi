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
-- 2. jira_integrations - Jira account integration details
-- 3. projects - Project records and timelines
-- 4. project_backlog - Backlog items for projects
-- 5. sprint - Sprint management and tracking
-- 6. sprint_leave - Developer leave tracking within sprints
-- 7. task - Task and work item tracking
-- 8. tbl_blocker - Project blockers tracking
-- 9. tbl_risk_parameters_selection - Risk parameter configuration
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
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT 'Backlog unique ID created by system',

    `project_id` BIGINT NOT NULL COMMENT 'Project ID this backlog item belongs to',
    `name` VARCHAR(255) NOT NULL COMMENT 'Backlog item name / summary',
    `description` TEXT NULL COMMENT 'Detailed description of the backlog item',
    `issue_type` VARCHAR(100) NOT NULL COMMENT 'Type: story, feature, change, bug',
    `status` VARCHAR(100) NOT NULL DEFAULT 'todo' COMMENT 'Current status of the item',
    `priority` VARCHAR(100) NULL COMMENT 'Priority: high, medium, low',
    `assignee` VARCHAR(255) NULL COMMENT 'Assigned user/person',

    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP 
        ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update time',

    -- Indexes
    INDEX `idx_project_id` (`project_id`),
    INDEX `idx_issue_type` (`issue_type`),
    INDEX `idx_status` (`status`),
    INDEX `idx_priority` (`priority`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Backlog items gathered before project start and new changes/features added later';


-- ============================================ sprint TABLE
-- Stores sprint information for projects
CREATE TABLE IF NOT EXISTS `sprint` (
  `sprint_id` INT NOT NULL AUTO_INCREMENT,
  `project_id` BIGINT NOT NULL,
  `sprint_name` VARCHAR(255) NOT NULL,
  `sprint_goal` TEXT,
  `start_date` DATE NOT NULL,
  `end_date` DATE NOT NULL,
  `sprint_status` ENUM('Not Started','In Progress','Completed','Closed') DEFAULT 'Not Started',
  `total_estimated_hours` INT DEFAULT 0,
  `total_completed_hours` INT DEFAULT 0,
  `created_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`sprint_id`),
  INDEX `idx_sprint_project` (`project_id`),
  INDEX `idx_sprint_status` (`sprint_status`),
  INDEX `idx_sprint_dates` (`start_date`, `end_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='Sprint management and tracking';

-- ============================================ sprint_leave TABLE
-- Stores developer leave information during sprints
CREATE TABLE IF NOT EXISTS `sprint_leave` (
  `leave_id` INT NOT NULL AUTO_INCREMENT,
  `sprint_id` INT NOT NULL,
  `project_id` BIGINT NOT NULL,
  `developer_name` VARCHAR(255) NOT NULL,
  `leave_date` DATE NOT NULL,
  `leave_hours` INT NOT NULL CHECK (`leave_hours` >= 0),
  `reason` VARCHAR(500) DEFAULT NULL,
  `leave_type` ENUM('Full Day','Half Day','Short Leave') DEFAULT 'Full Day',
  `created_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`leave_id`),
  INDEX `idx_leave_sprint` (`sprint_id`),
  INDEX `idx_leave_project` (`project_id`),
  INDEX `idx_leave_date` (`leave_date`),
  INDEX `idx_developer_name` (`developer_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='Developer leave tracking within sprints';

-- ============================================ task TABLE
-- Stores tasks, bugs, stories, and other work items
CREATE TABLE IF NOT EXISTS `task` (
  `task_id` INT NOT NULL AUTO_INCREMENT,
  `project_id` BIGINT NOT NULL,
  `sprint_id` INT DEFAULT NULL,
  `parent_task_id` INT DEFAULT NULL,
  `task_name` VARCHAR(255) NOT NULL,
  `description` TEXT,
  `task_type` ENUM('Task','Bug','Story','Epic','Spike') DEFAULT 'Task',
  `priority` ENUM('Low','Medium','High','Critical') DEFAULT 'Medium',
  `status` ENUM('To Do','In Progress','In Review','Blocked','Completed') DEFAULT 'To Do',
  `estimated_hours` INT DEFAULT 0,
  `logged_hours` INT DEFAULT 0,
  `story_points` INT DEFAULT 0,
  `assignee` VARCHAR(255) DEFAULT NULL,
  `start_date` DATE NOT NULL,
  `actual_start_date` DATE DEFAULT NULL,
  `end_date` DATE NOT NULL,
  `actual_end_date` DATE DEFAULT NULL,
  `created_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`task_id`),
  INDEX `idx_task_project` (`project_id`),
  INDEX `idx_task_sprint` (`sprint_id`),
  INDEX `idx_task_parent` (`parent_task_id`),
  INDEX `idx_task_type` (`task_type`),
  INDEX `idx_task_priority` (`priority`),
  INDEX `idx_task_status` (`status`),
  INDEX `idx_task_assignee` (`assignee`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='Task and work item tracking';

-- ============================================ tbl_blocker TABLE
-- Stores project blockers that prevent work from progressing
CREATE TABLE IF NOT EXISTS `tbl_blocker` (
  `blocker_id` INT NOT NULL AUTO_INCREMENT,
  `project_id` BIGINT NOT NULL,
  `sprint_id` INT DEFAULT NULL,
  `task_id` INT DEFAULT NULL,
  `blocker_title` VARCHAR(255) NOT NULL,
  `blocker_description` TEXT DEFAULT NULL,
  `blocker_type` ENUM('Technical','Dependency','Resource','Requirement','Infrastructure','External','Other') NOT NULL,
  `severity` ENUM('Low','Medium','High','Critical') DEFAULT 'Medium',
  `status` ENUM('Open','In Progress','Resolved') DEFAULT 'Open',
  `reported_by` VARCHAR(255) NOT NULL,
  `assigned_to` VARCHAR(255) DEFAULT NULL,
  `reported_date` DATE NOT NULL,
  `resolved_date` DATE DEFAULT NULL,
  `created_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`blocker_id`),
  INDEX `idx_blocker_project` (`project_id`),
  INDEX `idx_blocker_sprint` (`sprint_id`),
  INDEX `idx_blocker_task` (`task_id`),
  INDEX `idx_blocker_type` (`blocker_type`),
  INDEX `idx_blocker_severity` (`severity`),
  INDEX `idx_blocker_status` (`status`),
  INDEX `idx_blocker_reported_date` (`reported_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='Project blockers tracking with severity and resolution status';

-- ============================================ tbl_risk_parameters_selection TABLE
-- Stores risk parameter selection and weights for projects
CREATE TABLE IF NOT EXISTS `tbl_risk_parameters_selection` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `project_id` BIGINT NOT NULL,

    `uncompleted_tasks` BOOLEAN DEFAULT FALSE,
    `uncompleted_tasks_weight` INT DEFAULT 0,

    `detected_bugs` BOOLEAN DEFAULT FALSE,
    `detected_bugs_weight` INT DEFAULT 0,

    `blockers_count` BOOLEAN DEFAULT FALSE,
    `blockers_count_weight` INT DEFAULT 0,

    `developer_workload` BOOLEAN DEFAULT FALSE,
    `developer_workload_weight` INT DEFAULT 0,

    `task_dependency` BOOLEAN DEFAULT FALSE,
    `task_dependency_weight` INT DEFAULT 0,

    `timeline_conflict` BOOLEAN DEFAULT FALSE,
    `timeline_conflict_weight` INT DEFAULT 0,

    `developer_availability` BOOLEAN DEFAULT FALSE,
    `developer_availability_weight` INT DEFAULT 0,

    `task_progress` BOOLEAN DEFAULT FALSE,
    `task_progress_weight` INT DEFAULT 0,

    `sprint_completion_level` BOOLEAN DEFAULT FALSE,
    `sprint_completion_level_weight` INT DEFAULT 0,

    `project_budget` BOOLEAN DEFAULT FALSE,
    `project_budget_weight` INT DEFAULT 0,

    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX `idx_risk_project` (`project_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='Risk parameter selection and weights for project risk analysis';


-- ============================================
-- FOREIGN KEY CONSTRAINTS
-- ============================================
-- Maintains referential integrity between tables
-- Pattern: ALTER TABLE `child_table` ADD CONSTRAINT `fk_child_parent`
-- ============================================

-- Project Backlog -> Projects relationship
-- Ensures backlog items belong to valid projects
ALTER TABLE `project_backlog`
    ADD CONSTRAINT `fk_backlog_project`
    FOREIGN KEY (`project_id`)
    REFERENCES `projects`(`project_id`)
    ON UPDATE CASCADE
    ON DELETE CASCADE;

-- Sprint -> Projects relationship
-- Ensures sprints belong to valid projects
ALTER TABLE `sprint`
    ADD CONSTRAINT `fk_sprint_project`
    FOREIGN KEY (`project_id`)
    REFERENCES `projects`(`project_id`)
    ON UPDATE CASCADE
    ON DELETE CASCADE;

-- Sprint Leave -> Sprint relationship
-- Ensures leave records belong to valid sprints
ALTER TABLE `sprint_leave`
    ADD CONSTRAINT `fk_leave_sprint`
    FOREIGN KEY (`sprint_id`)
    REFERENCES `sprint`(`sprint_id`)
    ON UPDATE CASCADE
    ON DELETE CASCADE;

-- Sprint Leave -> Projects relationship
-- Ensures leave records belong to valid projects
ALTER TABLE `sprint_leave`
    ADD CONSTRAINT `fk_leave_project`
    FOREIGN KEY (`project_id`)
    REFERENCES `projects`(`project_id`)
    ON UPDATE CASCADE
    ON DELETE CASCADE;

-- Task -> Projects relationship
-- Ensures tasks belong to valid projects
ALTER TABLE `task`
    ADD CONSTRAINT `fk_task_project`
    FOREIGN KEY (`project_id`)
    REFERENCES `projects`(`project_id`)
    ON UPDATE CASCADE
    ON DELETE CASCADE;

-- Task -> Sprint relationship
-- Ensures tasks belong to valid sprints (nullable)
ALTER TABLE `task`
    ADD CONSTRAINT `fk_task_sprint`
    FOREIGN KEY (`sprint_id`)
    REFERENCES `sprint`(`sprint_id`)
    ON UPDATE CASCADE
    ON DELETE SET NULL;

-- Risk Parameters Selection -> Projects relationship
-- Ensures risk parameters belong to valid projects
ALTER TABLE `tbl_risk_parameters_selection`
    ADD CONSTRAINT `fk_risk_params_project`
    FOREIGN KEY (`project_id`)
    REFERENCES `projects`(`project_id`)
    ON UPDATE CASCADE
    ON DELETE CASCADE;

-- Blocker -> Projects relationship
-- Ensures blockers belong to valid projects
ALTER TABLE `tbl_blocker`
    ADD CONSTRAINT `fk_blocker_project`
    FOREIGN KEY (`project_id`)
    REFERENCES `projects`(`project_id`)
    ON UPDATE CASCADE
    ON DELETE CASCADE;

-- Blocker -> Sprint relationship
-- Ensures blockers belong to valid sprints (nullable)
ALTER TABLE `tbl_blocker`
    ADD CONSTRAINT `fk_blocker_sprint`
    FOREIGN KEY (`sprint_id`)
    REFERENCES `sprint`(`sprint_id`)
    ON UPDATE CASCADE
    ON DELETE SET NULL;

-- Blocker -> Task relationship
-- Ensures blockers belong to valid tasks (nullable)
ALTER TABLE `tbl_blocker`
    ADD CONSTRAINT `fk_blocker_task`
    FOREIGN KEY (`task_id`)
    REFERENCES `task`(`task_id`)
    ON UPDATE CASCADE
    ON DELETE SET NULL;

-- Add future foreign key constraints below following the same pattern:
-- 
-- Example template:
-- Relationship description goes in comment above the ALTER statement
-- ALTER TABLE `child_table`
--     ADD CONSTRAINT `fk_child_parent`
--     FOREIGN KEY (`parent_id`)
--     REFERENCES `parent_table`(`id`)
--     ON UPDATE CASCADE
--     ON DELETE [CASCADE|SET NULL|RESTRICT];
-- ============================================


