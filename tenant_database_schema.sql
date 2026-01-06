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
    `project_id` BIGINT NOT NULL PRIMARY KEY COMMENT 'Project ID provided by jira or system',

    `project_name` VARCHAR(255) NOT NULL COMMENT 'Name of the project',
    `key` VARCHAR(255) NOT NULL COMMENT 'Project key provided by system',
    `project_type` VARCHAR(100) NOT NULL COMMENT 'Type/category of the project',
    `start_date` DATE NOT NULL COMMENT 'Project start date',
    `end_date` DATE NOT NULL COMMENT 'Project end date',

    -- Project Management Metadata
    `sprint_size` INT NULL COMMENT 'Sprint duration in weeks (typically 1-4)',
    `project_lead` VARCHAR(255) NULL COMMENT 'Project lead name or email',

    -- Architecture and Stack Information
    `architecture_type` ENUM('Monolithic', 'Microservices', 'Serverless', 'Event-Driven', 'Layered', 'Modular', 'Other') NULL COMMENT 'Project architecture pattern',
    `stack_type` ENUM('Frontend', 'Backend', 'Fullstack') NULL COMMENT 'Application stack type',
    
    -- Technology Stack (separated by frontend/backend based on stack_type)
    `frontend_technologies` JSON NULL COMMENT 'Frontend technologies, frameworks, and languages (e.g., ["React", "TypeScript", "TailwindCSS"])',
    `backend_technologies` JSON NULL COMMENT 'Backend technologies, frameworks, and languages (e.g., ["Node.js", "Express", "MongoDB"])',
    
    -- Infrastructure
    `cloud_host` VARCHAR(100) NULL COMMENT 'Cloud hosting provider (e.g., AWS, Azure, GCP, DigitalOcean)',
    `budget` DECIMAL(12,2) NULL COMMENT 'Project budget',
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
    INDEX `idx_end_date` (`end_date`),
    
    -- Indexes for new columns
    INDEX `idx_project_lead` (`project_lead`),
    INDEX `idx_architecture_type` (`architecture_type`),
    INDEX `idx_stack_type` (`stack_type`),
    INDEX `idx_cloud_host` (`cloud_host`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Project records and timelines';

-- ============================================ project_backlog TABLE
-- Stores backlog items for projects

  CREATE TABLE IF NOT EXISTS `project_backlog` (
    `id` VARCHAR(128) NOT NULL PRIMARY KEY
        COMMENT 'Backlog unique ID created by jira',

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
    `tags` JSON DEFAULT NULL
        COMMENT 'Tags associated with the backlog item',

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


CREATE TABLE IF NOT EXISTS `project_backlog_priority` (
    `project_id` BIGINT NOT NULL
        COMMENT 'Project ID this backlog item belongs to',

    `backlog_id` VARCHAR(128) NOT NULL
        COMMENT 'Backlog item ID (from project_backlog)',

    `rank` INT NOT NULL
        COMMENT 'Priority rank (1 = highest priority)',

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
        ON DELETE CASCADE

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

