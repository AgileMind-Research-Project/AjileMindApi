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
    `project_id` BIGINT NOT NULL COMMENT 'Project ID provided by jira or system',
    `project_name` VARCHAR(255) NOT NULL COMMENT 'Name of the project',
    `key` VARCHAR(255) NOT NULL COMMENT 'Project key provided by system',
    `board_id` BIGINT DEFAULT NULL COMMENT 'Board ID provided by jira or system',
    `project_type` VARCHAR(100) NOT NULL COMMENT 'Type/category of the project',
    `start_date` DATE NOT NULL COMMENT 'Project start date',
    `end_date` DATE NOT NULL COMMENT 'Project end date',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update time',
    `sprint_size` INT DEFAULT NULL COMMENT 'Sprint duration in weeks (typically 1-4)',
    `project_lead` VARCHAR(255) DEFAULT NULL COMMENT 'Project lead name or email',
    `architecture_type` ENUM('Monolithic', 'Microservices', 'Serverless', 'Event-Driven', 'Layered', 'Modular', 'Other') DEFAULT NULL COMMENT 'Project architecture pattern',
    `stack_type` ENUM('Frontend', 'Backend', 'Fullstack') NULL COMMENT 'Application stack type',
    `frontend_technologies` JSON DEFAULT NULL COMMENT 'Frontend technologies, frameworks, and languages (e.g., ["React", "TypeScript", "TailwindCSS"])',
    `backend_technologies` JSON DEFAULT NULL COMMENT 'Backend technologies, frameworks, and languages (e.g., ["Node.js", "Express", "MongoDB"])',
    `cloud_host` VARCHAR(100) DEFAULT NULL COMMENT 'Cloud hosting provider (e.g., AWS, Azure, GCP, DigitalOcean)',
    `budget` DECIMAL(12,2) DEFAULT NULL COMMENT 'Total planned project budget in USD',
    `trust_index_threshold` INT DEFAULT 80 COMMENT 'Trust index threshold',
    `prioritize_task_count` INT DEFAULT 15 COMMENT 'Number of tasks to prioritize',
    `working_hours_for_day` INT DEFAULT 8 COMMENT 'Number of working hours for a day',
    `next_sprint_start_date` DATE DEFAULT NULL COMMENT 'Next sprint start date calculated from sprint size',
    `project_manager` JSON DEFAULT NULL COMMENT 'Project management methods used (e.g., ["Agile","Scrum","Kanban","Hybrid"])',

    PRIMARY KEY (`project_id`),
    UNIQUE KEY `unique_project_key` (`key`),
    UNIQUE KEY `unique_project_name` (`project_name`),
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


-- ============================================ project_backlog_priority TABLE
-- Stores backlog items for projects

