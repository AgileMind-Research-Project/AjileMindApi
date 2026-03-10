from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.core.logger import logger

scheduler = AsyncIOScheduler()

def start_scheduler():
    if not scheduler.running:
        try:
            # Inline imports to avoid circular dependency issues
            from app.services.notification_service import NotificationService
            from app.db.database import db
            
            # Initialize service
            service = NotificationService(db)
            
            # Register the periodic check for due notifications (Alerts & Release Notes)
            # This runs every 1 minute to fulfill the automated delivery requirement
            scheduler.add_job(
                service.process_due_notifications, 
                'interval', 
                minutes=1, 
                id='downtime_notifications_job',
                replace_existing=True
            )
            
            scheduler.start()
            logger.info("APScheduler started successfully with downtime_notifications_job.")
        except Exception as e:
            logger.error(f"Failed to start APScheduler: {e}")
