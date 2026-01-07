import pymysql
import sys

# Database credentials from .env
DB_HOST = "ballast.proxy.rlwy.net"
DB_PORT = 58607
DB_USER = "root"
DB_PASSWORD = "CtBeFkVkJSUcybwQFvevXGaOMspvxDHZ"
DB_NAME = "agilemind_db"

try:
    print(f"Connecting to {DB_HOST}:{DB_PORT}...")
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME
    )
    
    with conn.cursor() as cursor:
        print(f"Databases:")
        cursor.execute("SHOW DATABASES")
        for row in cursor.fetchall():
            print(f"- {row[0]}")
            
except Exception as e:
    print(f"Error: {e}")
