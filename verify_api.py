import requests
import json

print("=" * 70)
print("API ENDPOINT VERIFICATION")
print("=" * 70)

BASE_URL = "http://localhost:8000/api/v1"

endpoints = [
    ("List Release Notes", "GET", "/release-notes"),
    ("Get Release Note", "GET", "/release-notes/1"),
    ("Create Release Note", "POST", "/release-notes"),
    ("Update Release Note", "PUT", "/release-notes/1"),
    ("Delete Release Note", "DELETE", "/release-notes/1"),
    ("Publish Release Note", "POST", "/release-notes/1/publish"),
    ("Generate with AI", "POST", "/release-notes/generate"),
]

print("\n🌐 Testing API Endpoints (Expected: 401 Unauthorized):\n")

all_working = True
for name, method, path in endpoints:
    try:
        url = f"{BASE_URL}{path}"
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "POST":
            response = requests.post(url, json={}, timeout=5)
        elif method == "PUT":
            response = requests.put(url, json={}, timeout=5)
        elif method == "DELETE":
            response = requests.delete(url, timeout=5)
        
        # 401 = Endpoint exists but requires authentication (GOOD)
        # 404 = Endpoint doesn't exist (BAD)
        # 422 = Validation error (GOOD - endpoint exists)
        # 500 = Server error (BAD)
        
        if response.status_code in [401, 422]:
            print(f"   ✅ {name:30s} ({method:6s}) - Status {response.status_code}")
        elif response.status_code == 404:
            print(f"   ❌ {name:30s} ({method:6s}) - NOT FOUND (404)")
            all_working = False
        elif response.status_code == 500:
            print(f"   ⚠️  {name:30s} ({method:6s}) - SERVER ERROR (500)")
            all_working = False
        else:
            print(f"   ℹ️  {name:30s} ({method:6s}) - Status {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print(f"   ❌ {name:30s} - Cannot connect to server")
        all_working = False
    except Exception as e:
        print(f"   ❌ {name:30s} - Error: {e}")
        all_working = False

print("\n" + "=" * 70)
if all_working:
    print("✅ ALL API ENDPOINTS ARE ACCESSIBLE")
    print("Note: 401 (Unauthorized) is expected - authentication is required")
else:
    print("❌ SOME ENDPOINTS HAVE ISSUES")
print("=" * 70)