CREATE TABLE IF NOT EXISTS `project_backlog` (
    `id` VARCHAR(128) NOT NULL COMMENT 'Backlog unique ID created by jira',
    `project_id` BIGINT NOT NULL COMMENT 'Project ID this backlog item belongs to',
    `sprint_id` INT DEFAULT NULL COMMENT 'Sprint ID this item is assigned to',
    `summary` VARCHAR(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Backlog item name / summary',
    `description` TEXT COMMENT 'Detailed description of the backlog item',
    `issue_type` VARCHAR(100) NOT NULL COMMENT 'Type: story, feature, change, bug',
    `status` VARCHAR(100) NOT NULL DEFAULT 'todo' COMMENT 'Current status: todo, in_progress, done',
    `priority` VARCHAR(100) DEFAULT NULL COMMENT 'Priority: high, medium, low',
    `severity` VARCHAR(100) DEFAULT NULL COMMENT 'Severity level if applicable',
    `assignee` VARCHAR(255) DEFAULT NULL COMMENT 'Assigned user/person',
    `tags` JSON DEFAULT NULL COMMENT 'Tags associated with the backlog item',
    `estimated_hours` INT DEFAULT 0 COMMENT 'Estimated effort in hours',
    `logged_hours` INT DEFAULT 0 COMMENT 'Actual logged hours',
    `story_points` INT DEFAULT 0 COMMENT 'Story point estimation',
    `parent_task_id` VARCHAR(128) DEFAULT NULL COMMENT 'Parent task ID for subtasks (supports Jira keys like TAM-48)',
    `start_date` DATE DEFAULT NULL COMMENT 'Planned start date',
    `actual_start_date` DATE DEFAULT NULL COMMENT 'Actual start date',
    `end_date` DATE DEFAULT NULL COMMENT 'Planned end date',
    `actual_end_date` DATE DEFAULT NULL COMMENT 'Actual end date',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update time',
    `is_jira` TINYINT(1) NOT NULL DEFAULT 1 COMMENT 'Flag for Jira integration (true = enabled)',

    PRIMARY KEY (`id`),
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
    `status` ENUM('SCHEDULED', 'IN_PROGRESS', 'END', 'CANCELLED') DEFAULT 'SCHEDULED',
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
CREATE TABLE IF NOT EXISTS `transcripts` (
    `id` int NOT NULL AUTO_INCREMENT,
    `meeting_id` varchar(50) DEFAULT NULL COMMENT 'Reference to meetings.meeting_id',
    `title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Transcript title',
    `category` enum('daily_standup','sprint_meeting','retrospective','sprint_planning','other','sprint_review') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Meeting type',
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
  `sprint_id` bigint NOT NULL,
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

-- ============================================
-- BLOCKERS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS `tbl_blocker` (
  `blocker_id` int(11) NOT NULL AUTO_INCREMENT,
  `project_id` bigint(20) NOT NULL,
  `sprint_id` bigint(20) DEFAULT NULL,
  `task_id` int(11) DEFAULT NULL,
  `blocker_title` varchar(255) NOT NULL,
  `blocker_description` text DEFAULT NULL,
  `blocker_type` enum('Technical','Dependency','Resource','Requirement','Infrastructure','External','Other') NOT NULL,
  `severity` enum('Low','Medium','High','Critical') DEFAULT 'Medium',
  `status` enum('Open','In Progress','Resolved') DEFAULT 'Open',
  `reported_by` varchar(255) NOT NULL,
  `assigned_to` varchar(255) DEFAULT NULL,
  `reported_date` date NOT NULL,
  `resolved_date` date DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`blocker_id`),
  KEY `fk_blocker_project` (`project_id`),
  KEY `fk_blocker_sprint` (`sprint_id`),
  KEY `fk_blocker_task` (`task_id`),
  CONSTRAINT `fk_blocker_project` FOREIGN KEY (`project_id`) REFERENCES `projects` (`project_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_blocker_sprint` FOREIGN KEY (`sprint_id`) REFERENCES `sprint` (`sprint_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- RISK PARAMETERS SELECTION TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS `tbl_risk_parameters_selection` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `project_id` bigint(20) NOT NULL,
  `uncompleted_tasks` tinyint(1) DEFAULT 0,
  `uncompleted_tasks_weight` int(11) DEFAULT 0,
  `detected_bugs` tinyint(1) DEFAULT 0,
  `detected_bugs_weight` int(11) DEFAULT 0,
  `blockers_count` tinyint(1) DEFAULT 0,
  `blockers_count_weight` int(11) DEFAULT 0,
  `developer_workload` tinyint(1) DEFAULT 0,
  `developer_workload_weight` int(11) DEFAULT 0,
  `task_dependency` tinyint(1) DEFAULT 0,
  `task_dependency_weight` int(11) DEFAULT 0,
  `timeline_conflict` tinyint(1) DEFAULT 0,
  `timeline_conflict_weight` int(11) DEFAULT 0,
  `developer_availability` tinyint(1) DEFAULT 0,
  `developer_availability_weight` int(11) DEFAULT 0,
  `task_progress` tinyint(1) DEFAULT 0,
  `task_progress_weight` int(11) DEFAULT 0,
  `sprint_completion_level` tinyint(1) DEFAULT 0,
  `sprint_completion_level_weight` int(11) DEFAULT 0,
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `project_budget` tinyint(1) DEFAULT 0,
  `project_budget_weight` int(11) DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `fk_risk_params_project` (`project_id`),
  CONSTRAINT `fk_risk_params_project` FOREIGN KEY (`project_id`) REFERENCES `projects` (`project_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- REPORTS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS `reports` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `transcript_id` int(11) DEFAULT NULL,
  `project_id` bigint(20) DEFAULT NULL COMMENT 'Associated project ID',
  `report_type` enum('daily_standup','sprint_meeting','retrospective','brainstorming') NOT NULL COMMENT 'Report type',
  `report_content` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT 'Structured report content' CHECK (json_valid(`report_content`)),
  `template_id` int(11) DEFAULT NULL COMMENT 'Template used for generation',
  `version` int(11) DEFAULT 1 COMMENT 'Report version number',
  `status` enum('draft','published') DEFAULT 'draft' COMMENT 'Report status',
  `generated_by` varchar(50) DEFAULT 'llama3.2' COMMENT 'LLM model used',
  `generated_by_user` varchar(50) DEFAULT NULL COMMENT 'User who generated the report',
  `tenant_schema` varchar(100) DEFAULT NULL COMMENT 'Tenant schema identifier',
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_transcript` (`transcript_id`),
  KEY `idx_type` (`report_type`),
  KEY `idx_tenant` (`tenant_schema`),
  KEY `idx_status` (`status`),
  KEY `idx_project_id` (`project_id`),
  CONSTRAINT `fk_reports_transcript` FOREIGN KEY (`transcript_id`) REFERENCES `transcripts` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=74 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI-generated reports from transcripts';

-- ============================================
-- REPORT TEMPLATES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS `report_templates` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `template_name` varchar(255) NOT NULL COMMENT 'Template name',
  `report_type` varchar(50) NOT NULL,
  `header_content` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'Template header' CHECK (json_valid(`header_content`)),
  `footer_content` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'Template footer' CHECK (json_valid(`footer_content`)),
  `sections` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT 'Template sections structure' CHECK (json_valid(`sections`)),
  `styles` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'Styling configuration' CHECK (json_valid(`styles`)),
  `is_default` tinyint(1) DEFAULT 0 COMMENT 'Default template flag',
  `created_by` varchar(50) DEFAULT NULL COMMENT 'User who created the template',
  `tenant_schema` varchar(100) DEFAULT NULL COMMENT 'Tenant schema identifier',
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_type` (`report_type`),
  KEY `idx_tenant` (`tenant_schema`),
  KEY `idx_default` (`is_default`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Report templates for AI report generation';

-- ============================================
-- RECURRING BUGS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS `recurring_bugs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `project_id` bigint(20) NOT NULL,
  `report_id` int(11) NOT NULL,
  `transcript_id` int(11) NOT NULL,
  `bug_title` varchar(500) NOT NULL,
  `bug_description` text DEFAULT NULL,
  `source_section` varchar(100) DEFAULT NULL COMMENT 'where bug was found: what_didnt_go_well, blockers, issues_and_risks',
  `bug_hash` varchar(64) NOT NULL COMMENT 'Hash for finding similar bugs',
  `status` enum('open','resolved','dismissed') DEFAULT 'open',
  `meeting_date` date DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_project_id` (`project_id`),
  KEY `idx_bug_hash` (`bug_hash`),
  KEY `idx_status` (`status`),
  KEY `idx_meeting_date` (`meeting_date`),
  KEY `idx_report_id` (`report_id`)
) ENGINE=InnoDB AUTO_INCREMENT=50 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- NOTIFICATIONS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS `notifications` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT 'Notification ID',
  `header` varchar(255) NOT NULL COMMENT 'Notification header/title',
  `description` text NOT NULL COMMENT 'Notification description/message',
  `related_users` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT 'List of user emails who should see this notification' CHECK (json_valid(`related_users`)),
  `is_read` tinyint(1) DEFAULT 0 COMMENT 'Whether notification has been read',
  `notification_type` enum('INFO','WARNING','SUCCESS','ERROR') DEFAULT 'INFO' COMMENT 'Type of notification',
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_notification_type` (`notification_type`)
) ENGINE=InnoDB AUTO_INCREMENT=56 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='User notifications';

-- ============================================
-- NEW TASKS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS `new_tasks` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `report_id` int(11) NOT NULL,
  `transcript_id` int(11) NOT NULL,
  `project_id` bigint(20) DEFAULT NULL COMMENT 'Associated project ID',
  `task_title` varchar(500) NOT NULL,
  `assignee` varchar(255) DEFAULT NULL,
  `due_date` varchar(50) DEFAULT NULL,
  `priority` varchar(50) DEFAULT NULL,
  `status` enum('pending','approved','removed') DEFAULT 'pending',
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_new_tasks_status` (`status`),
  KEY `idx_new_tasks_report_id` (`report_id`),
  KEY `transcript_id` (`transcript_id`),
  KEY `idx_project_id` (`project_id`),
  CONSTRAINT `new_tasks_ibfk_1` FOREIGN KEY (`report_id`) REFERENCES `reports` (`id`) ON DELETE CASCADE,
  CONSTRAINT `new_tasks_ibfk_2` FOREIGN KEY (`transcript_id`) REFERENCES `transcripts` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--- Meeting Automation Approvals ---

CREATE TABLE IF NOT EXISTS `automation_approvals` (
  `project_id` BIGINT NOT NULL,
  `sprint_id` BIGINT NOT NULL,

  `backlog_prioritize` BOOLEAN NOT NULL DEFAULT 0 COMMENT 'Approval for backlog prioritization automation',
  `split_tasks` BOOLEAN NOT NULL DEFAULT 0 COMMENT 'Approval for automatic task splitting',
  `assign_tasks` BOOLEAN NOT NULL DEFAULT 0 COMMENT 'Approval for automatic task assignment',

  `approved_by` VARCHAR(255) DEFAULT NULL COMMENT 'Email of approver',
  `approved_at` DATETIME DEFAULT NULL,

  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  PRIMARY KEY (`project_id`, `sprint_id`),

  KEY `idx_project` (`project_id`),
  KEY `idx_sprint` (`sprint_id`),

  CONSTRAINT `fk_auto_project`
    FOREIGN KEY (`project_id`)
    REFERENCES `projects` (`project_id`)
    ON DELETE CASCADE,

  CONSTRAINT `fk_auto_sprint`
    FOREIGN KEY (`sprint_id`)
    REFERENCES `sprint` (`sprint_id`)
    ON DELETE CASCADE

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `bugs` (
    `project_id` BIGINT NOT NULL,
    `task_id` VARCHAR(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
    `sprint_id` BIGINT NOT NULL,

    PRIMARY KEY (`project_id`, `task_id`, `sprint_id`),

    CONSTRAINT `fk_bug_project`
        FOREIGN KEY (`project_id`)
        REFERENCES `projects`(`project_id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT `fk_bug_task`
        FOREIGN KEY (`task_id`)
        REFERENCES `project_backlog`(`id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT `fk_bug_sprint`
        FOREIGN KEY (`sprint_id`)
        REFERENCES `sprint`(`sprint_id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `release_notes` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `project_id` bigint(20) NOT NULL COMMENT 'Associated project',
  `version` varchar(50) NOT NULL COMMENT 'Semantic version (e.g., 1.0.0, 2.1.3)',
  `title` varchar(255) NOT NULL COMMENT 'Release title',
  `release_date` date DEFAULT NULL COMMENT 'Scheduled or actual release date',
  `release_type` enum('MAJOR','MINOR','PATCH','HOTFIX') DEFAULT 'MINOR' COMMENT 'Release classification',
  `start_sprint` int(11) DEFAULT NULL,
  `end_sprint` int(11) DEFAULT NULL,
  `content` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'Structured content: {features: [], bug_fixes: [], improvements: [], breaking_changes: [], known_issues: []}' CHECK (json_valid(`content`)),
  `summary` text DEFAULT NULL COMMENT 'Executive summary or overview',
  `status` enum('DRAFT','PUBLISHED','ARCHIVED') DEFAULT 'DRAFT' COMMENT 'Publication status',
  `created_by` varchar(255) NOT NULL COMMENT 'User ID of creator (must be PROJECT_MANAGER)',
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `published_at` datetime DEFAULT NULL COMMENT 'When the release note was published',
  `published_by` varchar(255) DEFAULT NULL COMMENT 'User ID who published the release note',
  PRIMARY KEY (`id`),
  KEY `idx_project_id` (`project_id`),
  KEY `idx_status` (`status`),
  KEY `idx_created_by` (`created_by`),
  KEY `idx_version` (`version`),
  KEY `idx_release_date` (`release_date`),
  KEY `idx_published_at` (`published_at`),
  CONSTRAINT `fk_release_notes_project` FOREIGN KEY (`project_id`) REFERENCES `projects` (`project_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Project release notes with versioning and structured content';

CREATE TABLE IF NOT EXISTS `downtime_notifications` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `type` enum('PLANNED_MAINTENANCE','EMERGENCY_OUTAGE','FEATURE_UPGRADE','SERVICE_DEGRADATION') NOT NULL,
  `priority` enum('HIGH','MEDIUM','LOW') NOT NULL DEFAULT 'MEDIUM',
  `affected_components` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT 'List of affected services' CHECK (json_valid(`affected_components`)),
  `target_emails` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`target_emails`)),
  `start_time` datetime NOT NULL,
  `end_time` datetime NOT NULL,
  `timezone` varchar(50) DEFAULT 'UTC',
  `subject` varchar(255) NOT NULL,
  `message_body` text NOT NULL,
  `audience` enum('ALL_USERS','INTERNAL_TEAM','PROJECT_MEMBERS','ADMINS') NOT NULL,
  `project_id` bigint(20) DEFAULT NULL COMMENT 'If audience is PROJECT_MEMBERS',
  `sent_by_user_id` varchar(50) DEFAULT NULL COMMENT 'Admin/User ID who sent it',
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `scheduled_at` datetime DEFAULT NULL,
  `status` varchar(50) DEFAULT 'PENDING',
  `created_by` varchar(255) DEFAULT NULL,
  `sent_at` datetime DEFAULT NULL,
  `release_note_status` varchar(50) DEFAULT 'NONE',
  `release_note_content` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`release_note_content`)),
  `release_sent_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_type` (`type`),
  KEY `idx_start_time` (`start_time`),
  KEY `idx_project_id` (`project_id`),
  KEY `idx_status` (`status`),
  KEY `idx_release_note_status` (`release_note_status`),
  CONSTRAINT `fk_downtime_project` FOREIGN KEY (`project_id`) REFERENCES `projects` (`project_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='History of system downtime and maintenance notifications';