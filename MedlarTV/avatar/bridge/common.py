"""
Bridge Common - Shared constants and types
"""

from enum import Enum
from typing import TypedDict, Literal

class BridgeEvent(str, Enum):
    """Bridge event types"""
    HANDSHAKE = "handshake"
    REGISTER = "register"
    UNREGISTER = "unregister"
    MOOD_UPDATE = "mood_update"
    CHAT_MESSAGE = "chat_message"
    SYSTEM_EVENT = "system_event"


MESSAGE_TYPES = Literal["handshake", "register", "unregister", "mood_update", "chat_message", "system_event"]


class BridgeMessage(TypedDict, total=False):
    """Bridge message structure"""
    event: str
    channel: str
    mood: str
    msg: str
    platform: str
    data: dict
