-- ============================================
-- DOCUMENT CHAT FEATURE - ENHANCED DATABASE SCHEMA
-- Date-based Document Storage with Metadata
-- ============================================
-- Updated schema to support documents indexed by date
-- with detailed metadata: title, type, body, etc.

USE agilemind_db;

-- ============================================
-- 1. DOCUMENTS TABLE (Enhanced with date-based indexing)
-- ============================================
-- Stores documents uploaded on specific dates with full metadata
-- Documents are indexed by upload_date to enable date-based filtering
-- Supports document types: stand_up_doc, retro_summary, sprint_notes, etc.

CREATE TABLE IF NOT EXISTS DOCUMENTS (
    -- Primary Keys & Identifiers
    DOCUMENT_ID VARCHAR(50) PRIMARY KEY COMMENT 'Unique document identifier (UUID)',
    TENANT_ID VARCHAR(50) NOT NULL COMMENT 'Tenant who owns this document',
    USER_ID VARCHAR(50) NOT NULL COMMENT 'User who uploaded the document',
    
    -- Document Content & Metadata
    TITLE VARCHAR(255) NOT NULL COMMENT 'Document title (e.g., "Sprint 15 Standup")',
    DOCUMENT_TYPE ENUM(
        'stand_up_doc', 
        'retro_summary', 
        'sprint_notes', 
        'meeting_notes',
        'task_summary',
        'architecture_doc',
        'other'
    ) NOT NULL DEFAULT 'other' COMMENT 'Type of document for categorization',
    
    BODY LONGTEXT NOT NULL COMMENT 'Full document body/content',
    FILENAME VARCHAR(255) NOT NULL COMMENT 'Original uploaded filename',
    FILE_SIZE INT NOT NULL COMMENT 'File size in bytes',
    
    -- Document Processing Metadata
    TOTAL_CHUNKS INT NOT NULL DEFAULT 0 COMMENT 'Number of text chunks generated for vector DB',
    STATUS ENUM('processing', 'ready', 'failed') DEFAULT 'processing' COMMENT 'Processing status for vector embeddings',
    
    -- Date-Based Indexing (Core Feature)
    UPLOAD_DATE DATE NOT NULL COMMENT 'Date document was uploaded (used for grouping)',
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp (precise time)',
    UPDATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    
    -- Relationships
    FOREIGN KEY (TENANT_ID) REFERENCES TENANTS(TENANT_ID) ON DELETE CASCADE,
    FOREIGN KEY (USER_ID) REFERENCES USERS(USER_ID) ON DELETE CASCADE,
    
    -- Indexes for performance
    INDEX IDX_TENANT (TENANT_ID),
    INDEX IDX_USER (USER_ID),
    INDEX IDX_STATUS (STATUS),
    
    -- Critical Index: Date-based filtering for dropdown
    INDEX IDX_UPLOAD_DATE (TENANT_ID, UPLOAD_DATE),
    
    -- Index for finding all documents on a specific date
    INDEX IDX_DATE_TENANT_STATUS (UPLOAD_DATE, TENANT_ID, STATUS),
    
    INDEX IDX_CREATED (CREATED_AT),
    INDEX IDX_TYPE (DOCUMENT_TYPE)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='Uploaded documents with date-based metadata for document chat feature';

-- ============================================
-- 2. DOCUMENT_VECTORS TABLE
-- ============================================
-- Links documents to vector DB chunks for retrieval
-- Used to track which chunks belong to which document

CREATE TABLE IF NOT EXISTS DOCUMENT_VECTORS (
    VECTOR_ID VARCHAR(50) PRIMARY KEY COMMENT 'Unique vector identifier',
    DOCUMENT_ID VARCHAR(50) NOT NULL COMMENT 'Reference to document',
    CHUNK_INDEX INT NOT NULL COMMENT 'Sequential chunk number within document',
    VECTOR_COLLECTION_ID VARCHAR(255) NOT NULL COMMENT 'ChromaDB collection ID reference',
    CHUNK_TEXT LONGTEXT COMMENT 'Original chunk text (for reference)',
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (DOCUMENT_ID) REFERENCES DOCUMENTS(DOCUMENT_ID) ON DELETE CASCADE,
    
    INDEX IDX_DOCUMENT (DOCUMENT_ID),
    INDEX IDX_CHUNK_INDEX (DOCUMENT_ID, CHUNK_INDEX)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='Maps document chunks to vector database entries';

-- ============================================
-- 3. CHAT_HISTORY TABLE (Enhanced to track source document)
-- ============================================
-- Stores chat messages linked to specific documents
-- Enables tracking which document was used for each answer

CREATE TABLE IF NOT EXISTS CHAT_HISTORY (
    CHAT_ID VARCHAR(50) PRIMARY KEY COMMENT 'Unique chat entry identifier',
    TENANT_ID VARCHAR(50) NOT NULL COMMENT 'Tenant context',
    USER_ID VARCHAR(50) NOT NULL COMMENT 'User who asked the question',
    
    -- Chat Content
    QUESTION TEXT NOT NULL COMMENT 'User question',
    ANSWER TEXT NOT NULL COMMENT 'LLM generated short answer',
    
    -- Source Document Tracking
    DOCUMENT_ID VARCHAR(50) COMMENT 'Document used to generate answer',
    UPLOAD_DATE DATE COMMENT 'Date of the source document',
    
    -- LLM Metadata
    SOURCES JSON COMMENT 'Source document references with context',
    MODEL VARCHAR(50) COMMENT 'LLM model used (e.g., gpt-4, claude-3)',
    RESPONSE_TIME_MS INT COMMENT 'Response generation time in milliseconds',
    
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Chat timestamp',
    
    FOREIGN KEY (TENANT_ID) REFERENCES TENANTS(TENANT_ID) ON DELETE CASCADE,
    FOREIGN KEY (USER_ID) REFERENCES USERS(USER_ID) ON DELETE CASCADE,
    FOREIGN KEY (DOCUMENT_ID) REFERENCES DOCUMENTS(DOCUMENT_ID) ON DELETE SET NULL,
    
    INDEX IDX_TENANT (TENANT_ID),
    INDEX IDX_USER (USER_ID),
    INDEX IDX_CREATED (CREATED_AT),
    
    -- Find all chats for a specific document
    INDEX IDX_DOCUMENT (DOCUMENT_ID),
    
    -- Find chats by date (supports date filtering)
    INDEX IDX_UPLOAD_DATE (UPLOAD_DATE),
    
    INDEX IDX_TENANT_DOCUMENT (TENANT_ID, DOCUMENT_ID)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='Chat history linked to specific source documents for audit trail';

-- ============================================
-- 4. VERIFICATION QUERY
-- ============================================
SELECT 
    TABLE_NAME,
    TABLE_ROWS,
    CREATE_TIME,
    TABLE_COMMENT
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'agilemind_db'
    AND TABLE_NAME IN ('DOCUMENTS', 'DOCUMENT_VECTORS', 'CHAT_HISTORY')
ORDER BY TABLE_NAME;

SELECT 'Document chat schema with date-based indexing created successfully!' as message;
