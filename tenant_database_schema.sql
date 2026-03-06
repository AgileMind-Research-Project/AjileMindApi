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

-- ============================================
-- DOCUMENTS TABLE
-- ============================================
-- Stores documents for RAG-based chatbot

CREATE TABLE IF NOT EXISTS `documents` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `doc_title` VARCHAR(255) NOT NULL COMMENT 'Title of the document',
    `doc_content` LONGTEXT NOT NULL COMMENT 'Complete document content for RAG context',
    `uploaded_date` DATE NOT NULL COMMENT 'Date when document was uploaded',
    `category` VARCHAR(100) COMMENT 'Optional category for document classification',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    `is_active` BOOLEAN DEFAULT TRUE COMMENT 'Soft delete flag',
    
    -- Indexes for performance
    INDEX `idx_uploaded_date` (`uploaded_date`),
    INDEX `idx_category` (`category`),
    INDEX `idx_created_at` (`created_at`),
    INDEX `idx_is_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Table for storing documents used in RAG-based chatbot';

-- ============================================ projects TABLE
-- Stores project details for the tenant
CREATE TABLE IF NOT EXISTS `projects` (
    `project_id` BIGINT NOT NULL
        COMMENT 'Project ID provided by jira or system',

    `project_name` VARCHAR(255) NOT NULL COMMENT 'Name of the project',
    `key` VARCHAR(255) NOT NULL COMMENT 'Project key provided by system',
    `board_id` BIGINT  DEFAULT NULL COMMENT 'Board ID provided by jira or system',
    `project_type` VARCHAR(100) NOT NULL COMMENT 'Type/category of the project',
    `start_date` DATE NOT NULL COMMENT 'Project start date',
    `end_date` DATE NOT NULL COMMENT 'Project end date',

    `key` VARCHAR(255) NOT NULL
        COMMENT 'Project key provided by system',

    `project_type` VARCHAR(100) NOT NULL
        COMMENT 'Type/category of the project',

    `start_date` DATE NOT NULL
        COMMENT 'Project start date',

    `end_date` DATE NOT NULL
        COMMENT 'Project end date',

    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        COMMENT 'Record creation time',

    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
        COMMENT 'Last update time',

    `sprint_size` INT DEFAULT NULL
        COMMENT 'Sprint duration in weeks (typically 1-4)',

    `project_lead` VARCHAR(255) DEFAULT NULL
        COMMENT 'Project lead name or email',

    `architecture_type` ENUM(
        'Monolithic', 'Microservices', 'Serverless',
        'Event-Driven', 'Layered', 'Modular', 'Other'
    ) DEFAULT NULL
        COMMENT 'Project architecture pattern',

    `stack_type` ENUM('Frontend', 'Backend', 'Fullstack') NULL COMMENT 'Application stack type',
    
    -- Technology Stack
    `frontend_technologies` JSON NULL COMMENT 'Frontend technologies (e.g., ["React","TypeScript"])',
    `backend_technologies` JSON NULL COMMENT 'Backend technologies (e.g., ["Node.js","Spring Boot"])',
    
    -- Infrastructure
    `cloud_host` VARCHAR(100) NULL COMMENT 'Cloud hosting provider',
    `budget` DECIMAL(12,2) NULL COMMENT 'Project budget',
    `trust_index_threshold` INT DEFAULT 80 COMMENT 'Trust index threshold',
    `prioritize_task_count` INT DEFAULT 15 COMMENT 'Number of tasks to prioritize',
    `working_hours_for_day` INT DEFAULT 8 COMMENT 'Number of working hours for a day',

    `frontend_technologies` JSON DEFAULT NULL
        COMMENT 'Frontend technologies, frameworks, and languages (e.g., ["React", "TypeScript", "TailwindCSS"])',

    `backend_technologies` JSON DEFAULT NULL
        COMMENT 'Backend technologies, frameworks, and languages (e.g., ["Node.js", "Express", "MongoDB"])',

    `cloud_host` VARCHAR(100) DEFAULT NULL
        COMMENT 'Cloud hosting provider (e.g., AWS, Azure, GCP, DigitalOcean)',

    `budget` DECIMAL(12,2) DEFAULT NULL
        COMMENT 'Total planned project budget in USD',

    `next_sprint_start_date` DATE DEFAULT NULL
        COMMENT 'Next sprint start date calculated from sprint size',

    `project_manager` JSON DEFAULT NULL
        COMMENT 'Project management manners used (e.g., ["Agile","Scrum","Kanban","Hybrid"])',

    `board_id` BIGINT DEFAULT NULL
        COMMENT 'Jira board identifier',

    `trust_index_threshold` INT DEFAULT NULL
        COMMENT 'Trust index threshold',

    `prioritize_task_count` INT DEFAULT NULL
        COMMENT 'Number of tasks to prioritize',

    -- Primary Key
    PRIMARY KEY (`project_id`),

    -- Unique constraints
    UNIQUE KEY `unique_project_key` (`key`),
    UNIQUE KEY `unique_project_name` (`project_name`),

    -- Indexes
    INDEX `idx_project_name` (`project_name`),
    INDEX `idx_project_key` (`key`),
    INDEX `idx_start_date` (`start_date`),
    INDEX `idx_end_date` (`end_date`)

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


-- ============================================ sprint TABLE
-- Stores sprint details for projects
CREATE TABLE IF NOT EXISTS `sprint` (
  `sprint_id` int NOT NULL,
  `project_id` bigint NOT NULL,
  `sprint_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `sprint_goal` text COLLATE utf8mb4_unicode_ci,
  `start_date` date NOT NULL,
  `end_date` date NOT NULL,
  `sprint_status` enum('Not Started','In Progress','Completed','Closed') COLLATE utf8mb4_unicode_ci DEFAULT 'Not Started',
  `total_estimated_hours` int DEFAULT '0',
  `total_completed_hours` int DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`sprint_id`),
  KEY `project_id` (`project_id`),
  CONSTRAINT `sprint_ibfk_1` FOREIGN KEY (`project_id`) REFERENCES `projects` (`project_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================ project_backlog TABLE
-- Stores backlog items for projects

CREATE TABLE IF NOT EXISTS `project_backlog` (
    `id` VARCHAR(128) NOT NULL
        COMMENT 'Backlog unique ID created by jira',

    `project_id` BIGINT NOT NULL
        COMMENT 'Project ID this backlog item belongs to',

    `sprint_id` INT NULL
        COMMENT 'Sprint ID this item is assigned to',

  `summary` VARCHAR(255) COLLATE utf8mb4_unicode_ci NOT NULL
    COMMENT 'Backlog item name / summary',

    `description` TEXT
        COMMENT 'Detailed description of the backlog item',

    `issue_type` VARCHAR(100) NOT NULL
        COMMENT 'Type: story, feature, change, bug',

    `status` VARCHAR(100) NOT NULL DEFAULT 'todo'
        COMMENT 'Current status: todo, in_progress, done',

    `priority` VARCHAR(100) DEFAULT NULL
        COMMENT 'Priority: high, medium, low',

    `severity` VARCHAR(100) DEFAULT NULL
        COMMENT 'Severity level if applicable',

    `assignee` VARCHAR(255) DEFAULT NULL
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

    `parent_task_id` VARCHAR(128) DEFAULT NULL
        COMMENT 'Parent task ID for subtasks (supports Jira keys like TAM-48)',

    `start_date` DATE DEFAULT NULL
        COMMENT 'Planned start date',

    `actual_start_date` DATE DEFAULT NULL
        COMMENT 'Actual start date',

    `end_date` DATE DEFAULT NULL
        COMMENT 'Planned end date',

    `actual_end_date` DATE DEFAULT NULL
        COMMENT 'Actual end date',

    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        COMMENT 'Record creation time',

    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
        COMMENT 'Last update time',

    `is_jira` TINYINT(1) NOT NULL DEFAULT 1
        COMMENT 'Flag for Jira integration (true = enabled)',

    `story_point_estimate` INT DEFAULT 0
        COMMENT 'Story Point Estimate',

    -- Primary Key
    PRIMARY KEY (`id`),

    -- Indexes
    INDEX `idx_project_id` (`project_id`),
    INDEX `idx_issue_type` (`issue_type`),
    INDEX `idx_status` (`status`),
    INDEX `idx_priority` (`priority`),
    INDEX `idx_sprint_id` (`sprint_id`),
    INDEX `idx_parent_task_id` (`parent_task_id`)

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



-- Migration: Add Documents Table for RAG-based Chatbot
-- Description: Creates documents table to store document content for RAG (Retrieval Augmented Generation) based chatbot
-- Date: 2025-12-22



-- Optional: Add tenant_id if multi-tenancy is needed
-- ALTER TABLE documents ADD COLUMN tenant_id INT NOT NULL AFTER id;
-- ALTER TABLE documents ADD FOREIGN KEY (tenant_id) REFERENCES tenants(id);

-- ============================================
-- MEETINGS TABLE
-- ============================================
-- Stores meeting records for the tenant
CREATE TABLE IF NOT EXISTS `meetings` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `meeting_id` VARCHAR(50) NOT NULL UNIQUE COMMENT 'Unique meeting identifier (UUID)',
    `project_id` BIGINT NULL COMMENT 'Associated project ID (optional)',
    `title` VARCHAR(255) NOT NULL COMMENT 'Meeting title',
    `description` TEXT NULL COMMENT 'Meeting agenda or description',
    
    -- Schedule
    `date` DATE NOT NULL COMMENT 'Meeting date',
    `start_time` TIME NOT NULL COMMENT 'Start time',
    `end_time` TIME NOT NULL COMMENT 'End time',
    
    -- Status & Type
    `status` ENUM('SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED') DEFAULT 'SCHEDULED',
    `category` VARCHAR(100) DEFAULT 'Daily Meeting' COMMENT 'Meeting category (e.g., Daily, Sprint Planning)',
    
    -- Content
    `meeting_transcript` LONGTEXT NULL COMMENT 'AI generated or manual transcript',
    `recording_url` VARCHAR(500) NULL COMMENT 'Link to meeting recording',
    `attendees` JSON NULL COMMENT 'List of meeting attendees (emails or user IDs)',
    
    -- Metadata
    `created_by` VARCHAR(100) NULL COMMENT 'User ID who created the meeting',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Indexes
    INDEX `idx_project_id` (`project_id`),
    INDEX `idx_date` (`date`),
    INDEX `idx_status` (`status`),
    INDEX `idx_category` (`category`),

    -- Foreign Key
    CONSTRAINT `fk_meetings_project`
        FOREIGN KEY (`project_id`)
        REFERENCES `projects` (`project_id`)
        ON UPDATE CASCADE
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Meeting records and schedules';

-- ============================================
-- TASK_UPDATES TABLE  
-- ============================================
-- AI-extracted task updates from meeting transcripts with human approval workflow
CREATE TABLE IF NOT EXISTS `task_updates` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `meeting_id` VARCHAR(50) NOT NULL COMMENT 'Reference to meetings table',
    `ticket_id` VARCHAR(50) NOT NULL COMMENT 'Jira ticket ID (e.g., API-400, BUG-102)',
    `task_id` INT NULL COMMENT 'Reference to task table if matched',
    `project_id` BIGINT NOT NULL COMMENT 'Project this task belongs to',
    
    -- AI Extracted Data
    `detected_status` ENUM('TODO', 'IN_PROGRESS', 'DONE', 'BLOCKED') NOT NULL COMMENT 'Status detected by AI',
    `blocker_description` TEXT NULL COMMENT 'Blocker details if status is BLOCKED',
    `ai_confidence_score` DECIMAL(3,2) DEFAULT 0.00 COMMENT 'AI confidence (0.00-1.00)',
    `ai_reasoning` TEXT NULL COMMENT 'Chain of Thought reasoning from AI',
    `extracted_context` TEXT NULL COMMENT 'Relevant excerpt from transcript',
    
    -- Approval Workflow
    `approval_status` ENUM('PENDING', 'APPROVED', 'REJECTED') DEFAULT 'PENDING',
    `reviewed_by` VARCHAR(100) NULL COMMENT 'User who reviewed',
    `review_timestamp` DATETIME NULL,
    `reviewer_remark` TEXT NULL COMMENT 'Optional remark from reviewer',
    
    -- Jira Integration
    `jira_sync_status` ENUM('NOT_SYNCED', 'SYNCED', 'FAILED') DEFAULT 'NOT_SYNCED',
    `jira_sync_timestamp` DATETIME NULL,
    `jira_error_message` TEXT NULL,
    
    -- Metadata
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX `idx_meeting_id` (`meeting_id`),
    INDEX `idx_ticket_id` (`ticket_id`),
    INDEX `idx_project_id` (`project_id`),
    INDEX `idx_approval_status` (`approval_status`),
    INDEX `idx_jira_sync_status` (`jira_sync_status`),
    
    -- Foreign Keys
    CONSTRAINT `fk_task_updates_meeting`
        FOREIGN KEY (`meeting_id`)
        REFERENCES `meetings` (`meeting_id`)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    
    CONSTRAINT `fk_task_updates_project`
        FOREIGN KEY (`project_id`)
        REFERENCES `projects` (`project_id`)
        ON UPDATE CASCADE
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI-extracted task updates with approval workflow';
-- ALTER TABLE documents ADD INDEX idx_tenant_id (tenant_id);

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='History of system downtime and maintenance notifications';

-- ============================================
-- RELEASE_NOTES TABLE
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

