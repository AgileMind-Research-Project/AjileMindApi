from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.core.logger import logger

scheduler = AsyncIOScheduler()

def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started.")
