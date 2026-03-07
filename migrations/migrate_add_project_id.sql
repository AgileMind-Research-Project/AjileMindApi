-- Migration: Add project_id to reports, new_tasks, and recurring_bugs tables
-- Run this migration for each tenant schema

-- Add project_id to reports table
ALTER TABLE `reports` 
ADD COLUMN `project_id` BIGINT DEFAULT NULL COMMENT 'Associated project ID' AFTER `transcript_id`,
ADD INDEX `idx_project_id` (`project_id`);

-- Add project_id to new_tasks table
ALTER TABLE `new_tasks` 
ADD COLUMN `project_id` BIGINT DEFAULT NULL COMMENT 'Associated project ID' AFTER `transcript_id`,
ADD INDEX `idx_project_id` (`project_id`);

-- Add project_id to recurring_bugs table
ALTER TABLE `recurring_bugs` 
ADD COLUMN `project_id` BIGINT DEFAULT NULL COMMENT 'Associated project ID' AFTER `transcript_id`,
ADD INDEX `idx_project_id` (`project_id`);

-- Update existing records to get project_id from transcripts
UPDATE `reports` r
JOIN `transcripts` t ON r.transcript_id = t.id
SET r.project_id = t.project_id
WHERE r.project_id IS NULL;

UPDATE `new_tasks` nt
JOIN `transcripts` t ON nt.transcript_id = t.id
SET nt.project_id = t.project_id
WHERE nt.project_id IS NULL;

UPDATE `recurring_bugs` rb
JOIN `transcripts` t ON rb.transcript_id = t.id
SET rb.project_id = t.project_id
WHERE rb.project_id IS NULL;
