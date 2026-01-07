"""
Run transcript and reports migration on tenant schema
"""
import asyncio
import os
from dotenv import load_dotenv
import aiomysql

# Load environment variables
load_dotenv()

async def run_migration():
    """Run the migration on the visionexdigital tenant schema"""
    
    # Database connection parameters
    db_config = {
        'host': os.getenv('DATABASE_HOST', 'ballast.proxy.rlwy.net'),
        'port': int(os.getenv('DATABASE_PORT', 58607)),
        'user': os.getenv('DATABASE_USER', 'root'),
        'password': os.getenv('DATABASE_PASSWORD'),
        'db': os.getenv('DATABASE_NAME', 'agilemind_db'),
        'charset': 'utf8mb4',
        'autocommit': False
    }
    
    tenant_schema = 'visionexdigital'
    
    print(f"Connecting to database: {db_config['host']}:{db_config['port']}/{db_config['db']}")
    print(f"Target schema: {tenant_schema}")
    
    try:
        # Connect to database
        connection = await aiomysql.connect(**db_config)
        cursor = await connection.cursor()
        
        # Read migration file
        migration_file = 'migrations/create_transcripts_tables.sql'
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Replace table names with schema-qualified names
        # This assumes tables without schema prefix
        tables_to_replace = ['transcripts', 'reports', 'report_templates']
        
        modified_sql = sql_content
        for table in tables_to_replace:
            # Replace DROP statements
            modified_sql = modified_sql.replace(
                f'DROP TABLE IF EXISTS {table}',
                f'DROP TABLE IF EXISTS {tenant_schema}.{table}'
            )
            # Replace CREATE TABLE statements
            modified_sql = modified_sql.replace(
                f'CREATE TABLE {table}',
                f'CREATE TABLE {tenant_schema}.{table}'
            )
            # Replace FOREIGN KEY REFERENCES
            modified_sql = modified_sql.replace(
                f'REFERENCES {table}(',
                f'REFERENCES {tenant_schema}.{table}('
            )
            # Replace INSERT INTO statements
            modified_sql = modified_sql.replace(
                f'INSERT INTO {table}',
                f'INSERT INTO {tenant_schema}.{table}'
            )
        
        print("\n=== Modified SQL ===")
        print(modified_sql[:500] + "...\n")
        
        # Split SQL into individual statements
        statements = [s.strip() for s in modified_sql.split(';') if s.strip()]
        
        print(f"Executing {len(statements)} SQL statements...")
        
        for i, statement in enumerate(statements, 1):
            if statement:
                try:
                    print(f"\n[{i}/{len(statements)}] Executing: {statement[:80]}...")
                    await cursor.execute(statement)
                    await connection.commit()
                    print(f"✅ Statement {i} executed successfully")
                except Exception as e:
                    print(f"❌ Error in statement {i}: {e}")
                    print(f"Statement: {statement[:200]}")
                    await connection.rollback()
                    # Continue with other statements
        
        print("\n" + "="*60)
        print("Migration completed!")
        print("="*60)
        
        # Verify tables exist
        await cursor.execute(f"SHOW TABLES FROM {tenant_schema} LIKE '%transcript%' OR LIKE '%report%'")
        tables = await cursor.fetchall()
        print(f"\n✅ Tables created in {tenant_schema} schema:")
        for table in tables:
            print(f"   - {table[0]}")
        
        await cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(run_migration())
