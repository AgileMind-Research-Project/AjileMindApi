"""
AgileMind Backend - FastAPI Application
Multi-tenant SaaS Platform for Agile Project Management
"""

from fastapi import FastAPIriskpara
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import sys
import os
from pathlib import Path

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings
from config_test import run_config_test

# Import routers
from app.api.v1 import auth, roles, audit, platform, users, jira, otp, projects, redis_chat, backlog, meetings, riskparameters, trust_index,notifications, backlog_priority, meters, documents, transcripts, reports, templates, notifications, release_notes
from app.meeting_config import routes as meetings_router
from app.task_updates_config import routes as task_updates_router
from app.db.database import db
from app.middleware.audit_middleware import AuditLoggingMiddleware
from app.core.redis_chat_client import init_redis_chat

from app.services.scheduler import start_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Run configuration tests on startup
    run_config_test()
    
    # Initialize database connection pool
    print("\n🔌 Initializing database connection pool...")
    try:
        await db.connect()
        print("✅ Database pool initialized successfully\n")
    except Exception as e:
        print(f"❌ Failed to initialize database pool: {e}\n")
        raise
    
    # Initialize Redis chat client
    print("🔌 Initializing Redis Chat client...")
    try:
        init_redis_chat()
        print("✅ Redis Chat initialized successfully\n")
    except Exception as e:
        print(f"⚠️  Redis Chat initialization warning: {e}\n")
        # Don't raise - chat is optional

    # Initialize Scheduler
    print("⏰ Initializing Background Scheduler...")
    try:
        start_scheduler()
        print("✅ Scheduler started successfully\n")
    except Exception as e:
        print(f"❌ Failed to start scheduler: {e}\n")
    
    yield
    
    # Cleanup
    
    # Cleanup
    print("\n" + "="*70)
    print("👋 Shutting down AgileMind Backend Server...")
    print("🔌 Closing database connections...")
    await db.disconnect()
    print("="*70 + "\n")

# Initialize FastAPI application
app = FastAPI(
    title=settings.APP_NAME + " API",
    description="Multi-tenant SaaS platform for agile project management",
    version=settings.APP_VERSION,
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    lifespan=lifespan
)

# CORS Configuration - Load from settings
cors_origins = settings.CORS_ORIGINS
if isinstance(cors_origins, str):
    cors_origins = [origin.strip() for origin in cors_origins.split(',')]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Audit Logging Middleware
if settings.AUDIT_LOGGING_ENABLED:
    app.add_middleware(AuditLoggingMiddleware)

