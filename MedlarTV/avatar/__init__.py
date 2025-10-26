"""
MedlarTV Avatar Module
WebSocket bridge for real-time communication between components.
"""

from .bridge_client import (
    start_bridge_loop,
    ws_send,
    register_channel,
    send_mood_update
)

__all__ = [
    'start_bridge_loop',
    'ws_send',
    'register_channel',
    'send_mood_update',
]
