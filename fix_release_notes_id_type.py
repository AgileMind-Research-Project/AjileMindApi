
import asyncio
from app.db.database import db
from app.core.logger import logger

async def fix_release_notes_schema():
    """
    Fixes the release_notes table schema by changing user ID columns from INT to VARCHAR(255).
    """
    try:
        # Initialize database pool
        await db.connect()
        logger.info("Database connected")
        
        # Get all tenant databases
        logger.info("Fetching tenant databases...")
        databases = await db.execute_query("SHOW DATABASES", fetch_all=True)
        
        ignored_dbs = {'information_schema', 'mysql', 'performance_schema', 'sys'}
        
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
                
            logger.info(f"Fixing release_notes table in {tenant_db}...")
            
            try:
                # Alter created_by column
                alter_created_by = f"""
                    ALTER TABLE `{tenant_db}`.release_notes 
                    MODIFY COLUMN `created_by` VARCHAR(255) NOT NULL COMMENT 'User ID of creator (must be PROJECT_MANAGER)'
                """
                await db.execute_query(alter_created_by, commit=True)
                logger.info(f"Updated created_by column in {tenant_db}")
                
                # Alter published_by column
                alter_published_by = f"""
                    ALTER TABLE `{tenant_db}`.release_notes 
                    MODIFY COLUMN `published_by` VARCHAR(255) NULL COMMENT 'User ID who published the release note'
                """
                await db.execute_query(alter_published_by, commit=True)
                logger.info(f"Updated published_by column in {tenant_db}")
                
            except Exception as e:
                logger.error(f"Error updating {tenant_db}: {e}")
        
        logger.info("Schema fix completed successfully")
        
    except Exception as e:
        logger.error(f"Schema fix failed: {e}")
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(fix_release_notes_schema())
