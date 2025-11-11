"""
Logging Decorators

Decorators for automatic logging of function calls, performance,
exceptions, and other events.
"""

import functools
import time
from typing import Callable, Any

from app.core.logger import (
    logger,
    log_performance,
    log_exception,
    log_database_query,
    log_ai_request,
)


def log_function_call(func: Callable) -> Callable:
    """
    Decorator to log function calls with arguments and return values.
    
    Usage:
        @log_function_call
        def my_function(arg1, arg2):
            return result
    """
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        func_name = func.__name__
        logger.debug(
            f"Calling {func_name}",
            extra={
                "extra_fields": {
                    "function": func_name,
                    "args_count": len(args),
                    "kwargs": list(kwargs.keys()),
                }
            }
        )
        
        try:
            result = await func(*args, **kwargs)
            logger.debug(f"Function {func_name} completed successfully")
            return result
        except Exception as e:
            log_exception(e, context={"function": func_name})
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        func_name = func.__name__
        logger.debug(
            f"Calling {func_name}",
            extra={
                "extra_fields": {
                    "function": func_name,
                    "args_count": len(args),
                    "kwargs": list(kwargs.keys()),
                }
            }
        )
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"Function {func_name} completed successfully")
            return result
        except Exception as e:
            log_exception(e, context={"function": func_name})
            raise
    
    # Return appropriate wrapper based on function type
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def monitor_performance(threshold_ms: float = 1000):
    """
    Decorator to monitor function performance.
    Logs warning if execution time exceeds threshold.
    
    Usage:
        @monitor_performance(threshold_ms=500)
        async def slow_function():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.time() - start_time) * 1000
                log_performance(
                    operation=func.__name__,
                    duration_ms=duration_ms,
                    threshold_ms=threshold_ms,
                )
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.time() - start_time) * 1000
                log_performance(
                    operation=func.__name__,
                    duration_ms=duration_ms,
                    threshold_ms=threshold_ms,
                )
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def log_exceptions(func: Callable) -> Callable:
    """
    Decorator to automatically log exceptions.
    
    Usage:
        @log_exceptions
        def risky_function():
            pass
    """
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            log_exception(e, context={"function": func.__name__})
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            log_exception(e, context={"function": func.__name__})
            raise
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def log_db_query(func: Callable) -> Callable:
    """
    Decorator to log database queries.
    
    Usage:
        @log_db_query
        async def execute_query(query: str):
            pass
    """
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        
        # Try to extract query from args/kwargs
        query = ""
        if args:
            query = str(args[0])[:200]
        elif "query" in kwargs:
            query = str(kwargs["query"])[:200]
        
        try:
            result = await func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000
            
            # Try to get row count from result
            rows_affected = 0
            if hasattr(result, "rowcount"):
                rows_affected = result.rowcount
            
            log_database_query(
                query=query,
                duration_ms=duration_ms,
                rows_affected=rows_affected,
            )
            
            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_exception(e, context={"query": query, "duration_ms": duration_ms})
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        
        query = ""
        if args:
            query = str(args[0])[:200]
        elif "query" in kwargs:
            query = str(kwargs["query"])[:200]
        
        try:
            result = func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000
            
            rows_affected = 0
            if hasattr(result, "rowcount"):
                rows_affected = result.rowcount
            
            log_database_query(
                query=query,
                duration_ms=duration_ms,
                rows_affected=rows_affected,
            )
            
            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_exception(e, context={"query": query, "duration_ms": duration_ms})
            raise
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


# Import asyncio at the end to avoid circular imports
import asyncio


__all__ = [
    'log_function_call',
    'monitor_performance',
    'log_exceptions',
    'log_db_query',
]
