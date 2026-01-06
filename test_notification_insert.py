import pymysql
import sys
from datetime import datetime

# Database credentials from .env
DB_HOST = "ballast.proxy.rlwy.net"
DB_PORT = 58607
DB_USER = "root"
DB_PASSWORD = "CtBeFkVkJSUcybwQFvevXGaOMspvxDHZ"
TARGET_DB = "sliit"

try:
    print(f"Connecting to {DB_HOST}:{DB_PORT} as {DB_USER}...")
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        autocommit=True
    )
    print("✓ Connected successfully.\n")
    
    with conn.cursor() as cursor:
        # Check current table structure
        print("=== Current Table Structure ===")
        cursor.execute(f"""
            SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = '{TARGET_DB}' 
            AND TABLE_NAME = 'downtime_notifications'
            ORDER BY ORDINAL_POSITION
        """)
        
        columns = cursor.fetchall()
        if not columns:
            print(f"✗ Table 'downtime_notifications' does not exist in database '{TARGET_DB}'!")
            print("\nYou need to create the table first. Run the tenant_database_schema.sql script.")
            sys.exit(1)
        
        print(f"Table has {len(columns)} columns:")
        for col in columns:
            nullable = "NULL" if col[2] == "YES" else "NOT NULL"
            default = f"DEFAULT {col[3]}" if col[3] else ""
            print(f"  {col[0]:<20} {col[1]:<30} {nullable:<10} {default}")
        
        # Test insert query (same as backend)
        print("\n=== Testing Insert Query ===")
        test_query = f"""
            INSERT INTO `{TARGET_DB}`.downtime_notifications 
            (type, priority, subject, message_body, audience, project_id, scheduled_at, status, created_by, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """
        
        test_params = (
            'PLANNED_MAINTENANCE',
            'MEDIUM',
            'Test Notification',
            'This is a test message',
            'ALL_USERS',
            None,
            None,
            'PENDING',
            'test@example.com'
        )
        
        print("Query:")
        print(test_query)
        print("\nParameters:")
        for i, param in enumerate(test_params):
            print(f"  {i+1}. {param}")
        
        try:
            cursor.execute(test_query, test_params)
            print(f"\n✓ Test insert successful! Inserted ID: {cursor.lastrowid}")
            
            # Delete test record
            cursor.execute(f"DELETE FROM `{TARGET_DB}`.downtime_notifications WHERE id = {cursor.lastrowid}")
            print(f"✓ Test record cleaned up.")
            
        except Exception as e:
            print(f"\n✗ Insert failed: {e}")
            print("\nThis is the error preventing notifications from being saved!")
    
    conn.close()

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
