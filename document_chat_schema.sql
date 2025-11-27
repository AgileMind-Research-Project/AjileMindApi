-- ============================================
-- DOCUMENT CHAT FEATURE - DATABASE SCHEMA
-- Add these tables to support PDF upload and RAG-based chat
-- ============================================

USE agilemind_db;

-- ============================================
-- 1. DOCUMENTS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS DOCUMENTS (
    DOCUMENT_ID VARCHAR(50) PRIMARY KEY COMMENT 'Unique document identifier',
    TENANT_ID VARCHAR(50) NOT NULL COMMENT 'Tenant who owns this document',
    USER_ID VARCHAR(50) NOT NULL COMMENT 'User who uploaded the document',
    FILENAME VARCHAR(255) NOT NULL COMMENT 'Original filename',
    FILE_SIZE INT NOT NULL COMMENT 'File size in bytes',
    TOTAL_CHUNKS INT NOT NULL COMMENT 'Number of text chunks generated',
    STATUS ENUM('processing', 'ready', 'failed') DEFAULT 'processing' COMMENT 'Processing status',
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Upload timestamp',
    UPDATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    
    FOREIGN KEY (TENANT_ID) REFERENCES TENANTS(TENANT_ID) ON DELETE CASCADE,
    FOREIGN KEY (USER_ID) REFERENCES USERS(USER_ID) ON DELETE CASCADE,
    INDEX IDX_TENANT (TENANT_ID),
    INDEX IDX_USER (USER_ID),
    INDEX IDX_STATUS (STATUS),
    INDEX IDX_CREATED (CREATED_AT)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Uploaded PDF documents metadata';

-- ============================================
-- 2. CHAT_HISTORY TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS CHAT_HISTORY (
    CHAT_ID VARCHAR(50) PRIMARY KEY COMMENT 'Unique chat entry identifier',
    TENANT_ID VARCHAR(50) NOT NULL COMMENT 'Tenant context',
    USER_ID VARCHAR(50) NOT NULL COMMENT 'User who asked the question',
    QUESTION TEXT NOT NULL COMMENT 'User question',
    ANSWER TEXT NOT NULL COMMENT 'LLM generated answer',
    SOURCES JSON COMMENT 'Source document references',
    MODEL VARCHAR(50) COMMENT 'LLM model used',
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Chat timestamp',
    
    FOREIGN KEY (TENANT_ID) REFERENCES TENANTS(TENANT_ID) ON DELETE CASCADE,
    FOREIGN KEY (USER_ID) REFERENCES USERS(USER_ID) ON DELETE CASCADE,
    INDEX IDX_TENANT (TENANT_ID),
    INDEX IDX_USER (USER_ID),
    INDEX IDX_CREATED (CREATED_AT)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Chat history for document Q&A';

-- ============================================
-- VERIFICATION
-- ============================================
SELECT 'Document Chat tables created successfully!' AS status;

-- Check tables
SHOW TABLES LIKE '%DOCUMENT%' OR TABLES LIKE '%CHAT%';

-- Describe new tables
DESCRIBE DOCUMENTS;
DESCRIBE CHAT_HISTORY;
