"""
Database Auto-Migration Module

Automatically applies required migrations when the application starts.
Handles adding missing columns for document chat feature.
"""

import aiomysql
from typing import Optional, List
from app.core.logger import logger
from app.core.config import settings


class DatabaseMigration:
    """Handle auto-migrations for database schema"""
    
    @staticmethod
    async def run_migrations(pool: aiomysql.Pool) -> bool:
        """
        Run all required database migrations.
        Safe to run multiple times - uses IF NOT EXISTS/IF EXISTS patterns.
        
        Args:
            pool: Database connection pool
            
        Returns:
            True if migrations successful, False otherwise
        """
        try:
            logger.info("Starting database migrations...")
            
            # List of migrations to apply
            migrations = [
                DatabaseMigration._create_documents_table_migration,
                DatabaseMigration._add_document_columns_migration,
                DatabaseMigration._create_document_vectors_table_migration,
                DatabaseMigration._create_jira_integration_table_migration,
            ]
            
            # Execute each migration
            for migration_func in migrations:
                await migration_func(pool)
            
            logger.info("All database migrations completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database migration failed: {e}")
            return False
    
    @staticmethod
    async def _create_documents_table_migration(pool: aiomysql.Pool) -> None:
        """
        Create DOCUMENTS table if it doesn't exist.
        This is the base table for all document chat functionality.
        """
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("""
                        CREATE TABLE IF NOT EXISTS `documents` (
                            `document_id` VARCHAR(255) PRIMARY KEY COMMENT 'Unique document identifier',
                            `TENANT_NAME` VARCHAR(255) NOT NULL COMMENT 'Tenant/Domain identifier',
                            `user_id` VARCHAR(255) NOT NULL COMMENT 'User who uploaded the document',
                            `filename` VARCHAR(255) NOT NULL COMMENT 'Original filename',
                            `file_size` BIGINT DEFAULT 0 COMMENT 'File size in bytes',
                            `title` VARCHAR(255) DEFAULT NULL COMMENT 'Document title',
                            `document_type` ENUM(
                                'stand_up_doc',
                                'retro_summary',
                                'sprint_notes',
                                'task_list',
                                'meeting_notes',
                                'other'
                            ) DEFAULT 'other' COMMENT 'Document category',
                            `body` LONGTEXT DEFAULT NULL COMMENT 'Full document content',
                            `upload_date` DATE DEFAULT NULL COMMENT 'Upload date for filtering',
                            `total_chunks` INT DEFAULT 0 COMMENT 'Number of text chunks created',
                            `status` ENUM('processing', 'ready', 'error', 'archived') DEFAULT 'processing' COMMENT 'Document processing status',
                            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp',
                            `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
                            
                            INDEX `idx_tenant` (`TENANT_NAME`),
                            INDEX `idx_user` (`user_id`),
                            INDEX `idx_status` (`status`),
                            INDEX `idx_upload_date` (`upload_date`),
                            INDEX `idx_document_type` (`document_type`),
                            INDEX `idx_tenant_date` (`TENANT_NAME`, `upload_date`),
                            INDEX `idx_tenant_status` (`TENANT_NAME`, `status`)
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
                        COMMENT='Documents uploaded by users for RAG-based chat'
                    """)
                    
                    await conn.commit()
                    logger.info("Migration: Created DOCUMENTS table")
                    
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("DOCUMENTS table already exists")
            else:
                logger.error(f"Migration failed - create_documents_table: {e}")
                raise
    
    @staticmethod
    async def _add_document_columns_migration(pool: aiomysql.Pool) -> None:
        """
        Add new columns to DOCUMENTS table:
        - TITLE: Document title
        - DOCUMENT_TYPE: Type enum
        - BODY: Full text content
        - UPLOAD_DATE: Upload date for filtering
        """
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # Add TITLE column
                    try:
                        await cursor.execute("""
                            ALTER TABLE `documents`
                            ADD COLUMN `title` VARCHAR(255) DEFAULT NULL COMMENT 'Document title'
                        """)
                        logger.info("[OK] Added TITLE column to documents")
                    except Exception as e:
                        if "Duplicate column name" in str(e):
                            logger.info("[INFO] TITLE column already exists")
                        else:
                            raise
                    
                    # Add DOCUMENT_TYPE column
                    try:
                        await cursor.execute("""
                            ALTER TABLE `documents`
                            ADD COLUMN `document_type` ENUM(
                                'stand_up_doc',
                                'retro_summary',
                                'sprint_notes',
                                'task_list',
                                'meeting_notes',
                                'other'
                            ) DEFAULT 'other' COMMENT 'Document type for categorization'
                        """)
                        logger.info("[OK] Added DOCUMENT_TYPE column to documents")
                    except Exception as e:
                        if "Duplicate column name" in str(e):
                            logger.info("[INFO] DOCUMENT_TYPE column already exists")
                        else:
                            raise
                    
                    # Add BODY column
                    try:
                        await cursor.execute("""
                            ALTER TABLE `documents`
                            ADD COLUMN `body` LONGTEXT DEFAULT NULL COMMENT 'Full document content'
                        """)
                        logger.info("[OK] Added BODY column to documents")
                    except Exception as e:
                        if "Duplicate column name" in str(e):
                            logger.info("[INFO] BODY column already exists")
                        else:
                            raise
                    
                    # Add UPLOAD_DATE column
                    try:
                        await cursor.execute("""
                            ALTER TABLE `documents`
                            ADD COLUMN `upload_date` DATE DEFAULT NULL COMMENT 'Upload date for filtering'
                        """)
                        logger.info("[OK] Added UPLOAD_DATE column to documents")
                    except Exception as e:
                        if "Duplicate column name" in str(e):
                            logger.info("[INFO] UPLOAD_DATE column already exists")
                        else:
                            raise
                    
                    # Create indexes (skip if they already exist)
                    try:
                        await cursor.execute("""
                            ALTER TABLE `documents` ADD INDEX `idx_upload_date` (`upload_date`)
                        """)
                        logger.info("[OK] Created index idx_upload_date")
                    except:
                        pass
                    
                    try:
                        await cursor.execute("""
                            ALTER TABLE `documents` ADD INDEX `idx_upload_date_tenant` (`tenant_name`, `upload_date`)
                        """)
                        logger.info("[OK] Created index idx_upload_date_tenant")
                    except:
                        pass
                    
                    try:
                        await cursor.execute("""
                            ALTER TABLE `documents` ADD INDEX `idx_document_type` (`document_type`)
                        """)
                        logger.info("[OK] Created index idx_document_type")
                    except:
                        pass
                    
                    try:
                        await cursor.execute("""
                            ALTER TABLE `documents` ADD INDEX `idx_status_date` (`status`, `upload_date`)
                        """)
                        logger.info("[OK] Created index idx_status_date")
                    except:
                        pass
                    
                    await conn.commit()
                    logger.info("[OK] Migration: Added document chat columns (TITLE, DOCUMENT_TYPE, BODY, UPLOAD_DATE)")
                    
        except Exception as e:
            logger.error(f"Migration failed - add_document_columns: {e}")
            raise
    
    @staticmethod
    async def _create_document_vectors_table_migration(pool: aiomysql.Pool) -> None:
        """
        Create DOCUMENT_VECTORS table for mapping documents to vector embeddings.
        """
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("""
                        CREATE TABLE IF NOT EXISTS `document_vectors` (
                            `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT 'Unique vector record ID',
                            `document_id` VARCHAR(255) NOT NULL COMMENT 'Reference to DOCUMENTS table',
                            `tenant_name` VARCHAR(255) NOT NULL COMMENT 'Tenant identifier',
                            `chunk_index` INT NOT NULL COMMENT 'Sequence number of chunk',
                            `chunk_text` TEXT NOT NULL COMMENT 'The actual text chunk',
                            `vector_collection_id` VARCHAR(255) COMMENT 'ChromaDB collection ID',
                            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            
                            INDEX `idx_document_id` (`document_id`),
                            INDEX `idx_tenant` (`tenant_name`),
                            INDEX `idx_collection` (`vector_collection_id`),
                            FOREIGN KEY (`document_id`) REFERENCES `documents`(`document_id`) 
                                ON DELETE CASCADE
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
                        COMMENT='Vector embeddings mapping table'
                    """)
                    
                    await conn.commit()
                    logger.info("[OK] Migration: Created DOCUMENT_VECTORS table")
                    
        except Exception as e:
            logger.error(f"Migration failed - create_document_vectors_table: {e}")
            raise
    
    @staticmethod
    async def _create_jira_integration_table_migration(pool: aiomysql.Pool) -> None:
        """
        Create JIRA_INTEGRATIONS table in tenant database.
        """
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("""
                        CREATE TABLE IF NOT EXISTS `jira_integrations` (
                            `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT 'Unique ID',
                            `jira_url` VARCHAR(255) NOT NULL COMMENT 'Jira instance URL',
                            `email` VARCHAR(255) NOT NULL COMMENT 'Jira account email',
                            `api_token` VARCHAR(255) NOT NULL COMMENT 'Jira API token (encrypted)',
                            `is_active` BOOLEAN DEFAULT TRUE COMMENT 'Integration is active',
                            `last_sync` TIMESTAMP NULL COMMENT 'Last sync timestamp',
                            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            
                            UNIQUE KEY `uq_jira_account` (`jira_url`, `email`),
                            INDEX `idx_jira_url` (`jira_url`),
                            INDEX `idx_is_active` (`is_active`)
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
                        COMMENT='Jira integration configuration'
                    """)
                    
                    await conn.commit()
                    logger.info("[OK] Migration: Created JIRA_INTEGRATIONS table")
                    
        except Exception as e:
            logger.error(f"Migration failed - create_jira_integration_table: {e}")
            raise
