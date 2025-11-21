import os
import json
import time
import traceback
from websockets.sync.client import connect
from websockets.exceptions import WebSocketException, ConnectionClosed

print("[DEBUG bridge_client] Module import complete")

BRIDGE_URL = os.getenv("BRIDGE_URL", "ws://127.0.0.1:8765")
RECONNECT_DELAY = 5  # seconds

print(f"[DEBUG bridge_client] BRIDGE_URL={BRIDGE_URL}")
print(f"[DEBUG bridge_client] RECONNECT_DELAY={RECONNECT_DELAY}")


def start_bridge_loop():
    """Persistent connection to MedlarTV Core bridge."""
    print("[DEBUG bridge_client] start_bridge_loop() ENTER")
    print(f"[Bridge] Starting Avatar Bridge at {BRIDGE_URL}")

    while True:
        print("[DEBUG bridge_client] Top of persistent WHILE TRUE loop — attempting connection…")
        try:
            print(f"[DEBUG bridge_client] Calling connect({BRIDGE_URL!r})")
            with connect(BRIDGE_URL) as ws:
                print("[DEBUG bridge_client] WebSocket CONNECTED successfully")
                print("[Bridge] Connected to MedlarTV Core!")

                payload = {"event": "register", "platform": "twitch", "channel": "MedlarTV"}
                payload_str = json.dumps(payload)
                print(f"[DEBUG bridge_client] Sending registration payload={payload_str}")
                ws.send(payload_str)

                while True:
                    print("[DEBUG bridge_client] Waiting for ws.recv()…")
                    try:
                        msg = ws.recv()
                        print(f"[DEBUG bridge_client] ws.recv() returned {msg!r}")

                        if msg:
                            print(f"[DEBUG bridge_client] Non-empty message received → printing to user")
                            print(f"[Bridge] {msg}")
                        else:
                            print("[DEBUG bridge_client] Empty message received (rare case)")

                    except ConnectionClosed:
                        print("[DEBUG bridge_client] ConnectionClosed EXCEPTION caught")
                        print("[Bridge] Connection closed by server. Reconnecting...")
                        break

                    except Exception as e:
                        print(f"[DEBUG bridge_client] General EXCEPTION in inner recv-loop: {e}")
                        print(f"[Bridge] Error receiving message: {e}")
                        traceback.print_exc()
                        break

        except (ConnectionRefusedError, WebSocketException) as e:
            print(f"[DEBUG bridge_client] ConnectionRefusedError/WebSocketException caught: {e}")
            print(f"[Bridge] Connection failed: {e}")

        except Exception as e:
            print(f"[DEBUG bridge_client] Unexpected EXCEPTION in connection block: {e}")
            print(f"[Bridge] Unexpected error: {e}")
            traceback.print_exc()

        print(f"[DEBUG bridge_client] Sleeping RECONNECT_DELAY={RECONNECT_DELAY}")
        print(f"[Bridge] Retrying connection in {RECONNECT_DELAY}s...")
        time.sleep(RECONNECT_DELAY)


def ws_send(payload: dict):
    """One-shot send (optional, used by tools)."""
    print("[DEBUG bridge_client] ws_send() ENTER")
    print(f"[DEBUG bridge_client] Raw payload={payload}")

    try:
        print(f"[DEBUG bridge_client] Connecting for one-shot send to {BRIDGE_URL!r}")
        with connect(BRIDGE_URL) as ws:
            payload_str = json.dumps(payload)
            print(f"[DEBUG bridge_client] Sending JSON={payload_str}")
            ws.send(payload_str)
            print("[DEBUG bridge_client] One-shot send complete")

    except Exception as e:
        print(f"[DEBUG bridge_client] EXCEPTION in ws_send(): {e}")
        print(f"[BridgeClient] send failed: {e}")


def register_channel(channel: str, platform: str = "twitch"):
    print("[DEBUG bridge_client] register_channel() ENTER")
    print(f"[DEBUG bridge_client] channel={channel!r} platform={platform!r}")
    ws_send({"event": "register", "platform": platform, "channel": channel})


def send_mood_update(mood: str):
    print("[DEBUG bridge_client] send_mood_update() ENTER")
    print(f"[DEBUG bridge_client] mood={mood!r}")
    ws_send({"event": "mood_update", "mood": mood})


def is_bridge_available() -> bool:
    try:
        with connect(BRIDGE_URL):
            return True
    except Exception:
        return False


if __name__ == "__main__":
    print("[DEBUG bridge_client] __main__ invoked — calling start_bridge_loop()")
    start_bridge_loop()
