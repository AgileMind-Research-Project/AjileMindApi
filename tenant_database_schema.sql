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
    `board_id` BIGINT  DEFAULT NULL COMMENT 'Board ID provided by jira or system',
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

CREATE TABLE IF NOT EXISTS `project_backlog` (
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

  `story_point_estimate` INT DEFAULT 0
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
  KEY `idx_parent_task_id` (`parent_task_id`)

) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_unicode_ci
COMMENT='Backlog items before project start and future changes/features';


-- ============================================ sprint TABLE
-- Stores sprint information for projects.
-- NOTE: sprint_id IS the Jira sprint ID (bigint, no AUTO_INCREMENT).
--       The Jira sprint ID must be fetched via /rest/agile/1.0/board/{boardId}/sprint
--       BEFORE inserting, and is supplied as sprint_id at INSERT time.
CREATE TABLE IF NOT EXISTS `sprint` (
  `sprint_id` bigint NOT NULL COMMENT 'Jira sprint ID — used as PK, no AUTO_INCREMENT',
  `project_id` bigint NOT NULL,
  `sprint_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `sprint_goal` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `start_date` date NOT NULL,
  `end_date` date NOT NULL,
  `sprint_status` enum('Future','Active','Closed','On Hold','Cancelled') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'Future',
  `total_estimated_hours` int DEFAULT '0',
  `total_completed_hours` int DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`sprint_id`),
  KEY `project_id` (`project_id`),
  CONSTRAINT `sprint_ibfk_1` FOREIGN KEY (`project_id`) REFERENCES `projects` (`project_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


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
    INDEX `idx_sprint_id` (`sprint_id`)

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

-- ============================================
-- FOREIGN KEY CONSTRAINTS
-- ============================================
-- Adding foreign keys after all tables are created
-- ============================================

-- project_backlog foreign keys
ALTER TABLE `project_backlog`
ADD CONSTRAINT `fk_backlog_project`
    FOREIGN KEY (`project_id`)
    REFERENCES `projects` (`project_id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE;

-- sprint foreign keys
ALTER TABLE `sprint`
ADD CONSTRAINT `fk_sprint_project`
    FOREIGN KEY (`project_id`)
    REFERENCES `projects` (`project_id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE;

-- project_backlog_priority foreign keys
ALTER TABLE `project_backlog_priority`
ADD CONSTRAINT `fk_priority_project`
    FOREIGN KEY (`project_id`)
    REFERENCES `projects` (`project_id`)
    ON UPDATE CASCADE
    ON DELETE CASCADE;

ALTER TABLE `project_backlog_priority`
ADD CONSTRAINT `fk_priority_backlog`
    FOREIGN KEY (`backlog_id`)
    REFERENCES `project_backlog` (`id`)
    ON UPDATE CASCADE
    ON DELETE CASCADE;

ALTER TABLE `project_backlog_priority`
ADD CONSTRAINT `fk_priority_sprint`
    FOREIGN KEY (`sprint_id`)
    REFERENCES `sprint` (`sprint_id`)
    ON UPDATE CASCADE
    ON DELETE CASCADE;

-- ============================================
-- TRANSCRIPTS TABLE
-- ============================================
CREATE TABLE `transcripts` (
    `id` int NOT NULL AUTO_INCREMENT,
    `meeting_id` varchar(50) DEFAULT NULL COMMENT 'Reference to meetings.meeting_id',
    `title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Transcript title',
    `category` enum('daily_standup','sprint_meeting','retrospective','sprint_planning','other') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Meeting type',
    `transcript_content` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Full transcript text',
    `transcript_date` date NOT NULL COMMENT 'Date of the meeting',
    `tags` json DEFAULT NULL COMMENT 'Tags for categorization',
    `file_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Original uploaded filename',
    `uploaded_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'User ID who uploaded',
    `tenant_schema` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Tenant schema identifier',
    `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `project_id` BIGINT DEFAULT 0 COMMENT 'Reference to projects.project_id',
    `sprint_id` BIGINT DEFAULT NULL COMMENT 'Reference to sprint.sprint_id',
    PRIMARY KEY (`id`),
    KEY `idx_category` (`category`),
    KEY `idx_date` (`transcript_date`),
    KEY `idx_tenant` (`tenant_schema`),
    KEY `idx_project_id` (`project_id`),
    KEY `idx_sprint_id` (`sprint_id`),
    FULLTEXT KEY `idx_content` (`transcript_content`),
    FULLTEXT KEY `idx_title` (`title`),
    CONSTRAINT `fk_transcripts_project`
        FOREIGN KEY (`project_id`)
        REFERENCES `projects`(`project_id`)
        ON DELETE SET NULL
        ON UPDATE CASCADE,
    CONSTRAINT `fk_transcripts_sprint`
        FOREIGN KEY (`sprint_id`)
        REFERENCES `sprint`(`sprint_id`)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB 
  AUTO_INCREMENT=6 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci 
  COMMENT='Meeting transcripts for AI report generation';

-- ============================================
-- SPRINT_LEAVE TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS `sprint_leave` (
  `leave_id` int NOT NULL AUTO_INCREMENT,
  `sprint_id` int NOT NULL,
  `project_id` bigint NOT NULL,
  `developer_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `leave_date` date NOT NULL,
  `leave_hours` int NOT NULL,
  `reason` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `leave_type` enum('Full Day','Half Day','Short Leave') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'Full Day',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`leave_id`),
  KEY `fk_leave_sprint` (`sprint_id`),
  KEY `fk_leave_project` (`project_id`),
  CONSTRAINT `fk_leave_project` FOREIGN KEY (`project_id`) REFERENCES `projects` (`project_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_leave_sprint` FOREIGN KEY (`sprint_id`) REFERENCES `sprint` (`sprint_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `sprint_leave_chk_1` CHECK ((`leave_hours` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


--- Meeting --- 

CREATE TABLE `meetings` (
  `meeting_id` VARCHAR(50) NOT NULL DEFAULT (UUID()),
  `project_id` BIGINT NOT NULL,
  `sprint_id` BIGINT NOT NULL,

  `title` VARCHAR(255) NOT NULL,
  `meeting_category` VARCHAR(100) NOT NULL,

  `meeting_date` DATE NOT NULL,
  `start_time` TIME NOT NULL,
  `end_time` TIME NOT NULL,

  `meeting_link` VARCHAR(500) NOT NULL,
  `status` VARCHAR(30) NOT NULL DEFAULT 'SCHEDULED',

  `created_by` VARCHAR(255) DEFAULT NULL COMMENT 'Email of user who created the meeting',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  `attendees` JSON DEFAULT NULL COMMENT 'List of meeting participants',

  PRIMARY KEY (`meeting_id`, `project_id`, `sprint_id`),

  KEY `idx_project` (`project_id`),
  KEY `idx_sprint` (`sprint_id`),
  KEY `idx_sprint_project_date` (`sprint_id`, `project_id`, `meeting_date`),

  CONSTRAINT `fk_meeting_project`
    FOREIGN KEY (`project_id`)
    REFERENCES `projects` (`project_id`)
    ON DELETE CASCADE,

  CONSTRAINT `fk_meeting_sprint`
    FOREIGN KEY (`sprint_id`)
    REFERENCES `sprint` (`sprint_id`)
    ON DELETE CASCADE,

  CHECK (`end_time` > `start_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

