import pymysql

DB_HOST = "ballast.proxy.rlwy.net"
DB_PORT = 58607
DB_USER = "root"
DB_PASSWORD = "CtBeFkVkJSUcybwQFvevXGaOMspvxDHZ"

print("=" * 60)
print("COMPREHENSIVE VERIFICATION - RELEASE NOTE BUILDER")
print("=" * 60)

try:
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cursor = conn.cursor()
    
    # Check all tenant databases
    cursor.execute("SHOW DATABASES")
    databases = [row[0] for row in cursor.fetchall()]
    tenant_dbs = [db for db in databases if db not in 
                  ['information_schema', 'mysql', 'performance_schema', 'sys', 'railway', 'agilemind_db']]
    
    print(f"\n✅ Found {len(tenant_dbs)} tenant databases")
    
    table_status = {}
    for db_name in tenant_dbs:
        cursor.execute(f"USE `{db_name}`")
        cursor.execute("SHOW TABLES LIKE 'release_notes'")
        exists = cursor.fetchone() is not None
        table_status[db_name] = exists
        
        if exists:
            # Get column count
            cursor.execute("DESCRIBE release_notes")
            columns = cursor.fetchall()
            print(f"   ✅ {db_name}: release_notes table exists ({len(columns)} columns)")
        else:
            print(f"   ❌ {db_name}: release_notes table MISSING")
    
    # Detailed check for sliit database
    print(f"\n{'=' * 60}")
    print("DETAILED SCHEMA CHECK (sliit database)")
    print("=" * 60)
    
    cursor.execute("USE sliit")
    cursor.execute("DESCRIBE release_notes")
    columns = cursor.fetchall()
    
    expected_columns = [
        'id', 'project_id', 'version', 'title', 'release_date',
        'release_type', 'content', 'summary', 'status', 
        'created_by', 'created_at', 'updated_at', 'published_at', 'published_by'
    ]
    
    actual_columns = [col[0] for col in columns]
    
    print(f"\nExpected columns: {len(expected_columns)}")
    print(f"Actual columns:   {len(actual_columns)}")
    
    for col in expected_columns:
        if col in actual_columns:
            print(f"   ✅ {col}")
        else:
            print(f"   ❌ {col} MISSING")
    
    # Check foreign key
    cursor.execute("SHOW CREATE TABLE release_notes")
    create_statement = cursor.fetchone()[1]
    
    if 'FOREIGN KEY' in create_statement and 'project_id' in create_statement:
        print(f"\n✅ Foreign key constraint exists (project_id → projects)")
    else:
        print(f"\n❌ Foreign key constraint MISSING")
    
    # Check for any existing data
    cursor.execute("SELECT COUNT(*) FROM release_notes")
    count = cursor.fetchone()[0]
    print(f"\n📊 Current release notes count: {count}")
    
    cursor.close()
    conn.close()
    
    print(f"\n{'=' * 60}")
    print("✅ DATABASE VERIFICATION COMPLETE")
    print("=" * 60)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
