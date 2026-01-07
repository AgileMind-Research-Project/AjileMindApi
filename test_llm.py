"""
Quick test to verify LLM service is working
"""
import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_llm_service():
    print("=" * 60)
    print("🧪 Testing LLM Service")
    print("=" * 60)
    
    try:
        from app.services.llm_service import llm_service
        print("✅ LLM Service imported successfully")
        
        # Test data
        test_metadata = {
            'total_tasks': 20,
            'uncompleted_tasks': 12,
            'todo_tasks': 8,
            'overdue_tasks': 3,
            'max_overdue_days': 10
        }
        
        print("\n📊 Test Data:")
        print(f"   Total Tasks: {test_metadata['total_tasks']}")
        print(f"   Uncompleted: {test_metadata['uncompleted_tasks']}")
        print(f"   Overdue: {test_metadata['overdue_tasks']}")
        
        print("\n🤖 Generating AI recommendations...")
        
        recommendations = await llm_service.generate_recommendations(
            risk_type='uncompleted_tasks',
            project_data={'project_id': 1, 'project_name': 'Test'},
            metadata=test_metadata
        )
        
        if recommendations:
            print(f"\n✅ Success! Generated {len(recommendations)} recommendations:\n")
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec}\n")
        else:
            print("\n⚠️ No recommendations generated (LLM might not be running)")
            
    except ImportError as e:
        print(f"\n❌ Failed to import LLM service: {e}")
        print("   Make sure dependencies are installed: pip install -r requirements.txt")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(test_llm_service())
