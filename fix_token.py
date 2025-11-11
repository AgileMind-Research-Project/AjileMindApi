"""Update existing token expiration to be valid"""
import asyncio
from app.db.database import db

async def fix_token():
    try:
        await db.connect()
        
        # Update the latest token to expire 1 hour from now
        result = await db.execute_query(
            '''UPDATE password_reset_tokens 
               SET expires_at = DATE_ADD(NOW(), INTERVAL 1 HOUR)
               WHERE token = %s''',
            ('DntB4TMxznR1w-D83wBaPjRmdfGD97dMl_4n94qypow',),
            commit=True
        )
        
        print("✅ Token updated successfully!")
        
        # Verify it's now valid
        check = await db.execute_query(
            '''SELECT token, expires_at, used, created_at 
               FROM password_reset_tokens 
               WHERE token = %s''',
            ('DntB4TMxznR1w-D83wBaPjRmdfGD97dMl_4n94qypow',),
            fetch_one=True
        )
        
        if check:
            print(f"\nUpdated Token Info:")
            print(f"  Token: {check['token'][:20]}...")
            print(f"  Expires At: {check['expires_at']}")
            print(f"  Created At: {check['created_at']}")
            print(f"  Used: {check['used']}")
            
            # Check if now valid
            valid = await db.execute_query(
                '''SELECT COUNT(*) as count 
                   FROM password_reset_tokens 
                   WHERE token = %s AND used = FALSE AND expires_at > NOW()''',
                ('DntB4TMxznR1w-D83wBaPjRmdfGD97dMl_4n94qypow',),
                fetch_one=True
            )
            
            if valid and valid['count'] > 0:
                print("\n✅ Token is NOW VALID!")
            else:
                print("\n❌ Token is still invalid")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(fix_token())
