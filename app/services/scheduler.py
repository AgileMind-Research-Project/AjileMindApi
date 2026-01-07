from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.db.database import db
from app.services.notification_service import NotificationService
from app.core.logger import logger
import asyncio

scheduler = AsyncIOScheduler()

async def check_downtime_notifications():
    try:
        service = NotificationService(db)
        await service.process_due_notifications()
    except Exception as e:
        logger.error(f"Scheduler Job Error: {e}")

def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(check_downtime_notifications, 'interval', minutes=1)
        scheduler.start()
        logger.info("APScheduler started.")
