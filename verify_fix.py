
import sys
import os

# Add the project root to the python path
sys.path.append(os.getcwd())

print("Attempting to import app.services.meeting_service...")
try:
    from app.services import meeting_service
    print("✅ Successfully imported meeting_service")
except Exception as e:
    print(f"❌ Failed to import meeting_service: {e}")
    sys.exit(1)

print("Attempting to import app.websocket.socket_server...")
try:
    from app.websocket import socket_server
    print("✅ Successfully imported socket_server")
except Exception as e:
    print(f"❌ Failed to import socket_server: {e}")
    sys.exit(1)

print("Attempting to import app.api.v1.meetings...")
try:
    from app.api.v1 import meetings
    print("✅ Successfully imported meetings")
except Exception as e:
    print(f"❌ Failed to import meetings: {e}")
    sys.exit(1)

print("All imports successful!")
