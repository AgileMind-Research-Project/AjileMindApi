
import asyncio
from app.db.database import Database
from app.core.config import settings

async def apply_schema_update():
    db = Database()
    await db.connect()
    
    # Get all tenant databases
    # We assume tenant databases are named in a specific way or we just iterate known ones. 
    # For now, let's query the 'projects' or similar to find tenants or just use a hardcoded list if known, 
    # but better: query information_schema or just iterate the ones we know: 'sliit', 'example', 'visionexdigital'
    # Actually, we can just try to run it on `sliit` since that's what the user is using.
    # But let's try to be generic. 
    
    # Simplified: specific tenants the user mentioned
    tenants = ['sliit', 'example', 'visionexdigital'] 
    
    for tenant in tenants:
        print(f"Checking tenant: {tenant}")
        try:
            # Check if table exists
            check_table = f"SELECT 1 FROM information_schema.tables WHERE table_schema = '{tenant}' AND table_name = 'meetings'"
            table_exists = await db.execute_query(check_table, fetch_one=True)
            
            if table_exists:
                print(f"Updating 'meetings' table in {tenant}...")
                
                check_col = f"SELECT 1 FROM information_schema.columns WHERE table_schema = '{tenant}' AND table_name = 'meetings' AND column_name = 'attendees'"
                col_exists = await db.execute_query(check_col, fetch_one=True)
                
                if not col_exists:
                    alter_query = f"ALTER TABLE `{tenant}`.`meetings` ADD COLUMN `attendees` JSON NULL COMMENT 'List of meeting attendees'"
                    await db.execute_query(alter_query, commit=True)
                    print(f"Added 'attendees' column to {tenant}.meetings")
                else:
                    print(f"'attendees' column already exists in {tenant}.meetings")
            else:
                print(f"Table 'meetings' not found in {tenant}. Skipping.")
                
        except Exception as e:
            print(f"Error processing {tenant}: {e}")
            
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(apply_schema_update())
