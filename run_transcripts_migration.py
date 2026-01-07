"""
Run Transcripts Migration

Executes the SQL migration to create transcripts, reports, and report_templates tables.
"""

import os
import sys
import asyncio
import aiomysql
from dotenv import load_dotenv

# Add app directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Load environment variables
load_dotenv()


async def run_migration():
    """Run the transcripts migration"""
    
    # Database connection parameters from .env
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 3306)),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'db': os.getenv('DB_NAME', 'ajilemind'),
        'charset': 'utf8mb4',
        'autocommit': True
    }
    
    print(f"Connecting to database: {db_config['host']}:{db_config['port']}/{db_config['db']}")
    
    try:
        # Read SQL file
        sql_file_path = os.path.join(os.path.dirname(__file__), 'migrations', 'create_transcripts_tables.sql')
        
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        # Connect to database
        connection = await aiomysql.connect(**db_config)
        
        try:
            cursor = await connection.cursor()
            
            # Split SQL script into individual statements
            statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip()]
            
            print(f"\nExecuting {len(statements)} SQL statements...\n")
            
            for i, statement in enumerate(statements, 1):
                if statement:
                    # Get statement type
                    stmt_type = statement.split()[0].upper()
                    print(f"[{i}/{len(statements)}] Executing {stmt_type} statement...")
                    
                    try:
                        await cursor.execute(statement)
                        print(f"✓ Success")
                    except Exception as e:
                        print(f"✗ Error: {e}")
                        raise
            
            await connection.commit()
            print("\n✓ Migration completed successfully!")
            
            # Verify tables created
            await cursor.execute("SHOW TABLES LIKE 'transcripts'")
            transcripts_exists = await cursor.fetchone()
            
            await cursor.execute("SHOW TABLES LIKE 'reports'")
            reports_exists = await cursor.fetchone()
            
            await cursor.execute("SHOW TABLES LIKE 'report_templates'")
            templates_exists = await cursor.fetchone()
            
            print("\nVerification:")
            print(f"  - transcripts table: {'✓ Created' if transcripts_exists else '✗ Not found'}")
            print(f"  - reports table: {'✓ Created' if reports_exists else '✗ Not found'}")
            print(f"  - report_templates table: {'✓ Created' if templates_exists else '✗ Not found'}")
            
            await cursor.close()
        
        finally:
            connection.close()
    
    except FileNotFoundError:
        print(f"Error: SQL migration file not found at {sql_file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error running migration: {e}")
        sys.exit(1)


if __name__ == '__main__':
    print("=" * 60)
    print("Transcripts & Reports Migration")
    print("=" * 60)
    print()
    
    asyncio.run(run_migration())
