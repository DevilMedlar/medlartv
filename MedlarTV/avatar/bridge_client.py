import os
import json
import time
import traceback
from websockets.sync.client import connect
from websockets.exceptions import WebSocketException, ConnectionClosed

BRIDGE_URL = os.getenv("BRIDGE_URL", "ws://127.0.0.1:8765")
RECONNECT_DELAY = 5  # seconds

def start_bridge_loop():
    """Persistent connection to MedlarTV Core bridge."""
    print(f"[Bridge] 🚀 Starting Avatar Bridge at {BRIDGE_URL}")

    while True:
        try:
            with connect(BRIDGE_URL) as ws:
                print("[Bridge] 🔗 Connected to MedlarTV Core!")
                ws.send(json.dumps({"event": "register", "platform": "twitch", "channel": "MedlarTV"}))

                while True:
                    try:
                        msg = ws.recv()
                        if msg:
                            print(f"[Bridge] 💬 {msg}")
                    except ConnectionClosed:
                        print("[Bridge] ⚠️ Connection closed by server. Reconnecting...")
                        break
                    except Exception as e:
                        print(f"[Bridge] ⚠️ Error receiving message: {e}")
                        traceback.print_exc()
                        break

        except (ConnectionRefusedError, WebSocketException) as e:
            print(f"[Bridge] ❌ Connection failed: {e}")
        except Exception as e:
            print(f"[Bridge] 🧨 Unexpected error: {e}")
            traceback.print_exc()

        print(f"[Bridge] ⏳ Retrying connection in {RECONNECT_DELAY}s...")
        time.sleep(RECONNECT_DELAY)


def ws_send(payload: dict):
    """One-shot send (optional, used by tools)."""
    try:
        with connect(BRIDGE_URL) as ws:
            ws.send(json.dumps(payload))
    except Exception as e:
        print(f"[BridgeClient] ⚠️ send failed: {e}")


def register_channel(channel: str, platform: str = "twitch"):
    ws_send({"event": "register", "platform": platform, "channel": channel})


def send_mood_update(mood: str):
    ws_send({"event": "mood_update", "mood": mood})


if __name__ == "__main__":
    start_bridge_loop()