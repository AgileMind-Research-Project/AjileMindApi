import pymysql

DB_HOST = "ballast.proxy.rlwy.net"
DB_PORT = 58607
DB_USER = "root"
DB_PASSWORD = "CtBeFkVkJSUcybwQFvevXGaOMspvxDHZ"

try:
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        db="sliit"
    )
    
    cursor = conn.cursor()
    cursor.execute("SHOW CREATE TABLE projects")
    result = cursor.fetchone()
    
    print("=== PROJECTS TABLE SCHEMA ===")
    print(result[1])
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
