import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from app.db.database import Database
from app.core.config import settings

async def update_schema():
    print(f"Connecting to database {settings.DB_NAME} at {settings.DB_HOST}...")
    db = Database()
    await db.connect()
    
    # Check if table 'downtime_notifications' exists
    check_table_query = "SHOW TABLES LIKE 'downtime_notifications'"
    result = await db.execute_query(check_table_query, fetch_all=True)
    
    if result:
        print("Table 'downtime_notifications' found. Attempting to add column 'scheduled_at'...")
        query = """
        ALTER TABLE downtime_notifications 
        ADD COLUMN scheduled_at DATETIME NULL COMMENT 'When the notification is scheduled to be sent';
        """
        try:
            await db.execute_query(query, commit=True)
            print("Successfully added 'scheduled_at' column.")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("Column 'scheduled_at' already exists.")
            else:
                print(f"Error updating schema: {e}")
    else:
        print("Table 'downtime_notifications' does NOT exist. Creating table...")
        # Create table WITHOUT Foreign Key to projects to avoid dependency issues if projects table is missing in this context
        create_query = """
        CREATE TABLE IF NOT EXISTS `downtime_notifications` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `type` ENUM('PLANNED_MAINTENANCE', 'EMERGENCY_OUTAGE', 'FEATURE_UPGRADE', 'SERVICE_DEGRADATION') NOT NULL,
            `priority` ENUM('HIGH', 'MEDIUM', 'LOW') NOT NULL DEFAULT 'MEDIUM',
            `affected_components` JSON NOT NULL COMMENT 'List of affected services',
            `start_time` DATETIME NOT NULL,
            `end_time` DATETIME NOT NULL,
            `timezone` VARCHAR(50) DEFAULT 'UTC',
            `subject` VARCHAR(255) NOT NULL,
            `message_body` TEXT NOT NULL,
            `audience` ENUM('ALL_USERS', 'INTERNAL_TEAM', 'PROJECT_MEMBERS', 'ADMINS') NOT NULL,
            `project_id` BIGINT NULL COMMENT 'If audience is PROJECT_MEMBERS',
            `sent_by_user_id` VARCHAR(50) NULL COMMENT 'Admin/User ID who sent it',
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            `scheduled_at` DATETIME NULL COMMENT 'When the notification is scheduled to be sent',
            INDEX `idx_type` (`type`),
            INDEX `idx_start_time` (`start_time`),
            INDEX `idx_project_id` (`project_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='History of system downtime and maintenance notifications';
        """
        try:
            await db.execute_query(create_query, commit=True)
            print("Successfully created 'downtime_notifications' table with 'scheduled_at' column (FK omitted).")
        except Exception as e:
            print(f"Error creating table: {e}")

    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(update_schema())
