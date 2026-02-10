"""WebSocket module for real-time meeting communication"""

from .socket_server import sio, socket_app

__all__ = ['sio', 'socket_app']
