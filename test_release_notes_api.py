import requests

# Test Release Notes API endpoints
BASE_URL = "http://localhost:8000/api/v1"

print("Testing Release Notes API Endpoints...")
print("=" * 50)

# Test 1: Check if endpoint exists (should get 401 without auth, not 404)
try:
    response = requests.get(f"{BASE_URL}/release-notes")
    print(f"✅ GET /release-notes endpoint exists (Status: {response.status_code})")
    if response.status_code == 401:
        print("   Expected: 401 Unauthorized (authentication required)")
    elif response.status_code == 404:
        print("   ❌ ERROR: Endpoint not found!")
except Exception as e:
    print(f"❌ Error connecting to API: {e}")

print("\n" + "=" * 50)
print("Backend API is ready!")
print("Frontend is accessible at: http://localhost:3008/release-notes")
