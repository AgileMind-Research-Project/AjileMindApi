import os
from pathlib import Path

print("=" * 70)
print("FILE EXISTENCE VERIFICATION")
print("=" * 70)

base_path = Path(__file__).parent

# Backend files
backend_files = [
    ("Schema", "app/schemas/release_note_schemas.py"),
    ("Service", "app/services/release_note_service.py"),
    ("API Router", "app/api/v1/release_notes.py"),
]

print("\n📁 BACKEND FILES:")
all_exist = True
for name, path in backend_files:
    full_path = base_path / path
    exists = full_path.exists()
    if exists:
        size = full_path.stat().st_size
        print(f"   ✅ {name}: {path} ({size:,} bytes)")
    else:
        print(f"   ❌ {name}: {path} MISSING")
        all_exist = False

# Check main.py imports
print("\n📝 MAIN.PY INTEGRATION:")
main_py = base_path / "main.py"
if main_py.exists():
    content = main_py.read_text()
    
    checks = [
        ("Import release_notes", "release_notes" in content and "from app.api.v1 import" in content),
        ("Router registration", "release_notes.router" in content and "/release-notes" in content),
    ]
    
    for check_name, passed in checks:
        if passed:
            print(f"   ✅ {check_name}")
        else:
            print(f"   ❌ {check_name} MISSING")
            all_exist = False
else:
    print("   ❌ main.py not found")
    all_exist = False

print("\n" + "=" * 70)
if all_exist:
    print("✅ ALL BACKEND FILES VERIFIED")
else:
    print("❌ SOME FILES MISSING")
print("=" * 70)
