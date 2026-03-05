"""
Migration: Make transcript_id nullable in reports table

This allows documents to be uploaded directly without requiring a transcript.
"""

import asyncio
import sys
sys.path.insert(0, 'c:\\Users\\Lahiru\\Desktop\\Research project\\imp\\AjileMindApi')

from app.db.database import db


async def migrate():
    """Make transcript_id nullable in all tenant databases"""
    await db.connect()
    try:
        # Get all tenant databases
        results = await db.execute_query(
            "SHOW DATABASES LIKE %s", 
            ("tenant_%",), 
            fetch_all=True
        )
        tenant_dbs = [list(r.values())[0] for r in results]
        print(f"Found {len(tenant_dbs)} tenant databases")
        
        for tenant_db in tenant_dbs:
            try:
                # Alter the reports table to make transcript_id nullable
                await db.execute_query(
                    "ALTER TABLE reports MODIFY COLUMN transcript_id INT NULL",
                    commit=True,
                    schema=tenant_db
                )
                print(f"✓ Updated {tenant_db}")
            except Exception as e:
                print(f"✗ Error updating {tenant_db}: {e}")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(migrate())
