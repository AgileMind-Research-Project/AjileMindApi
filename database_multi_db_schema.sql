-- Multi-Database Tenant Architecture Schema
-- Users stored in CENTRALIZED database (from .env DB_NAME)
-- Each tenant gets their own database with ONLY tenant_info table
-- NO users table in tenant databases

-- Centralized Database (e.g., agilemind_db from .env)
-- Already has users table from database_schema.sql
-- tenant_id field in users table links to tenant database name

-- Example: Tenant Database Structure
-- Database name: tenant_tn_{domain}
-- Example: tenant_tn_sliit, tenant_tn_axixtadigitalalabs
-- Table created dynamically per tenant:

-- 1. tenant_info table (in each tenant database)
-- This is the ONLY table in tenant databases
/*
CREATE TABLE IF NOT EXISTS `tenant_info` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `tenant_id` VARCHAR(50) UNIQUE NOT NULL,
    `tenant_name` VARCHAR(255) NOT NULL,
    `tenant_email` VARCHAR(255) NOT NULL,
    `tenant_status` ENUM('ACTIVE', 'SUSPENDED', 'INACTIVE') DEFAULT 'ACTIVE',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_tenant_id` (`tenant_id`),
    INDEX `idx_status` (`tenant_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
*/

-- 2. users table (in CENTRALIZED database, NOT in tenant databases)
-- This table already exists in main database from database_schema.sql
-- tenant_id field links users to their tenant database
/*
Centralized users table structure (already exists):
- user_id: Primary key
- tenant_id: Links to tenant_tn_{domain} database (e.g., 'tn-sliit')
- email: User email
- password_hash: Hashed password
- first_name, last_name: User names
- role: User role
- status: Account status
- Other user fields...
*/

-- Architecture Overview:
-- =====================
-- 
-- Registration Flow:
-- 1. User registers with email: it223@my.sliit.lk
-- 2. System extracts domain: sliit
-- 3. System generates tenant_id: tn-sliit
-- 4. System creates database: tenant_tn_sliit
-- 5. System creates tenant_info table with tenant metadata
-- 6. System creates user in CENTRALIZED users table with tenant_id = 'tn-sliit'
-- 
-- Login Flow:
-- 1. User enters email: it223@my.sliit.lk
-- 2. System extracts domain: sliit
-- 3. System generates tenant_id: tn-sliit
-- 4. System queries CENTRALIZED users table:
--    SELECT * FROM users WHERE tenant_id = 'tn-sliit' AND email = 'it223@my.sliit.lk'
-- 5. System verifies password
-- 6. System generates JWT with tenant_id and tenant_name
--
-- Database Naming:
-- - Centralized database: From .env DB_NAME (e.g., agilemind_db)
--   Contains: users table (all users from all companies)
-- - Tenant database: tenant_tn_{domain} (e.g., tenant_tn_sliit)
--   Contains: tenant_info table only
--
-- Tenant Linking:
-- - tenant_id in users table = 'tn-sliit'
-- - Corresponding tenant database = tenant_tn_sliit
-- - tenant_info table in tenant_tn_sliit has same tenant_id
--
-- Security:
-- - Users centralized for easy management and authentication
-- - Tenant business data isolated in separate databases
-- - tenant_id links users to their company database
-- - Direct domain-to-database mapping
