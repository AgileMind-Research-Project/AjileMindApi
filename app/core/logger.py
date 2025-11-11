"""
Logging Configuration for AgileMind Backend

This module sets up comprehensive logging with multiple handlers,
formatters, and integration points for monitoring and debugging.

Features:
- Console and file logging
- JSON structured logging
- Log rotation
- Request/response logging
- Performance monitoring
- Security event logging
- Integration with external services (Sentry, CloudWatch, etc.)
"""

import logging
import sys
import os
import json
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Dict, Any, Optional
import traceback
from contextvars import ContextVar

# Context variables for request tracking
request_context: ContextVar[Dict[str, Any]] = ContextVar('request_context', default={})

# Create logs directory
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Get environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO" if ENVIRONMENT == "production" else "DEBUG")


class JsonFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    Outputs logs in JSON format for easy parsing and analysis.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "environment": ENVIRONMENT,
        }
        
        # Add context from ContextVar
        context = request_context.get()
        log_data.update(context)
        
        # Add extra fields
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """
    Colored console formatter for development.
    Makes logs easier to read in terminal.
    """
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        
        # Add context if available
        context = request_context.get()
        context_str = ""
        if context:
            context_parts = [f"{k}={v}" for k, v in context.items()]
            context_str = f" [{', '.join(context_parts)}]"
        
        record.msg = f"{record.msg}{context_str}"
        
        return super().format(record)


