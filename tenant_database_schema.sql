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

-- ============================================
-- 2. SPRINTS TABLE
-- ============================================
-- Sprint management and tracking
-- ============================================
CREATE TABLE IF NOT EXISTS `sprints` (
    `sprint_id` VARCHAR(50) PRIMARY KEY COMMENT 'Unique sprint identifier (e.g., spr-abc123)',
    `sprint_name` VARCHAR(255) NOT NULL COMMENT 'Sprint name/title',
    `sprint_goal` TEXT COMMENT 'Sprint goal/objective',
    `start_date` DATE NOT NULL COMMENT 'Sprint start date',
    `end_date` DATE NOT NULL COMMENT 'Sprint end date',
    `status` ENUM('PLANNED', 'ACTIVE', 'COMPLETED', 'CANCELLED') DEFAULT 'PLANNED' COMMENT 'Sprint status',
    `velocity` INT COMMENT 'Sprint velocity (story points completed)',
    `created_by` VARCHAR(50) COMMENT 'User ID who created sprint',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX `idx_status` (`status`),
    INDEX `idx_dates` (`start_date`, `end_date`),
    INDEX `idx_created_by` (`created_by`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='Sprint tracking and management';

-- ============================================
-- 3. TASKS TABLE
-- ============================================
-- Task and issue tracking with Jira integration
-- ============================================
CREATE TABLE IF NOT EXISTS `tasks` (
    `task_id` VARCHAR(50) PRIMARY KEY COMMENT 'Unique task identifier (e.g., tsk-xyz789)',
    `sprint_id` VARCHAR(50) COMMENT 'Associated sprint ID',
    `task_title` VARCHAR(255) NOT NULL COMMENT 'Task title',
    `task_description` TEXT COMMENT 'Task description',
    `task_type` ENUM('STORY', 'TASK', 'BUG', 'EPIC', 'SUBTASK') DEFAULT 'TASK' COMMENT 'Task type',
    `priority` ENUM('HIGHEST', 'HIGH', 'MEDIUM', 'LOW', 'LOWEST') DEFAULT 'MEDIUM' COMMENT 'Task priority',
    `status` ENUM('TODO', 'IN_PROGRESS', 'IN_REVIEW', 'DONE', 'BLOCKED') DEFAULT 'TODO' COMMENT 'Task status',
    `assigned_to` VARCHAR(50) COMMENT 'User ID task is assigned to',
    `story_points` INT COMMENT 'Story points estimate',
    `time_estimate_hours` DECIMAL(5,2) COMMENT 'Time estimate in hours',
    `time_spent_hours` DECIMAL(5,2) COMMENT 'Time spent in hours',
    `jira_issue_key` VARCHAR(50) COMMENT 'Linked Jira issue key (e.g., PROJ-123)',
    `jira_issue_id` VARCHAR(50) COMMENT 'Linked Jira issue ID',
    `parent_task_id` VARCHAR(50) COMMENT 'Parent task ID for subtasks',
    `labels` JSON COMMENT 'Array of task labels',
    `created_by` VARCHAR(50) COMMENT 'User ID who created task',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX `idx_sprint` (`sprint_id`),
    INDEX `idx_status` (`status`),
    INDEX `idx_priority` (`priority`),
    INDEX `idx_assigned_to` (`assigned_to`),
    INDEX `idx_created_by` (`created_by`),
    INDEX `idx_jira` (`jira_issue_key`),
    INDEX `idx_parent` (`parent_task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='Task and issue tracking';

-- ============================================
-- 4. MEETINGS TABLE
-- ============================================
-- Meeting records and documentation
-- ============================================
CREATE TABLE IF NOT EXISTS `meetings` (
    `meeting_id` VARCHAR(50) PRIMARY KEY COMMENT 'Unique meeting identifier (e.g., mtg-def456)',
    `meeting_title` VARCHAR(255) NOT NULL COMMENT 'Meeting title',
    `meeting_type` ENUM('DAILY_STANDUP', 'SPRINT_PLANNING', 'SPRINT_REVIEW', 'SPRINT_RETROSPECTIVE', 'BACKLOG_REFINEMENT', 'OTHER') DEFAULT 'OTHER' COMMENT 'Meeting type',
    `meeting_date` DATETIME NOT NULL COMMENT 'Meeting date and time',
    `duration_minutes` INT COMMENT 'Meeting duration in minutes',
    `sprint_id` VARCHAR(50) COMMENT 'Associated sprint ID',
    `attendees` JSON COMMENT 'Array of attendee user IDs',
    `agenda` TEXT COMMENT 'Meeting agenda',
    `notes` TEXT COMMENT 'Meeting notes',
    `action_items` JSON COMMENT 'Array of action items',
    `recording_url` VARCHAR(500) COMMENT 'Meeting recording URL',
    `created_by` VARCHAR(50) COMMENT 'User ID who created meeting',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX `idx_date` (`meeting_date`),
    INDEX `idx_type` (`meeting_type`),
    INDEX `idx_sprint` (`sprint_id`),
    INDEX `idx_created_by` (`created_by`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='Meeting records and documentation';

-- ============================================
-- 5. RETROSPECTIVES TABLE
-- ============================================
-- Sprint retrospective data and insights
-- ============================================
CREATE TABLE IF NOT EXISTS `retrospectives` (
    `retro_id` VARCHAR(50) PRIMARY KEY COMMENT 'Unique retrospective identifier (e.g., ret-ghi012)',
    `sprint_id` VARCHAR(50) NOT NULL COMMENT 'Associated sprint ID',
    `retro_date` DATETIME NOT NULL COMMENT 'Retrospective date',
    `went_well` JSON COMMENT 'Things that went well (array of items)',
    `to_improve` JSON COMMENT 'Things to improve (array of items)',
    `action_items` JSON COMMENT 'Action items for next sprint (array)',
    `team_mood` ENUM('VERY_HAPPY', 'HAPPY', 'NEUTRAL', 'UNHAPPY', 'VERY_UNHAPPY') COMMENT 'Overall team mood',
    `team_velocity` INT COMMENT 'Team velocity for the sprint',
    `completed_story_points` INT COMMENT 'Story points completed',
    `participants` JSON COMMENT 'Array of participant user IDs',
    `facilitator_id` VARCHAR(50) COMMENT 'User ID of facilitator',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX `idx_sprint` (`sprint_id`),
    INDEX `idx_date` (`retro_date`),
    INDEX `idx_facilitator` (`facilitator_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='Sprint retrospective data';

-- ============================================
-- INITIAL DATA (Optional)
-- ============================================
-- Insert default tenant info
-- This will be populated during tenant registration
-- INSERT INTO `tenant_info` (domain, tenant_name, tenant_email, tenant_status)
-- VALUES ('{DOMAIN}', '{COMPANY_NAME}', '{ADMIN_EMAIL}', 'ACTIVE');

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- Check all tables created
SELECT 
    TABLE_NAME,
    TABLE_ROWS,
    CREATE_TIME,
    TABLE_COMMENT
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = '{TENANT_DB}'
ORDER BY TABLE_NAME;

-- ============================================
-- NOTES
-- ============================================
-- 1. This schema is applied automatically during tenant registration
-- 2. Each tenant gets their own isolated database
-- 3. Database name = domain extracted from email (e.g., visionexdigital)
-- 4. All user management happens in centralized database
-- 5. This database stores tenant-specific operational data only
-- 6. Backup each tenant database separately for data isolation

-- ============================================
-- USAGE EXAMPLE
-- ============================================
-- For tenant with email: admin@visionexdigital.com.au
-- Database name: visionexdigital
-- 
-- To create:
-- CREATE DATABASE visionexdigital CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE visionexdigital;
-- [Run all CREATE TABLE statements above]
