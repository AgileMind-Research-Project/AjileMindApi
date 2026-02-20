"""
Quick diagnostic to check why AI recommendations aren't working
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("="*60)
print("🔍 DIAGNOSING AI RECOMMENDATIONS")
print("="*60)

# Check 1: LLM Service Import
print("\n1️⃣ Checking if LLM service can be imported...")
try:
    from app.services.llm_service import llm_service
    print("   ✅ LLM Service imported successfully")
    
    if llm_service.llm:
        print(f"   ✅ LLM initialized: {llm_service.model_name}")
    else:
        print("   ❌ LLM object is None - Ollama not connected")
        
except Exception as e:
    print(f"   ❌ Failed to import: {e}")
    sys.exit(1)

# Check 2: Ollama Connection
print("\n2️⃣ Testing Ollama connection...")
try:
    import httpx
    response = httpx.get("http://localhost:11434/api/tags")
    if response.status_code == 200:
        print("   ✅ Ollama is running")
        models = response.json().get('models', [])
        print(f"   ✅ Available models: {[m.get('name') for m in models]}")
    else:
        print(f"   ❌ Ollama returned status: {response.status_code}")
except Exception as e:
    print(f"   ❌ Cannot connect to Ollama: {e}")
    print("   💡 Start Ollama service")

# Check 3: Quick AI Test
print("\n3️⃣ Testing AI generation (quick test)...")
import asyncio

async def quick_test():
    try:
        test_metadata = {
            'total_tasks': 10,
            'uncompleted_tasks': 5,
            'overdue_tasks': 2
        }
        
        print("   Sending simple prompt to AI...")
        recommendations = await llm_service.generate_recommendations(
            risk_type='uncompleted_tasks',
            project_data={'project_id': 1},
            metadata=test_metadata
        )
        
        if recommendations:
            print(f"   ✅ AI generated {len(recommendations)} recommendations")
            print("\n   Sample recommendation:")
            print(f"   • {recommendations[0][:100]}...")
            return True
        else:
            print("   ❌ AI returned empty list")
            return False
            
    except Exception as e:
        print(f"   ❌ AI generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

result = asyncio.run(quick_test())

print("\n" + "="*60)
if result:
    print("✅ DIAGNOSIS: AI is working correctly!")
    print("\n💡 If recommendations still don't show in browser:")
    print("   1. Restart backend: uvicorn main:app --reload")
    print("   2. Hard refresh browser: Ctrl+Shift+R")
    print("   3. Check browser console for errors")
else:
    print("❌ DIAGNOSIS: AI is not working")
    print("\n💡 Troubleshooting steps:")
    print("   1. Ensure Ollama is running: ollama list")
    print("   2. Check model is downloaded: ollama pull llama3.2")
    print("   3. Restart Ollama service")
    print("   4. Check firewall/antivirus not blocking localhost:11434")
print("="*60)
