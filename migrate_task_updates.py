"""
Migration script to add task_updates table to existing tenant databases
"""

import asyncio
from app.db.database import Database
from app.core.config import settings

async def apply_task_updates_migration():
    db = Database()
    await db.connect()
    
    tenants = ['sliit', 'example', 'visionexdigital']
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS `task_updates` (
        `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
        `meeting_id` VARCHAR(50) NOT NULL COMMENT 'Reference to meetings table',
        `ticket_id` VARCHAR(50) NOT NULL COMMENT 'Jira ticket ID (e.g., API-400, BUG-102)',
        `task_id` INT NULL COMMENT 'Reference to task table if matched',
        `project_id` BIGINT NOT NULL COMMENT 'Project this task belongs to',
        
        -- AI Extracted Data
        `detected_status` ENUM('TODO', 'IN_PROGRESS', 'DONE', 'BLOCKED') NOT NULL COMMENT 'Status detected by AI',
        `blocker_description` TEXT NULL COMMENT 'Blocker details if status is BLOCKED',
        `ai_confidence_score` DECIMAL(3,2) DEFAULT 0.00 COMMENT 'AI confidence (0.00-1.00)',
        `ai_reasoning` TEXT NULL COMMENT 'Chain of Thought reasoning from AI',
        `extracted_context` TEXT NULL COMMENT 'Relevant excerpt from transcript',
        
        -- Approval Workflow
        `approval_status` ENUM('PENDING', 'APPROVED', 'REJECTED') DEFAULT 'PENDING',
        `reviewed_by` VARCHAR(100) NULL COMMENT 'User who reviewed',
        `review_timestamp` DATETIME NULL,
        `reviewer_remark` TEXT NULL COMMENT 'Optional remark from reviewer',
        
        -- Jira Integration
        `jira_sync_status` ENUM('NOT_SYNCED', 'SYNCED', 'FAILED') DEFAULT 'NOT_SYNCED',
        `jira_sync_timestamp` DATETIME NULL,
        `jira_error_message` TEXT NULL,
        
        -- Metadata
        `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        
        -- Indexes
        INDEX `idx_meeting_id` (`meeting_id`),
        INDEX `idx_ticket_id` (`ticket_id`),
        INDEX `idx_project_id` (`project_id`),
        INDEX `idx_approval_status` (`approval_status`),
        INDEX `idx_jira_sync_status` (`jira_sync_status`),
        
        -- Foreign Keys
        CONSTRAINT `fk_task_updates_meeting`
            FOREIGN KEY (`meeting_id`)
            REFERENCES `meetings` (`meeting_id`)
            ON UPDATE CASCADE
            ON DELETE CASCADE,
        
        CONSTRAINT `fk_task_updates_project`
            FOREIGN KEY (`project_id`)
            REFERENCES `projects` (`project_id`)
            ON UPDATE CASCADE
            ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI-extracted task updates with approval workflow';
    """
    
    for tenant in tenants:
        print(f"Processing tenant: {tenant}")
        try:
            check_meetings = f"SELECT 1 FROM information_schema.tables WHERE table_schema = '{tenant}' AND table_name = 'meetings'"
            meetings_exists = await db.execute_query(check_meetings, fetch_one=True)
            
            if not meetings_exists:
                print(f"  Skipping {tenant}: meetings table does not exist")
                continue
            
            check_table = f"SELECT 1 FROM information_schema.tables WHERE table_schema = '{tenant}' AND table_name = 'task_updates'"
            table_exists = await db.execute_query(check_table, fetch_one=True)
            
            if table_exists:
                print(f"  task_updates table already exists in {tenant}")
            else:
                print(f"  Creating task_updates table in {tenant}...")
                await db.execute_query(f"USE `{tenant}`")
                await db.execute_query(create_table_sql, commit=True)
                print(f"  ✓ Successfully created task_updates table in {tenant}")
        
        except Exception as e:
            print(f"  ✗ Error processing {tenant}: {e}")
            continue
    
    await db.execute_query(f"USE `{settings.DB_NAME}`")
    await db.disconnect()
    print("\n✓ Migration completed!")

if __name__ == "__main__":
    asyncio.run(apply_task_updates_migration())
