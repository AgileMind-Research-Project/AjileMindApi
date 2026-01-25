"""
WebSocket Server for Real-Time Meeting Communication

Handles:
- Meeting room management
- WebRTC signaling (offer/answer/ICE)
- Participant status broadcasting
- Chat message relay
- Meeting transcript collection and storage
"""

import socketio
import logging
from typing import Dict, Set, List
from datetime import datetime
import json
import os

logger = logging.getLogger(__name__)

# Import CORS origins from settings to use the same config
from app.core.config import settings
from app.services.meeting_service import get_meeting_service

# Get CORS origins
cors_origins = settings.CORS_ORIGINS
if isinstance(cors_origins, str):
    cors_origins = [origin.strip() for origin in cors_origins.split(',')]

# Redis manager for multi-server Socket.IO
redis_host = os.getenv('REDIS_HOST', 'localhost')
redis_port = os.getenv('REDIS_PORT', '6379')
redis_password = os.getenv('REDIS_PASSWORD', '')
redis_db = os.getenv('REDIS_DB', '0')
if redis_password:
    redis_url = f'redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}'
else:
    redis_url = f'redis://{redis_host}:{redis_port}/{redis_db}'
logger.info(f'?? Socket.IO Redis: {redis_host}:{redis_port}')
mgr = socketio.AsyncRedisManager(redis_url)

# Redis manager for multi-server Socket.IO
redis_host = os.getenv('REDIS_HOST', 'localhost')
redis_port = os.getenv('REDIS_PORT', '6379')
redis_password = os.getenv('REDIS_PASSWORD', '')
redis_db = os.getenv('REDIS_DB', '0')
if redis_password:
    redis_url = f'redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}'
else:
    redis_url = f'redis://{redis_host}:{redis_port}/{redis_db}'
logger.info(f'?? Socket.IO Redis: {redis_host}:{redis_port}')
mgr = socketio.AsyncRedisManager(redis_url)

# Create Socket.IO server
# IMPORTANT: Disable Socket.IO's CORS - let FastAPI's CORSMiddleware handle ALL CORS
# This prevents duplicate Access-Control-Allow-Origin headers which browsers reject
sio = socketio.AsyncServer(
    # CORS is handled by FastAPI's CORSMiddleware wrapping the app
    # Setting this to empty list prevents Socket.IO from adding a DUPLICATE header
    # which causes the "multiple values" CORS error in browsers
    cors_allowed_origins=[], 
    async_mode='asgi',
    logger=True,
    engineio_logger=True,
    ping_timeout=60,
    ping_interval=25
)

# Track active meetings and participants
# meeting_id -> Set of session IDs
active_meetings: Dict[str, Set[str]] = {}
# session_id -> {meeting_id, user_id, username}
session_data: Dict[str, dict] = {}
# meeting_id -> List of chat messages for transcript
meeting_transcripts: Dict[str, List[dict]] = {}


# ==================== Helper Functions ====================

def get_meeting_data(meeting_id: str) -> dict:
    """Get meeting data from Redis"""
    try:
        meeting_service = get_meeting_service()
        meeting = meeting_service.get_meeting(meeting_id)
        return meeting or {}
    except Exception as e:
        logger.error(f"Failed to get meeting data: {e}")
        return {}


async def save_meeting_transcript(meeting_id: str):
    """Save meeting transcript to Redis"""
    try:
        meeting_service = get_meeting_service()
        
        # Get transcript messages
        messages = meeting_transcripts.get(meeting_id, [])
        
        if not messages:
            logger.info(f"No transcript to save for meeting {meeting_id}")
            return
        
        # Format transcript
        transcript_lines = []
        transcript_lines.append(f"Meeting Transcript - {meeting_id}")
        transcript_lines.append(f"Generated: {datetime.utcnow().isoformat()}")
        transcript_lines.append("=" * 80)
        transcript_lines.append("")
        
        for msg in messages:
            timestamp = msg.get('timestamp', '')
            username = msg.get('username', 'Unknown')
            message = msg.get('message', '')
            transcript_lines.append(f"[{timestamp}] {username}: {message}")
        
        transcript_content = "\n".join(transcript_lines)
        
        # Get meeting info for metadata
        meeting = get_meeting_data(meeting_id)
        
        metadata = {
            'message_count': len(messages),
            'participants': list(set(msg.get('username', 'Unknown') for msg in messages)),
            'duration': 'Session ended',
            'ended_at': datetime.utcnow().isoformat()
        }
        
        # Store in Redis
        result = meeting_service.store_transcript(
            meeting_id=meeting_id,
            content=transcript_content,
            format='text',
            metadata=metadata
        )
        
        if result:
            logger.info(f"✅ Saved transcript for meeting {meeting_id} ({len(messages)} messages)")
            # Clean up in-memory transcript
            if meeting_id in meeting_transcripts:
                del meeting_transcripts[meeting_id]
        else:
            logger.error(f"❌ Failed to save transcript for meeting {meeting_id}")
            
    except Exception as e:
        logger.error(f"Error saving transcript: {e}", exc_info=True)


