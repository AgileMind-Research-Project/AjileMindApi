-- ============================================================================
-- Migration: Convert Single Role to Multiple Roles
-- Description: Update user tables to support multiple role assignments per user
-- ============================================================================

-- Step 1: Add new roles column (JSON array) to tenant tables
-- This needs to be run for each tenant table
-- Replace '{tenant_name}' with actual tenant table names

-- Example for 'sliit' tenant:
ALTER TABLE `sliit`
ADD COLUMN `roles` JSON DEFAULT NULL COMMENT 'User roles as JSON array'
AFTER `role`;

-- Step 2: Migrate existing role data to roles array
-- Convert single role to JSON array format
UPDATE `sliit`
SET `roles` = JSON_ARRAY(`role`)
WHERE `role` IS NOT NULL;

-- Step 3: Update any NULL roles to empty array
UPDATE `sliit`
SET `roles` = JSON_ARRAY()
WHERE `roles` IS NULL;

-- Step 4: (Optional) After confirming migration is successful, 
-- you can drop the old role column:
-- ALTER TABLE `sliit` DROP COLUMN `role`;

-- Note: Keep the old 'role' column temporarily for rollback safety
-- Once you've verified the migration works, you can drop it

-- Step 5: Add index for better performance on role queries
-- ALTER TABLE `sliit` ADD INDEX `idx_roles` ((CAST(`roles` AS CHAR(255)) ARRAY));

-- ============================================================================
-- For Multi-Tenant Setup: Run this for ALL tenant tables
-- ============================================================================

-- To apply this to all tenant tables, you can use this dynamic approach:

-- Show all tenant tables:
-- SELECT TABLE_NAME 
-- FROM INFORMATION_SCHEMA.TABLES 
-- WHERE TABLE_SCHEMA = DATABASE() 
-- AND TABLE_NAME NOT IN ('roles', 'tenant_info', 'projects', 'password_reset_tokens', 'audit_logs');

-- Then run the ALTER TABLE and UPDATE statements for each tenant table

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Check role migration status:
-- SELECT 
--     user_id, 
--     email, 
--     role AS old_role, 
--     roles AS new_roles 
-- FROM `sliit` 
-- LIMIT 10;

-- Count users by number of roles:
-- SELECT 
--     JSON_LENGTH(roles) as role_count,
--     COUNT(*) as user_count
-- FROM `sliit`
-- GROUP BY role_count;

-- ============================================================================
-- Rollback Plan (if needed)
-- ============================================================================

-- If you need to rollback:
-- 1. Restore from the old 'role' column (if not dropped)
-- ALTER TABLE `sliit` DROP COLUMN `roles`;

-- Or if you need to convert back from JSON array to single role:
-- UPDATE `sliit`
-- SET `role` = JSON_UNQUOTE(JSON_EXTRACT(`roles`, '$[0]'))
-- WHERE `roles` IS NOT NULL;
