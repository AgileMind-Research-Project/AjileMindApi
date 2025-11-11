"""
Database Connection and Utilities

Handles MySQL database connections and query execution.
"""

import aiomysql
from typing import Optional, Dict, List, Any
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.logger import logger, log_database_query
import time


class Database:
    """Database connection manager"""
    
    def __init__(self):
        self.pool: Optional[aiomysql.Pool] = None
    
    async def connect(self):
        """Create database connection pool"""
        try:
            self.pool = await aiomysql.create_pool(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                db=settings.DB_NAME,
                minsize=1,
                maxsize=settings.DB_POOL_SIZE,
                echo=settings.DEBUG,
                autocommit=False
            )
            logger.info(f"Database pool created: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise
    
    async def disconnect(self):
        """Close database connection pool"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            logger.info("Database pool closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get database connection from pool"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        
        async with self.pool.acquire() as conn:
            yield conn
    
    async def execute_query(
        self,
        query: str,
        params: tuple = None,
        fetch_one: bool = False,
        fetch_all: bool = False,
        commit: bool = False
    ) -> Optional[Any]:
        """
        Execute database query with logging and error handling.
        
        Args:
            query: SQL query string
            params: Query parameters tuple
            fetch_one: Return single row
            fetch_all: Return all rows
            commit: Commit transaction
        
        Returns:
            Query result or None
        """
        start_time = time.time()
        result = None
        
        try:
            async with self.get_connection() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(query, params or ())
                    
                    if fetch_one:
                        result = await cursor.fetchone()
                    elif fetch_all:
                        result = await cursor.fetchall()
                    else:
                        result = cursor
                    
                    if commit:
                        await conn.commit()
                    
                    duration_ms = (time.time() - start_time) * 1000
                    rows_affected = cursor.rowcount
                    
                    log_database_query(
                        query=query,
                        duration_ms=duration_ms,
                        rows_affected=rows_affected
                    )
                    
                    return result
                    
        except Exception as e:
            logger.exception(f"Database query failed: {e}")
            raise
    
    async def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """
        Execute query with multiple parameter sets.
        
        Args:
            query: SQL query string
            params_list: List of parameter tuples
        
        Returns:
            Number of rows affected
        """
        start_time = time.time()
        
        try:
            async with self.get_connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.executemany(query, params_list)
                    await conn.commit()
                    
                    duration_ms = (time.time() - start_time) * 1000
                    rows_affected = cursor.rowcount
                    
                    log_database_query(
                        query=query,
                        duration_ms=duration_ms,
                        rows_affected=rows_affected
                    )
                    
                    return rows_affected
                    
        except Exception as e:
            logger.exception(f"Batch query failed: {e}")
            raise


# Global database instance
db = Database()


async def get_db() -> Database:
    """Dependency for FastAPI routes"""
    return db