@sio.event
async def connect(sid, environ):
    """Client connected"""
    logger.info(f"🔌 Client connected: {sid}")


@sio.event
async def disconnect(sid):
    """Client disconnected"""
    logger.info(f"🔌 Client disconnected: {sid}")
    
    # Clean up session
    if sid in session_data:
        data = session_data[sid]
        meeting_id = data.get('meeting_id')
        username = data.get('username')
        user_id = data.get('user_id')
        
        # Remove from meeting
        if meeting_id and meeting_id in active_meetings:
            active_meetings[meeting_id].discard(sid)
            
            # Notify others
            await sio.emit(
                'user-left',
                {
                    'user_id': user_id,
                    'username': username
                },
                room=meeting_id,
                skip_sid=sid
            )
            
            logger.info(f"👤 User left meeting: {username} from {meeting_id}")
            
            # Check if meeting is now empty - save transcript if last participant
            if len(active_meetings[meeting_id]) == 0:
                logger.info(f"📝 Last participant left, saving meeting transcript for {meeting_id}")
                await save_meeting_transcript(meeting_id)
                # Clean up empty meeting
                del active_meetings[meeting_id]
        
        del session_data[sid]


@sio.event
async def join_meeting(sid, data):
    """User joins a meeting"""
    logger.info(f"📥 RECEIVED join_meeting event from {sid}")
    logger.info(f"📥 Data: {data}")
    
    meeting_id = data.get('meeting_id')
    user_id = data.get('user_id')
    username = data.get('username')
    
    if not all([meeting_id, user_id, username]):
        logger.error(f"❌ Invalid join data: {data}")
        return
    
    # Get meeting data to retrieve channel_id
    meeting = get_meeting_data(meeting_id)
    channel_id = meeting.get('channel_id') if meeting else None
    
    # Store session data with channel_id and initial media status
    session_data[sid] = {
        'meeting_id': meeting_id,
        'user_id': user_id,
        'username': username,
        'channel_id': channel_id,  # Store channel_id for chat sync
        'mic_enabled': True,       # Track mic status (default on)
        'camera_enabled': True     # Track camera status (default on)
    }
    
    # Add to meeting room
    await sio.enter_room(sid, meeting_id)
    
    
    # Track in active meetings
    if meeting_id not in active_meetings:
        active_meetings[meeting_id] = set()
    active_meetings[meeting_id].add(sid)
    
    # Get list of existing participants (excluding the new user) WITH their media status
    existing_participants = []
    for existing_sid in active_meetings[meeting_id]:
        if existing_sid != sid and existing_sid in session_data:
            existing_data = session_data[existing_sid]
            existing_participants.append({
                'user_id': existing_data['user_id'],
                'username': existing_data['username'],
                'session_id': existing_sid,
                'mic_enabled': existing_data.get('mic_enabled', True),
                'camera_enabled': existing_data.get('camera_enabled', True)
            })
    
    # Send existing participants to the new user (with their current media status)
    if existing_participants:
        await sio.emit(
            'existing-participants',
            {'participants': existing_participants},
            room=sid
        )
        logger.info(f"📋 Sent {len(existing_participants)} existing participants to {username} (with media status)")
    
    # Notify others in the room about the new user (with their initial media status)
    logger.info(f"📤 EMITTING user-joined to room {meeting_id} (skip {sid})")
    await sio.emit(
        'user-joined',
        {
            'user_id': user_id,
            'username': username,
            'session_id': sid,
            'mic_enabled': True,    # New user starts with mic on
            'camera_enabled': True  # New user starts with camera on
        },
        room=meeting_id,
        skip_sid=sid
    )
    
    logger.info(f"✅ User joined meeting: {username} ({user_id}) in {meeting_id}")
    if channel_id:
        logger.info(f"📍 Associated with channel: {channel_id}")
    logger.info(f"📊 Meeting {meeting_id} now has {len(active_meetings[meeting_id])} participants")


