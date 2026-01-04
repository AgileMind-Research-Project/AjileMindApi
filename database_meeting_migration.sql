-- ============================================
-- Meeting Management Tables
-- Add to tenant database schema
-- ============================================
-- Run this migration on each tenant database
-- Example: USE visionexdigital_db;

-- ============================================
-- 1. MEETINGS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS `meetings` (
    `id` VARCHAR(50) PRIMARY KEY COMMENT 'Unique meeting identifier',
    `title` VARCHAR(255) NOT NULL COMMENT 'Meeting title',
    `description` TEXT COMMENT 'Meeting description',
    `meeting_type` ENUM('standup', 'planning', 'retrospective', 'review', 'general') NOT NULL COMMENT 'Type of meeting',
    `scheduled_date` DATETIME NOT NULL COMMENT 'Scheduled date and time',
    `duration_minutes` INT NOT NULL COMMENT 'Duration in minutes',
    `location` VARCHAR(255) COMMENT 'Meeting location',
    `is_virtual` BOOLEAN DEFAULT FALSE COMMENT 'Whether meeting is virtual',
    `meeting_link` VARCHAR(500) COMMENT 'Virtual meeting link',
    `status` ENUM('scheduled', 'in-progress', 'completed', 'cancelled') DEFAULT 'scheduled' COMMENT 'Meeting status',
    `created_by` VARCHAR(50) NOT NULL COMMENT 'User ID who created the meeting',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `started_at` DATETIME COMMENT 'When meeting actually started',
    `ended_at` DATETIME COMMENT 'When meeting actually ended',
    
    INDEX `idx_scheduled_date` (`scheduled_date`),
    INDEX `idx_meeting_type` (`meeting_type`),
    INDEX `idx_status` (`status`),
    INDEX `idx_created_by` (`created_by`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='Meeting records';

-- ============================================
-- 2. MEETING_PARTICIPANTS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS `meeting_participants` (
    `id` VARCHAR(50) PRIMARY KEY COMMENT 'Unique participant record identifier',
    `meeting_id` VARCHAR(50) NOT NULL COMMENT 'Reference to meeting',
    `user_id` VARCHAR(50) NOT NULL COMMENT 'User ID',
    `attended` BOOLEAN DEFAULT FALSE COMMENT 'Whether user attended',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (`meeting_id`) REFERENCES `meetings`(`id`) ON DELETE CASCADE,
    INDEX `idx_meeting_id` (`meeting_id`),
    INDEX `idx_user_id` (`user_id`),
    UNIQUE KEY `uq_meeting_user` (`meeting_id`, `user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='Meeting participants';

-- ============================================
-- 3. MEETING_NOTES TABLE (Optional)
-- ============================================
CREATE TABLE IF NOT EXISTS `meeting_notes` (
    `id` VARCHAR(50) PRIMARY KEY COMMENT 'Unique note identifier',
    `meeting_id` VARCHAR(50) NOT NULL COMMENT 'Reference to meeting',
    `content` TEXT NOT NULL COMMENT 'Note content',
    `created_by` VARCHAR(50) NOT NULL COMMENT 'User ID who created the note',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (`meeting_id`) REFERENCES `meetings`(`id`) ON DELETE CASCADE,
    INDEX `idx_meeting_id` (`meeting_id`),
    INDEX `idx_created_by` (`created_by`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='Meeting notes';

-- ============================================
-- 4. MEETING_ACTION_ITEMS TABLE (Optional)
-- ============================================
CREATE TABLE IF NOT EXISTS `meeting_action_items` (
    `id` VARCHAR(50) PRIMARY KEY COMMENT 'Unique action item identifier',
    `meeting_id` VARCHAR(50) NOT NULL COMMENT 'Reference to meeting',
    `description` TEXT NOT NULL COMMENT 'Action item description',
    `assigned_to` VARCHAR(50) COMMENT 'User ID assigned to',
    `due_date` DATE COMMENT 'Due date',
    `completed` BOOLEAN DEFAULT FALSE COMMENT 'Whether action item is completed',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (`meeting_id`) REFERENCES `meetings`(`id`) ON DELETE CASCADE,
    INDEX `idx_meeting_id` (`meeting_id`),
    INDEX `idx_assigned_to` (`assigned_to`),
    INDEX `idx_completed` (`completed`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='Meeting action items';
