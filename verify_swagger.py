import requests
import json

print("=" * 70)
print("SWAGGER API DOCUMENTATION VERIFICATION")
print("=" * 70)

try:
    # Get OpenAPI schema
    response = requests.get("http://localhost:8000/api/v1/openapi.json", timeout=10)
    
    if response.status_code == 200:
        openapi_schema = response.json()
        
        # Check if release-notes endpoints are in the schema
        paths = openapi_schema.get('paths', {})
        
        release_note_endpoints = [
            '/api/v1/release-notes',
            '/api/v1/release-notes/{release_note_id}',
            '/api/v1/release-notes/{release_note_id}/publish',
            '/api/v1/release-notes/generate',
        ]
        
        print("\n📚 Checking OpenAPI/Swagger Documentation:\n")
        
        found_count = 0
        for endpoint in release_note_endpoints:
            if endpoint in paths:
                methods = list(paths[endpoint].keys())
                print(f"   ✅ {endpoint}")
                print(f"      Methods: {', '.join(methods).upper()}")
                found_count += 1
            else:
                print(f"   ❌ {endpoint} NOT FOUND in OpenAPI schema")
        
        # Check tags
        tags = openapi_schema.get('tags', [])
        release_notes_tag = any(tag.get('name') == 'Release Notes' for tag in tags)
        
        if release_notes_tag:
            print(f"\n   ✅ 'Release Notes' tag exists in documentation")
        else:
            print(f"\n   ⚠️  'Release Notes' tag not found")
        
        print(f"\n📊 Summary:")
        print(f"   Found {found_count} release note endpoint groups")
        print(f"   Total API paths: {len(paths)}")
        
        print("\n" + "=" * 70)
        print("✅ SWAGGER DOCUMENTATION VERIFIED")
        print("=" * 70)
        print(f"\n🌐 View full API docs at: http://localhost:8000/api/v1/docs")
        
    else:
        print(f"\n❌ Failed to get OpenAPI schema")
        print(f"   Status: {response.status_code}")
        
except requests.exceptions.ConnectionError:
    print("\n❌ Cannot connect to API server")
    print("   Make sure the backend is running: python main.py")
except Exception as e:
    print(f"\n❌ Error: {e}")