@sio.event
async def offer(sid, data):
    """
    WebRTC offer from one peer to another
    
    Data: {
        'to': session_id,
        'offer': SDP offer object
    }
    """
    logger.info(f"📥 RECEIVED offer from {sid}")
    logger.info(f"📥 Offer data keys: {data.keys()}")
    
    to_sid = data.get('to')
    offer_data = data.get('offer')
    
    if to_sid and offer_data:
        # Get sender info
        sender = session_data.get(sid, {})
        
        await sio.emit(
            'offer',
            {
                'from': sid,
                'user_id': sender.get('user_id'),
                'username': sender.get('username'),
                'offer': offer_data
            },
            room=to_sid
        )
        logger.info(f"📤 Relayed offer: {sid} -> {to_sid}")


@sio.event
async def answer(sid, data):
    """
    WebRTC answer from peer
    
    Data: {
        'to': session_id,
        'answer': SDP answer object
    }
    """
    logger.info(f"📥 RECEIVED answer from {sid}")
    logger.info(f"📥 Answer to: {data.get('to')}")
    
    to_sid = data.get('to')
    answer_data = data.get('answer')
    
    if to_sid and answer_data:
        await sio.emit(
            'answer',
            {
                'from': sid,
                'answer': answer_data
            },
            room=to_sid
        )
        logger.info(f"📤 Relayed answer: {sid} -> {to_sid}")


@sio.event
async def ice_candidate(sid, data):
    """
    ICE candidate exchange
    
    Data: {
        'to': session_id,
        'candidate': ICE candidate object
    }
    """
    to_sid = data.get('to')
    candidate = data.get('candidate')
    
    if to_sid and candidate:
        await sio.emit(
            'ice-candidate',
            {
                'from': sid,
                'candidate': candidate
            },
            room=to_sid
        )
        logger.debug(f"🧊 Relayed ICE: {sid} -> {to_sid}")


@sio.event
async def chat_message(sid, data):
    """
    Broadcast chat message to all in meeting
    
    Data: {
        'message': string,
        'timestamp': string (optional)
    }
    """
    if sid not in session_data:
        return
    
    sender = session_data[sid]
    meeting_id = sender['meeting_id']
    channel_id = sender.get('channel_id')
    
    message_data = {
        'user_id': sender['user_id'],
        'username': sender['username'],
        'message': data.get('message'),
        'timestamp': data.get('timestamp') or datetime.utcnow().isoformat()
    }
    
    # Store message for transcript
    if meeting_id not in meeting_transcripts:
        meeting_transcripts[meeting_id] = []
    meeting_transcripts[meeting_id].append(message_data)
    
    # NEW: Also save to channel chat if channel is linked
    if channel_id:
        try:
            from app.services.redis_chat_service import get_redis_chat_service
            chat_service = get_redis_chat_service()
            
            chat_service.send_message(
                channel_id=channel_id,
                user_id=sender['user_id'],
                username=sender['username'],
                content=data.get('message'),
                message_type='meeting_chat',  # Mark as meeting message
                metadata={
                    'meeting_id': meeting_id,
                    'timestamp': message_data['timestamp'],
                    'source': 'meeting'
                }
            )
            logger.info(f"💬 Saved meeting message to channel {channel_id}")
        except Exception as e:
            logger.error(f"Failed to save message to channel chat: {e}")
    
    # Broadcast to all in meeting (including sender)
    await sio.emit('chat-message', message_data, room=meeting_id)
    logger.info(f"💬 Chat from {sender['username']}: {data.get('message')[:50]}...")


@sio.event
async def mic_toggle(sid, data):
    """Broadcast mic status change"""
    if sid not in session_data:
        return
    
    sender = session_data[sid]
    meeting_id = sender['meeting_id']
    enabled = data.get('enabled', True)
    
    # Track status in session data for new joiners
    sender['mic_enabled'] = enabled
    
    await sio.emit(
        'mic-toggle',
        {
            'user_id': sender['user_id'],
            'enabled': enabled
        },
        room=meeting_id,
        skip_sid=sid
    )
    logger.info(f"🎤 {sender['username']} mic: {enabled}")


