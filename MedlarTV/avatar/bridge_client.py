import json, os
from websockets.sync.client import connect
from websockets.exceptions import WebSocketException  # ← add

BRIDGE_URL = os.getenv("BRIDGE_URL", "ws://127.0.0.1:8765")

def ws_send(payload: dict):
    try:
        with connect(BRIDGE_URL) as ws:
            ws.send(json.dumps(payload))
    except WebSocketException as e:
        print(f"[BridgeClient] WebSocket error: {e}")
    except Exception as e:
        print(f"[BridgeClient] ⚠️ send failed: {e}")


def register_channel(channel: str, platform: str = "twitch"):
    ws_send({
        "event": "register",
        "platform": platform,
        "channel": channel,
    })

def send_mood_update(mood: str):
    ws_send({
        "event": "mood_update",
        "mood": mood,
    })