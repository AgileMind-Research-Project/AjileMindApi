-- Migration: Add Documents Table for RAG-based Chatbot
-- Description: Creates documents table to store document content for RAG (Retrieval Augmented Generation) based chatbot
-- Date: 2025-12-22

CREATE TABLE IF NOT EXISTS documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    doc_title VARCHAR(255) NOT NULL COMMENT 'Title of the document',
    doc_content LONGTEXT NOT NULL COMMENT 'Complete document content for RAG context',
    uploaded_date DATE NOT NULL COMMENT 'Date when document was uploaded',
    category VARCHAR(100) COMMENT 'Optional category for document classification',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    is_active BOOLEAN DEFAULT TRUE COMMENT 'Soft delete flag',
    
    -- Indexes for performance
    INDEX idx_uploaded_date (uploaded_date),
    INDEX idx_category (category),
    INDEX idx_created_at (created_at),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Table for storing documents used in RAG-based chatbot';

-- Optional: Add tenant_id if multi-tenancy is needed
-- ALTER TABLE documents ADD COLUMN tenant_id INT NOT NULL AFTER id;
-- ALTER TABLE documents ADD FOREIGN KEY (tenant_id) REFERENCES tenants(id);
-- ALTER TABLE documents ADD INDEX idx_tenant_id (tenant_id);