@sio.event
async def camera_toggle(sid, data):
    """Broadcast camera status change"""
    if sid not in session_data:
        return
    
    sender = session_data[sid]
    meeting_id = sender['meeting_id']
    enabled = data.get('enabled', True)
    
    # Track status in session data for new joiners
    sender['camera_enabled'] = enabled
    
    await sio.emit(
        'camera-toggle',
        {
            'user_id': sender['user_id'],
            'enabled': enabled
        },
        room=meeting_id,
        skip_sid=sid
    )
    logger.info(f"📹 {sender['username']} camera: {enabled}")


@sio.event
async def speaking(sid, data):
    """Broadcast speaking status to other participants"""
    if sid not in session_data:
        return
    
    sender = session_data[sid]
    meeting_id = sender['meeting_id']
    is_speaking = data.get('speaking', False)
    
    await sio.emit(
        'user-speaking',
        {
            'user_id': sender['user_id'],
            'username': sender['username'],
            'speaking': is_speaking
        },
        room=meeting_id,
        skip_sid=sid  # Don't send back to the speaker
    )
    # Only log when someone starts speaking (not stops) to reduce log noise
    if is_speaking:
        logger.debug(f"🗣️ {sender['username']} is speaking")


@sio.event
async def screen_share_toggle(sid, data):
    """Broadcast screen share status change"""
    if sid not in session_data:
        return
    
    sender = session_data[sid]
    meeting_id = sender['meeting_id']
    
    await sio.emit(
        'screen-share-toggle',
        {
            'user_id': sender['user_id'],
            'enabled': data.get('enabled')
        },
        room=meeting_id,
        skip_sid=sid
    )
    logger.info(f"🖥️ {sender['username']} screen share: {data.get('enabled')}")


# ==================== Meeting Data & Transcript Events ====================

@sio.event
async def get_meeting_info(sid, data):
    """
    Get real-time meeting information from Redis
    
    Data: {
        'meeting_id': string
    }
    
    Returns meeting data to the requesting client
    """
    try:
        meeting_id = data.get('meeting_id')
        if not meeting_id:
            await sio.emit('meeting-info-error', {'error': 'Meeting ID required'}, room=sid)
            return
        
        # Get meeting data from Redis
        meeting = get_meeting_data(meeting_id)
        
        if meeting:
            # Get participant count from active connections
            participant_count = len(active_meetings.get(meeting_id, set()))
            meeting['active_participant_count'] = participant_count
            
            await sio.emit('meeting-info', meeting, room=sid)
            logger.info(f"📊 Sent meeting info for {meeting_id} to {sid}")
        else:
            await sio.emit('meeting-info-error', {'error': 'Meeting not found'}, room=sid)
            
    except Exception as e:
        logger.error(f"Error getting meeting info: {e}")
        await sio.emit('meeting-info-error', {'error': str(e)}, room=sid)


@sio.event
async def save_transcript(sid, data):
    """
    Manually save meeting transcript to Redis
    
    Data: {
        'meeting_id': string (optional, uses current session if not provided)
    }
    """
    try:
        # Get meeting_id from data or current session
        meeting_id = data.get('meeting_id')
        
        if not meeting_id and sid in session_data:
            meeting_id = session_data[sid].get('meeting_id')
        
        if not meeting_id:
            await sio.emit('save-transcript-error', {'error': 'Meeting ID required'}, room=sid)
            return
        
        # Save transcript
        await save_meeting_transcript(meeting_id)
        
        await sio.emit('save-transcript-success', {
            'meeting_id': meeting_id,
            'saved_at': datetime.utcnow().isoformat()
        }, room=sid)
        
        logger.info(f"📝 Manually saved transcript for meeting {meeting_id}")
        
    except Exception as e:
        logger.error(f"Error saving transcript: {e}")
        await sio.emit('save-transcript-error', {'error': str(e)}, room=sid)


# Create ASGI app
# When mounted at /socket.io in FastAPI, set socketio_path to empty
# This tells Socket.IO that FastAPI already handles the /socket.io prefix
socket_app = socketio.ASGIApp(
    sio,
    socketio_path='',  # Empty because FastAPI mounts at /socket.io
)
