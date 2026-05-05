import pymysql
import json

def check_project_10009():
    conn = pymysql.connect(
        host='localhost',
        user='root',
        password='root', # Defaulting to root/root or similar if not specified
        db='sliit'
    )
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # Check project
            cursor.execute("SELECT project_id, project_name, board_id, sprint_size FROM projects WHERE project_id = 10009")
            project = cursor.fetchone()
            print("Project Info:", json.dumps(project, indent=2))
            
            # Check sprints
            cursor.execute("SELECT * FROM sprint WHERE project_id = 10009")
            sprints = cursor.fetchall()
            print("\nSprints:", json.dumps(sprints, indent=2, default=str))
            
    finally:
        conn.close()

if __name__ == "__main__":
    check_project_10009()