def setup_logger(
    name: str = "agile_mind",
    log_level: str = LOG_LEVEL,
    log_to_console: bool = True,
    log_to_file: bool = True,
    json_format: bool = (ENVIRONMENT == "production")
) -> logging.Logger:
    """
    Set up and configure logger with multiple handlers.
    
    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_console: Enable console output
        log_to_file: Enable file output
        json_format: Use JSON format for logs
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    logger.handlers = []
    
    # Console Handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        
        if json_format:
            console_handler.setFormatter(JsonFormatter())
        else:
            console_formatter = ColoredFormatter(
                '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
        
        logger.addHandler(console_handler)
    
    # File Handlers
    if log_to_file:
        # General application log (rotating by size)
        app_log_handler = RotatingFileHandler(
            LOG_DIR / "app.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10
        )
        app_log_handler.setLevel(logging.INFO)
        
        # Error log (rotating by size)
        error_log_handler = RotatingFileHandler(
            LOG_DIR / "error.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10
        )
        error_log_handler.setLevel(logging.ERROR)
        
        # Daily rotating log
        daily_log_handler = TimedRotatingFileHandler(
            LOG_DIR / "daily.log",
            when="midnight",
            interval=1,
            backupCount=30  # Keep 30 days
        )
        daily_log_handler.setLevel(logging.INFO)
        
        # Set formatters
        if json_format:
            formatter = JsonFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s - [%(filename)s:%(lineno)d]',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        app_log_handler.setFormatter(formatter)
        error_log_handler.setFormatter(formatter)
        daily_log_handler.setFormatter(formatter)
        
        logger.addHandler(app_log_handler)
        logger.addHandler(error_log_handler)
        logger.addHandler(daily_log_handler)
    
    return logger


# Create default logger
logger = setup_logger()


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(f"agile_mind.{name}")


def add_context(**kwargs):
    """
    Add context to all subsequent logs in the current request.
    
    Usage:
        add_context(request_id="req-123", user_id="user-456")
    """
    context = request_context.get().copy()
    context.update(kwargs)
    request_context.set(context)


def clear_context():
    """Clear logging context."""
    request_context.set({})


def log_with_context(level: str, message: str, **kwargs):
    """
    Log message with additional context.
    
    Args:
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **kwargs: Additional context fields
    """
    log_func = getattr(logger, level.lower())
    
    # Create a custom LogRecord with extra fields
    extra = {"extra_fields": kwargs}
    log_func(message, extra=extra)


# Specialized logging functions

def log_request(method: str, path: str, status_code: int, duration_ms: float, **kwargs):
    """
    Log HTTP request.
    
    Args:
        method: HTTP method
        path: Request path
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        **kwargs: Additional context (user_id, tenant_id, etc.)
    """
    log_data = {
        "type": "http_request",
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": duration_ms,
        **kwargs
    }
    
    if status_code >= 500:
        log_with_context("error", f"{method} {path} - {status_code} - {duration_ms}ms", **log_data)
    elif status_code >= 400:
        log_with_context("warning", f"{method} {path} - {status_code} - {duration_ms}ms", **log_data)
    else:
        log_with_context("info", f"{method} {path} - {status_code} - {duration_ms}ms", **log_data)


def log_auth_event(event: str, **kwargs):
    """
    Log authentication event.
    
    Args:
        event: Event type (login_success, login_failed, logout, etc.)
        **kwargs: Event details (user_id, ip_address, etc.)
    """
    security_logger = get_logger("security")
    
    log_data = {
        "type": "auth_event",
        "event": event,
        **kwargs
    }
    
    security_logger.info(f"Auth event: {event}", extra={"extra_fields": log_data})


def log_authorization(action: str, user_id: str, resource: str, allowed: bool, **kwargs):
    """
    Log authorization check.
    
    Args:
        action: Action attempted
        user_id: User ID
        resource: Resource being accessed
        allowed: Whether access was allowed
        **kwargs: Additional context
    """
    security_logger = get_logger("security")
    
    log_data = {
        "type": "authorization",
        "action": action,
        "user_id": user_id,
        "resource": resource,
        "allowed": allowed,
        **kwargs
    }
    
    level = "warning" if not allowed else "info"
    log_func = getattr(security_logger, level)
    log_func(
        f"Authorization {'granted' if allowed else 'denied'}: {action} on {resource}",
        extra={"extra_fields": log_data}
    )


def log_performance(operation: str, duration_ms: float, threshold_ms: float = 1000, **kwargs):
    """
    Log performance metrics.
    
    Args:
        operation: Operation name
        duration_ms: Duration in milliseconds
        threshold_ms: Warning threshold
        **kwargs: Additional context
    """
    perf_logger = get_logger("performance")
    
    log_data = {
        "type": "performance",
        "operation": operation,
        "duration_ms": duration_ms,
        **kwargs
    }
    
    if duration_ms > threshold_ms:
        perf_logger.warning(
            f"Slow operation: {operation} took {duration_ms}ms",
            extra={"extra_fields": log_data}
        )
    else:
        perf_logger.debug(
            f"Operation: {operation} took {duration_ms}ms",
            extra={"extra_fields": log_data}
        )


def log_database_query(query: str, duration_ms: float, rows_affected: int = 0, **kwargs):
    """
    Log database query.
    
    Args:
        query: SQL query
        duration_ms: Query duration
        rows_affected: Number of rows affected
        **kwargs: Additional context
    """
    db_logger = get_logger("database")
    
    log_data = {
        "type": "database_query",
        "query": query[:200],  # Truncate long queries
        "duration_ms": duration_ms,
        "rows_affected": rows_affected,
        **kwargs
    }
    
    if duration_ms > 500:
        db_logger.warning(
            f"Slow query ({duration_ms}ms): {query[:100]}",
            extra={"extra_fields": log_data}
        )
    else:
        db_logger.debug(
            f"Query ({duration_ms}ms): {query[:100]}",
            extra={"extra_fields": log_data}
        )


def log_ai_request(operation: str, model: str, tokens_used: int, duration_ms: float, **kwargs):
    """
    Log AI/ML API request.
    
    Args:
        operation: Operation type
        model: Model name
        tokens_used: Number of tokens consumed
        duration_ms: Request duration
        **kwargs: Additional context
    """
    ai_logger = get_logger("ai")
    
    log_data = {
        "type": "ai_request",
        "operation": operation,
        "model": model,
        "tokens_used": tokens_used,
        "duration_ms": duration_ms,
        **kwargs
    }
    
    ai_logger.info(
        f"AI request: {operation} using {model} - {tokens_used} tokens - {duration_ms}ms",
        extra={"extra_fields": log_data}
    )


def log_integration_event(provider: str, event: str, success: bool, **kwargs):
    """
    Log integration event (Jira, Teams, GitHub).
    
    Args:
        provider: Integration provider
        event: Event type
        success: Whether event succeeded
        **kwargs: Additional context
    """
    integration_logger = get_logger("integration")
    
    log_data = {
        "type": "integration_event",
        "provider": provider,
        "event": event,
        "success": success,
        **kwargs
    }
    
    level = "info" if success else "error"
    log_func = getattr(integration_logger, level)
    log_func(
        f"Integration {provider}: {event} - {'success' if success else 'failed'}",
        extra={"extra_fields": log_data}
    )


def log_exception(exception: Exception, context: Dict[str, Any] = None):
    """
    Log exception with full traceback and context.
    
    Args:
        exception: Exception instance
        context: Additional context dictionary
    """
    logger.exception(
        f"Exception occurred: {type(exception).__name__}: {str(exception)}",
        extra={"extra_fields": context or {}},
        exc_info=True
    )


# Export commonly used functions
__all__ = [
    'logger',
    'get_logger',
    'setup_logger',
    'add_context',
    'clear_context',
    'log_with_context',
    'log_request',
    'log_auth_event',
    'log_authorization',
    'log_performance',
    'log_database_query',
    'log_ai_request',
    'log_integration_event',
    'log_exception',
]