# Health check endpoint
@app.get("/", tags=["Health"])
async def root():
    """
    Root endpoint - API status and quick info
    
    Returns basic information about the API including:
    - Service status
    - API version
    - Environment
    - Documentation URLs
    """
    return {
        "status": "online",
        "service": settings.APP_NAME + " API",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "message": "Welcome to AgileMind API - Multi-tenant Agile Project Management Platform",
        "documentation": {
            "swagger": f"http://{settings.HOST}:{settings.PORT}{settings.API_PREFIX}/docs",
            "redoc": f"http://{settings.HOST}:{settings.PORT}{settings.API_PREFIX}/redoc"
        },
        "endpoints": {
            "health": "/health",
            "api_status": f"{settings.API_PREFIX}/status",
            "api_docs": f"{settings.API_PREFIX}/docs"
        }
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Comprehensive health check endpoint
    
    Performs basic health checks and returns:
    - Overall service health status
    - Database connectivity status
    - Configuration status
    - System information
    
    This endpoint can be used by load balancers, monitoring tools, and orchestration platforms.
    """
    import datetime
    import pymysql
    
    # Check database connection
    db_status = "unknown"
    db_details = {}
    try:
        connection = pymysql.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME
        )
        db_status = "connected"
        db_details = {
            "host": settings.DB_HOST,
            "port": settings.DB_PORT,
            "database": settings.DB_NAME,
            "status": "✅ Connected"
        }
        connection.close()
    except Exception as e:
        db_status = "disconnected"
        db_details = {
            "status": "❌ Disconnected",
            "error": str(e)
        }
    
    overall_status = "healthy" if db_status == "connected" else "degraded"
    
    return {
        "status": overall_status,
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.datetime.now().isoformat(),
        "environment": settings.ENVIRONMENT,
        "checks": {
            "database": {
                "status": db_status,
                "details": db_details
            },
            "configuration": {
                "status": "loaded",
                "details": {
                    "api_prefix": settings.API_PREFIX,
                    "cors_enabled": True,
                    "debug_mode": settings.DEBUG
                }
            }
        },
        "uptime": "Server running"
    }

@app.get(f"{settings.API_PREFIX}/status", tags=["API Info"])
async def api_status():
    """
    Detailed API status and capabilities
    
    Returns comprehensive information about:
    - API version and configuration
    - Available endpoints and their implementation status
    - Feature availability
    - Rate limiting information
    """
    return {
        "api_version": settings.APP_VERSION,
        "api_prefix": settings.API_PREFIX,
        "status": "active",
        "environment": settings.ENVIRONMENT,
        "features": {
            "multi_tenancy": "available",
            "authentication": "jwt",
            "database": "mysql",
            "cors": "enabled"
        },
        "endpoints": {
            "platform": {
                "register_tenant": "Active",
                "health": "Active"
            },
            "authentication": {
                "login": "Active",
                "logout": "Active",
                "register": "Active",
                "refresh_token": "Planned",
                "change_password": "Requires Auth",
                "forgot_password": "Active",
                "reset_password": "Active",
                "invite_user": "Requires Auth",
                "get_current_user": "Requires Auth"
            },
            "tenants": {
                "create": "Planned",
                "list": "Planned",
                "update": "Planned",
                "delete": "Planned"
            },
            "users": {
                "profile": "Planned",
                "list": "Planned",
                "update": "Planned"
            },
            "sprints": {
                "create": "Planned",
                "list": "Planned",
                "update": "Planned",
                "analytics": "Planned"
            },
            "tasks": {
                "create": "Planned",
                "list": "Planned",
                "update": "Planned",
                "assign": "Planned"
            }
        },
        "rate_limiting": {
            "enabled": False,
            "requests_per_minute": "unlimited"
        },
        "documentation": {
            "swagger_ui": f"{settings.API_PREFIX}/docs",
            "redoc": f"{settings.API_PREFIX}/redoc"
        }
    }

# Include routers
app.include_router(platform.router, prefix=f"{settings.API_PREFIX}/platform", tags=["Platform"])
app.include_router(auth.router, prefix=f"{settings.API_PREFIX}/auth", tags=["Authentication"])
app.include_router(otp.router, prefix=f"{settings.API_PREFIX}/otp", tags=["OTP Authentication"])
app.include_router(roles.router, prefix=f"{settings.API_PREFIX}/roles", tags=["Roles"])
app.include_router(audit.router, prefix=f"{settings.API_PREFIX}/audit", tags=["Audit Logs"])
app.include_router(users.router, prefix=f"{settings.API_PREFIX}/users", tags=["Users"])
app.include_router(jira.router, prefix=f"{settings.API_PREFIX}/jira", tags=["Jira Integration"])
app.include_router(projects.router, prefix=f"{settings.API_PREFIX}/projects", tags=["Projects"])
app.include_router(backlog.router, prefix=f"{settings.API_PREFIX}/backlog", tags=["Backlog"])
app.include_router(backlog_priority.router, prefix=f"{settings.API_PREFIX}/backlog-priority", tags=["Backlog Priority"])
app.include_router(notifications.router, prefix=f"{settings.API_PREFIX}/notifications", tags=["Notifications"])
app.include_router(redis_chat.router, prefix=f"{settings.API_PREFIX}/chat", tags=["Redis Chat"])
app.include_router(riskparameters.router,prefix=f"{settings.API_PREFIX}/risk-parameters", tags=["Risk Parameters"])
app.include_router(documents.router, prefix=f"{settings.API_PREFIX}/documents", tags=["Documents & RAG Chatbot"])
app.include_router(meetings_router.router, prefix=f"{settings.API_PREFIX}/meetings", tags=["Meetings"])
app.include_router(task_updates_router.router, prefix=f"{settings.API_PREFIX}/task-updates", tags=["Task Updates"])
app.include_router(transcripts.router, prefix=f"{settings.API_PREFIX}/transcripts", tags=["Transcripts"])
app.include_router(reports.router, prefix=f"{settings.API_PREFIX}/reports", tags=["Reports"])
app.include_router(templates.router, prefix=f"{settings.API_PREFIX}/report-templates", tags=["Report Templates"])
app.include_router(notifications.router, prefix=f"{settings.API_PREFIX}/notifications", tags=["Notifications"])
app.include_router(release_notes.router, prefix=f"{settings.API_PREFIX}/release-notes", tags=["Release Notes"])
app.include_router(riskparameters.router, prefix=f"{settings.API_PREFIX}/risk-parameters", tags=["Risk Parameters"])
app.include_router(trust_index.router, prefix=f"{settings.API_PREFIX}/trust-index", tags=["Trust Index"])
# app.include_router(tenants.router, prefix=f"{settings.API_PREFIX}/tenants", tags=["Tenants"])

if __name__ == "__main__":    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )
