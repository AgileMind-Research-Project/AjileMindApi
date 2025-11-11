"""Test script to check password reset token"""
import asyncio
from app.db.database import db

async def test_token():
    try:
        await db.connect()
        
        # Check latest token
        result = await db.execute_query(
            'SELECT token, expires_at, used, created_at FROM password_reset_tokens ORDER BY created_at DESC LIMIT 1',
            fetch_one=True
        )
        
        if result:
            print("✅ Latest Password Reset Token Found:")
            print(f"   Token: {result['token'][:20]}...")
            print(f"   Expires At: {result['expires_at']}")
            print(f"   Used: {result['used']}")
            print(f"   Created At: {result['created_at']}")
            
            # Check if token is still valid
            valid_check = await db.execute_query(
                '''SELECT token_id, expires_at, used 
                   FROM password_reset_tokens 
                   WHERE token = %s AND used = FALSE AND expires_at > NOW()''',
                (result['token'],),
                fetch_one=True
            )
            
            if valid_check:
                print("\n✅ Token is VALID (not used, not expired)")
            else:
                print("\n❌ Token is INVALID (used or expired)")
        else:
            print("❌ No tokens found in database")
        
        await db.close()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_token())
