"""
Meeting Scheduler Service - Background Link Poster

Fulfills the requirement: "link add before 5 meeting start meeting"
Automatically monitors scheduled meetings and posts the meeting link 
to the corresponding channel 5 minutes before start time.
"""

import asyncio
import logging
from datetime import datetime, timedelta, time
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.db.database import db
from app.core.logger import logger
from app.services.meeting_service import get_meeting_service
from app.services.redis_chat_service import get_redis_chat_service

class MeetingSchedulerService:
    _instance = None
    _running = False
    _task = None

    def __init__(self):
        self.chat_service = get_redis_chat_service()
        self.processed_meetings = set()  # Reminders (tenant, meeting_id)
        self.started_meetings = set()    # Active Notifications (tenant, meeting_id)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start(self):
        """Start the background scheduler task"""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._worker_loop())
        logger.info("Meeting Scheduler Task started")

    async def stop(self):
        """Stop the background scheduler task"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Meeting Scheduler Task stopped")

    async def _worker_loop(self):
        """Main loop that runs every minute"""
        while self._running:
            try:
                await self.check_upcoming_meetings()
            except Exception as e:
                logger.error(f"Error in Meeting Scheduler loop: {e}", exc_info=True)
            
            # Run every 60 seconds
            await asyncio.sleep(60)

    async def check_upcoming_meetings(self):
        """
        1. Discover all tenants (actual databases)
        2. Update status of meetings (ENDED/ONGOING)
        3. Query their meetings tables for reminders
        4. Post links for those starting in the next 5 minutes
        5. Post 'Happening Now' for those starting exactly now
        """
        now = datetime.now()
        today = now.date()
        current_time = now.time()

        # Window for 5-minute reminder (Catch everything starting in the next 5 minutes)
        reminder_time = (now + timedelta(minutes=5)).time()
        
        # Window for "Starting Now" notification
        start_now_window = (now - timedelta(minutes=2)).time()
        start_now_end = (now + timedelta(minutes=1)).time()

        # Discovery: Get actual tenants
        tenants = await self._discover_tenants()

        for tenant in tenants:
            try:
                # 1. Verify if 'meetings' table exists
                table_check = f"SHOW TABLES IN `{tenant}` LIKE 'meetings'"
                table_res = await db.execute_query(table_check, fetch_all=True)
                if not table_res:
                    continue

                has_sprint_id = await self._meetings_has_column(tenant, "sprint_id")
                sprint_select = "sprint_id" if has_sprint_id else "NULL AS sprint_id"

                # 2. Update status and Finalize (move to ended and save transcript)
                # Select meetings that SHOULD be ended but are still SCHEDULED or ONGOING
                to_end_query = f"""
                    SELECT meeting_id, project_id, {sprint_select}, title
                    FROM `{tenant}`.`meetings`
                    WHERE status IN ('SCHEDULED', 'ONGOING')
                    AND (meeting_date < %s OR (meeting_date = %s AND end_time <= %s))
                """
                to_end_meetings = await db.execute_query(to_end_query, (today, today, current_time), fetch_all=True)

                if to_end_meetings:
                    for mtg in to_end_meetings:
                        await self._finalize_meeting(tenant, mtg)

                # Update to ONGOING: (today AND start_time passed AND not yet ended)
                ongoing_query = f"""
                    UPDATE `{tenant}`.`meetings`
                    SET status = 'ONGOING'
                    WHERE status = 'SCHEDULED'
                    AND meeting_date = %s
                    AND start_time <= %s
                    AND end_time > %s
                """
                await db.execute_query(ongoing_query, (today, current_time, current_time), commit=True)

                # 3. Query scheduled meetings for reminder notifications
                query = f"""
                    SELECT meeting_id, project_id, {sprint_select}, title, start_time, meeting_link, status
                    FROM `{tenant}`.`meetings`
                    WHERE meeting_date = %s
                    AND status IN ('SCHEDULED', 'ONGOING')
                """
                meetings = await db.execute_query(query, (today,), fetch_all=True)
                
                if not meetings:
                    continue

                for mtg in meetings:
                    m_id = mtg['meeting_id']
                    start_time_val = mtg['start_time']
                    
                    # Convert start_time-val to time object (s_time)
                    if isinstance(start_time_val, timedelta):
                        s_time = (datetime.min + start_time_val).time()
                    elif isinstance(start_time_val, str):
                        try:
                            s_time = datetime.strptime(start_time_val, "%H:%M:%S").time()
                        except:
                            try:
                                s_time = datetime.strptime(start_time_val, "%H:%M").time()
                            except:
                                logger.error(f"Could not parse start_time: {start_time_val} for {tenant}.{m_id}")
                                continue
                    elif isinstance(start_time_val, time):
                        s_time = start_time_val
                    else:
                        if hasattr(start_time_val, 'hour'):
                            s_time = start_time_val # Probably time or datetime
                        else:
                            continue

                    # 1. 5-Minute Reminder (Catch if starting in the next 5 mins and not yet posted)
                    if current_time <= s_time <= reminder_time:
                        if (tenant, m_id) not in self.processed_meetings:
                            channel = await self._find_project_channel(tenant, mtg['project_id'])
                            if channel:
                                msg = (f"🔔 *UPCOMING MEETING* 🔔\n\n"
                                       f"The session **{mtg['title']}** is scheduled to start in **5 minutes**.\n\n"
                                       f"🗓️ *When:* Today at {s_time.strftime('%I:%M %p')}\n"
                                       f"🔗 *Meeting Link:* [Click here to join]({settings.FRONTEND_URL}{mtg['meeting_link']})")
                                
                                self.chat_service.send_message(channel['id'], "system", "AgileMind Bot", msg, "system")
                                self.processed_meetings.add((tenant, m_id))
                                logger.info(f"Posted 5-min reminder for meeting {m_id} (starts {s_time}) in {tenant}")
                            else:
                                logger.warning(f"Could not find chat channel for project {mtg['project_id']} in tenant {tenant}")

                    # 2. Happening Now Notification
                    if start_now_window <= s_time <= start_now_end:
                        if (tenant, m_id) not in self.started_meetings:
                            channel = await self._find_project_channel(tenant, mtg['project_id'])
                            if channel:
                                msg = (f"🏁 *MEETING STARTING NOW* 🏁\n\n"
                                       f"The meeting **{mtg['title']}** has officially started!\n\n"
                                       f"🔗 **Join Now:** {settings.FRONTEND_URL}{mtg['meeting_link']}\n"
                                       f"━━━━━━━━━━━━━━━━━━━━━━━━")
                                
                                self.chat_service.send_message(channel['id'], "system", "AgileMind Bot", msg, "system")
                                self.started_meetings.add((tenant, m_id))
                                logger.info(f"Posted 'Live Now' notification for meeting {m_id} in {tenant}")

            except Exception as e:
                # Log but continue with other tenants
                logger.error(f"Error scanning tenant {tenant}: {str(e)}")
                continue

        # Cache cleanup
        if len(self.processed_meetings) > 1000: self.processed_meetings.clear()
        if len(self.started_meetings) > 1000: self.started_meetings.clear()

    async def _find_project_channel(self, tenant_name: str, project_id: int) -> Optional[Dict[str, Any]]:
        """Find the main channel for a project"""
        channels = self.chat_service.get_tenant_channels(tenant_name)
        for channel in channels:
            if str(channel.get('project_id')) == str(project_id):
                return channel
        return None

    async def _discover_tenants(self) -> List[str]:
        """Discovery: Get actual tenants by looking for tenant databases/tables according to schema"""
        try:
            # According to database_schema.sql, tenants are identified by tables in information_schema
            # We look for databases that end in '_db' or are listed as tenant domains
            db_query = "SHOW DATABASES"
            all_dbs = await db.execute_query(db_query, fetch_all=True)
            
            # System databases to ignore
            excluded_dbs = ('information_schema', 'mysql', 'performance_schema', 'sys', 'agilemind_db', 'phpmyadmin', 'railway', 'test')
            
            tenants = []
            for d in all_dbs:
                db_name = list(d.values())[0]
                if db_name not in excluded_dbs:
                    # In this architecture, each tenant has a database (e.g., 'sliit', 'visionexdigital')
                    tenants.append(db_name)
            
            return tenants
        except Exception as e:
            logger.error(f"Tenant discovery failed: {e}")
            return []

    async def _meetings_has_column(self, tenant: str, column_name: str) -> bool:
        """Check if a tenant's meetings table has a given column."""
        try:
            column_query = """
                SELECT 1
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s
                  AND TABLE_NAME = 'meetings'
                  AND COLUMN_NAME = %s
                LIMIT 1
            """
            result = await db.execute_query(column_query, (tenant, column_name), fetch_all=True)
            return bool(result)
        except Exception as e:
            logger.warning(f"Column check failed for {tenant}.meetings.{column_name}: {e}")
            return False

    async def _finalize_meeting(self, tenant: str, meeting_data: Dict[str, Any]):
        """Mark as ENDED in SQL/Redis and attempt to save transcript"""
        m_id = meeting_data['meeting_id']
        project_id = meeting_data.get('project_id')
        sprint_id = meeting_data.get('sprint_id')
        title = meeting_data.get('title', 'Untitled Meeting')
        
        logger.info(f"Finalizing meeting {m_id} in {tenant} (Time Passed)")

        # 1. Update SQL Status
        update_sql = f"UPDATE `{tenant}`.`meetings` SET status = 'ENDED' WHERE meeting_id = %s"
        await db.execute_query(update_sql, (m_id,), commit=True)

        # 2. Sync with Redis (End session)
        try:
            meeting_service = get_meeting_service()
            
            # 2.1 Get full participant details (including emails) BEFORE ending
            participants = meeting_service.get_participants(m_id)
            attendees_data = [] # List of {username, email}
            for p in participants:
                attendees_data.append({
                    'username': p.get('username'),
                    'email': p.get('email', '')
                })

            meeting_service.end_meeting(
                meeting_id=m_id,
                tenant_name=tenant,
                user_id="system",
                username="AgileMind Bot"
            )
            
            # 3. Enhanced Transcript Capture (Prioritize 'Speaking things')
            # 3.1 Try to get speech segments from Redis first
            speech_key = f"meeting:{m_id}:speech_segments"
            speech_json_list = meeting_service.redis.get_list_range(speech_key, 0, -1)
            
            transcript_content = ""
            if speech_json_list:
                import json
                speech_segments = [json.loads(s) for s in speech_json_list]
                transcript_content = self._generate_transcript_from_messages(speech_segments)
                logger.info(f"Generated speaker-based transcript for {m_id}")
            else:
                # 3.2 Fallback to chat messages if no speech recorded
                channel_id = meeting_data.get('channel_id')
                if not channel_id:
                    channel = await self._find_project_channel(tenant, project_id)
                    channel_id = channel['id'] if channel else None

                if channel_id:
                    messages = self.chat_service.get_messages(channel_id, limit=500)
                    transcript_content = self._generate_transcript_from_messages(messages)
                    logger.info(f"Fallback to chat transcript for {m_id}")

            if transcript_content:
                # Unified Store: This adds to BOTH Redis (for chat) and MySQL (for history)
                # It also internally handles the transcript table deduplication
                await meeting_service.store_transcript(
                    meeting_id=m_id,
                    content=transcript_content,
                    tenant_name=tenant,
                    user_id="system",
                    username="AgileMind Bot",
                    metadata={
                        'project_id': project_id,
                        'sprint_id': sprint_id,
                        'category': 'automatic_finalize'
                    }
                )
                
                # Update attendees WITH EMAILS in the meetings table
                if attendees_data:
                    import json
                    update_attendees_sql = f"UPDATE `{tenant}`.`meetings` SET attendees = %s WHERE meeting_id = %s"
                    await db.execute_query(update_attendees_sql, (json.dumps(attendees_data), m_id), commit=True)
                
                logger.info(f"Finalized meeting {m_id} (Stored in Redis + MySQL)")
        except Exception as e:
            logger.error(f"Failed to finalize transcript for meeting {m_id}: {e}")

    def _generate_transcript_from_messages(self, messages: List[Dict[str, Any]]) -> str:
        """Format chat messages into a readable transcript"""
        lines = []
        # messages are newest first from get_messages
        for msg in reversed(messages):
            ts = msg.get('created_at', '').split('T')[-1][:5] # HH:MM
            user = msg.get('username', 'Unknown')
            text = msg.get('content', '')
            if text and msg.get('type') != 'system':
                lines.append(f"[{ts}] {user}: {text}")
        return "\n".join(lines) if lines else "No discussion recorded."

# Singleton access
def get_meeting_scheduler_service():
    return MeetingSchedulerService.get_instance()
