
import asyncio
import os
import sys

# Add the project root to sys.path to import app modules
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

from app.db.database import db
from app.core.logger import logger
from app.core.config import settings

async def migrate_release_notes_sprints():
    """
    Migration to remove sprint_duration and add start_sprint and end_sprint columns.
    """
    try:
        # Initialize database pool
        await db.connect()
        logger.info("Database connected")
        
        # Get all tenant databases
        logger.info("Fetching tenant databases...")
        # aiomysql result is list of dicts with DictCursor
        databases = await db.execute_query("SHOW DATABASES", fetch_all=True)
        
        ignored_dbs = {'information_schema', 'mysql', 'performance_schema', 'sys', 'railway', 'agilemind_db'}
        
        for db_record in databases:
            tenant_db = db_record['Database']
            if tenant_db in ignored_dbs:
                continue
                
            logger.info(f"Checking database: {tenant_db}")
            
            # Check if release_notes table exists
            table_check = await db.execute_query(
                f"SELECT COUNT(*) as count FROM information_schema.tables WHERE table_schema = '{tenant_db}' AND table_name = 'release_notes'",
                fetch_one=True
            )
            
            if not table_check or table_check['count'] == 0:
                logger.info(f"Skipping {tenant_db} - release_notes table not found")
                continue
                
            logger.info(f"Updating release_notes table in {tenant_db}...")
            
            try:
                # 1. Check if sprint_duration exists
                col_check = await db.execute_query(
                    f"SHOW COLUMNS FROM `{tenant_db}`.release_notes LIKE 'sprint_duration'",
                    fetch_one=True
                )
                
                if col_check:
                    logger.info(f"Dropping sprint_duration from {tenant_db}")
                    await db.execute_query(f"ALTER TABLE `{tenant_db}`.release_notes DROP COLUMN `sprint_duration` ", commit=True)
                
                # 2. Add start_sprint and end_sprint
                # Check if they already exist first to avoid errors
                cols = await db.execute_query(f"SHOW COLUMNS FROM `{tenant_db}`.release_notes", fetch_all=True)
                col_names = [c['Field'] for c in cols]
                
                if 'start_sprint' not in col_names:
                    logger.info(f"Adding start_sprint to {tenant_db}")
                    await db.execute_query(f"ALTER TABLE `{tenant_db}`.release_notes ADD COLUMN `start_sprint` INT NULL AFTER `release_type` ", commit=True)
                
                if 'end_sprint' not in col_names:
                    logger.info(f"Adding end_sprint to {tenant_db}")
                    await db.execute_query(f"ALTER TABLE `{tenant_db}`.release_notes ADD COLUMN `end_sprint` INT NULL AFTER `start_sprint` ", commit=True)
                
                logger.info(f"Successfully updated release_notes in {tenant_db}")
                
            except Exception as e:
                logger.error(f"Error updating {tenant_db}: {e}")
        
        logger.info("Migration completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(migrate_release_notes_sprints())
