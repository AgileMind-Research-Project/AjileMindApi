
import asyncio
import aiomysql
import os
import sys
from dotenv import load_dotenv

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

async def run():
    print("Starting migration to add project_id to transcripts...")
    try:
        conn = await aiomysql.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 3306)),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            autocommit=True
        )
        cursor = await conn.cursor()
        
        # Target schemas - in a real scenario we might fetch these from a registry
        # For now, we target 'sliit' which is the active one in logs
        schemas = ['sliit'] 
        
        for schema in schemas:
            print(f"Migrating schema: {schema}")
            try:
                # Check if table exists
                await cursor.execute(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '{schema}' AND table_name = 'transcripts'")
                (count,) = await cursor.fetchone()
                
                if count == 0:
                    print(f"Skipping {schema}, transcripts table not found.")
                    continue

                # Add column
                try:
                    await cursor.execute(f"ALTER TABLE {schema}.transcripts ADD COLUMN project_id BIGINT DEFAULT NULL AFTER file_name")
                    print(f"Added project_id column to {schema}.transcripts")
                except Exception as e:
                    if "Duplicate column" in str(e) or "1060" in str(e):
                        print(f"Column project_id already exists in {schema}.transcripts")
                    else:
                        print(f"Error adding column to {schema}: {e}")

                # Add index
                try:
                    await cursor.execute(f"CREATE INDEX idx_project_id ON {schema}.transcripts(project_id)")
                    print(f"Added index idx_project_id to {schema}.transcripts")
                except Exception as e:
                     if "Duplicate key" in str(e) or "already exists" in str(e) or "1061" in str(e):
                         print(f"Index idx_project_id already exists in {schema}.transcripts")
                     else:
                         print(f"Error adding index to {schema}: {e}")

            except Exception as e:
                print(f"Error processing schema {schema}: {e}")
                
        await cursor.close()
        conn.close()
        print("Migration completed.")
        
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    asyncio.run(run())
