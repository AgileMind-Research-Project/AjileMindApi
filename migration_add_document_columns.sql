-- ============================================
-- AUTO MIGRATION: Add Document Chat Columns
-- ============================================
-- This migration adds the required columns for the date-based 
-- document chat feature to the DOCUMENTS table
-- 
-- Columns added:
-- - TITLE: Document title (e.g., "Sprint 15 Standup")
-- - DOCUMENT_TYPE: Enum of document types
-- - BODY: Full text content of document
-- - UPLOAD_DATE: Date document was uploaded (indexed for filtering)
-- ============================================

USE `{TENANT_DB}`;

-- ============================================
-- 1. ALTER DOCUMENTS TABLE - ADD NEW COLUMNS
-- ============================================

ALTER TABLE IF EXISTS `documents`
ADD COLUMN IF NOT EXISTS `title` VARCHAR(255) 
    COMMENT 'Document title (e.g., Sprint 15 Standup)' 
    DEFAULT NULL AFTER `filename`,
    
ADD COLUMN IF NOT EXISTS `document_type` ENUM(
    'stand_up_doc',
    'retro_summary', 
    'sprint_notes',
    'task_list',
    'meeting_notes',
    'other'
)
    COMMENT 'Type of document for categorization' 
    DEFAULT 'other' AFTER `title`,
    
ADD COLUMN IF NOT EXISTS `body` LONGTEXT 
    COMMENT 'Full document content extracted from PDF' 
    DEFAULT NULL AFTER `document_type`,
    
ADD COLUMN IF NOT EXISTS `upload_date` DATE 
    COMMENT 'Date document was uploaded (for date-based filtering)' 
    DEFAULT CURDATE() AFTER `updated_at`;

-- ============================================
-- 2. CREATE INDEXES FOR PERFORMANCE
-- ============================================

ALTER TABLE IF EXISTS `documents`
ADD INDEX IF NOT EXISTS `idx_upload_date` (`upload_date`) COMMENT 'Fast date-based queries',
ADD INDEX IF NOT EXISTS `idx_upload_date_tenant` (`tenant_name`, `upload_date`) COMMENT 'Fast date queries per tenant',
ADD INDEX IF NOT EXISTS `idx_document_type` (`document_type`) COMMENT 'Filter by document type',
ADD INDEX IF NOT EXISTS `idx_status_date` (`status`, `upload_date`) COMMENT 'Filter ready docs by date';

-- ============================================
-- 3. CREATE DOCUMENT_VECTORS TABLE
-- ============================================
-- Stores mapping between documents and vector embeddings in ChromaDB

CREATE TABLE IF NOT EXISTS `document_vectors` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT 'Unique vector record ID',
    `document_id` VARCHAR(255) NOT NULL COMMENT 'Reference to DOCUMENTS table',
    `tenant_name` VARCHAR(255) NOT NULL COMMENT 'Tenant identifier',
    `chunk_index` INT NOT NULL COMMENT 'Sequence number of this chunk',
    `chunk_text` TEXT NOT NULL COMMENT 'The actual text chunk',
    `vector_collection_id` VARCHAR(255) COMMENT 'ChromaDB collection ID for this chunk',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX `idx_document_id` (`document_id`),
    INDEX `idx_tenant` (`tenant_name`),
    INDEX `idx_collection` (`vector_collection_id`),
    FOREIGN KEY (`document_id`) REFERENCES `documents`(`document_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='Mapping between documents and vector embeddings';

-- ============================================
-- 4. UPDATE EXISTING DOCUMENTS
-- ============================================
-- Set upload_date to current date for existing documents
-- This ensures they appear in the date picker

UPDATE `documents` 
SET `upload_date` = DATE(`created_at`)
WHERE `upload_date` IS NULL AND `status` = 'ready';

-- ============================================
-- 5. VERIFY CHANGES
-- ============================================

-- Show new DOCUMENTS table structure
DESCRIBE `documents`;

-- Count indexed columns
SELECT 
    TABLE_NAME,
    INDEX_NAME,
    COLUMN_NAME
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'documents'
ORDER BY INDEX_NAME, SEQ_IN_INDEX;

-- Show DOCUMENT_VECTORS table structure
DESCRIBE `document_vectors`;

-- ============================================
-- 6. NOTES
-- ============================================
-- 
-- Document Types (Enum values):
-- - stand_up_doc: Daily standup notes
-- - retro_summary: Retrospective summary
-- - sprint_notes: Sprint planning/review notes
-- - task_list: Task or ticket lists
-- - meeting_notes: Meeting minutes
-- - other: Any other document type
--
-- Upload Date Index: Optimizes queries like:
--   SELECT * FROM documents WHERE upload_date = '2025-01-15'
--   SELECT DISTINCT upload_date FROM documents
--
-- Composite Index: Optimizes tenant-specific date queries:
--   SELECT * FROM documents WHERE tenant_name = 'xyz' AND upload_date = '2025-01-15'
--
-- ============================================
