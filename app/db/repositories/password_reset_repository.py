"""
Password Reset Token Repository

Database operations for password reset tokens.
"""

import uuid
from typing import Optional, Dict, Any
from app.db.database import Database
from app.core.logger import logger


class PasswordResetRepository:
    """Repository for password reset token operations"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def create_reset_token(
        self,
        user_id: str,
        token: str,
        expires_in_hours: int = 1
    ) -> Dict[str, Any]:
        """
        Create password reset token.
        
        Args:
            user_id: User ID
            token: Reset token
            expires_in_hours: Token expiration hours
        
        Returns:
            Created token data
        """
        token_id = f"prt-{uuid.uuid4().hex[:16]}"
        
        query = """
            INSERT INTO password_reset_tokens (
                token_id, user_id, token, expires_at, used, created_at
            )
            VALUES (%s, %s, %s, DATE_ADD(NOW(), INTERVAL %s HOUR), FALSE, NOW())
        """
        
        await self.db.execute_query(
            query,
            (token_id, user_id, token, expires_in_hours),
            commit=True
        )
        
        logger.info(f"Password reset token created for user: {user_id}")
        
        # Fetch the created token to get the actual expires_at timestamp
        created_token = await self.db.execute_query(
            "SELECT token_id, user_id, token, expires_at FROM password_reset_tokens WHERE token_id = %s",
            (token_id,),
            fetch_one=True
        )
        
        return created_token if created_token else {
            "token_id": token_id,
            "user_id": user_id,
            "token": token,
            "expires_in_hours": expires_in_hours
        }
    
    async def get_valid_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get valid (non-expired, unused) reset token.
        
        Args:
            token: Reset token
        
        Returns:
            Token data or None
        """
        query = """
            SELECT 
                token_id,
                user_id,
                token,
                expires_at,
                used,
                created_at
            FROM password_reset_tokens
            WHERE token = %s
              AND used = FALSE
              AND expires_at > NOW()
        """
        
        result = await self.db.execute_query(query, (token,), fetch_one=True)
        return result
    
    async def mark_token_used(self, token: str) -> bool:
        """
        Mark reset token as used.
        
        Args:
            token: Reset token
        
        Returns:
            True if marked
        """
        query = """
            UPDATE password_reset_tokens
            SET used = TRUE
            WHERE token = %s
        """
        
        await self.db.execute_query(query, (token,), commit=True)
        logger.info(f"Password reset token marked as used")
        return True
    
    async def invalidate_user_tokens(self, user_id: str) -> bool:
        """
        Invalidate all tokens for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            True if invalidated
        """
        query = """
            UPDATE password_reset_tokens
            SET used = TRUE
            WHERE user_id = %s AND used = FALSE
        """
        
        await self.db.execute_query(query, (user_id,), commit=True)
        logger.info(f"All password reset tokens invalidated for user: {user_id}")
        return True
