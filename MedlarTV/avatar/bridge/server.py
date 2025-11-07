import asyncio
import websockets
import json
import time

ACTIVE_CONNECTIONS = set()
CHANNEL_REGISTRY = {}  # track which Twitch channels are connected

# --- Client Management ---
async def register(websocket):
    ACTIVE_CONNECTIONS.add(websocket)
    print(f"[Bridge] ✓ Connected ({len(ACTIVE_CONNECTIONS)})")
    await websocket.send(json.dumps({"event": "handshake", "msg": "connected"}))


async def unregister(websocket):
    if websocket in ACTIVE_CONNECTIONS:
        ACTIVE_CONNECTIONS.remove(websocket)
        # remove this websocket from any channels it was linked to
        for channel, sockets in list(CHANNEL_REGISTRY.items()):
            if websocket in sockets:
                sockets.remove(websocket)
                if not sockets:
                    del CHANNEL_REGISTRY[channel]
        print(f"[Bridge] ✗ Disconnected ({len(ACTIVE_CONNECTIONS)})")


# --- Broadcasting ---
async def broadcast(payload: dict, channel: str | None = None):
    """Send event to all connected clients, or only one Twitch channel.
       Includes retry logic to wait briefly for late connections."""
    targets = (
        CHANNEL_REGISTRY.get(channel.lower(), [])
        if channel
        else ACTIVE_CONNECTIONS
    )

    if not targets:
        print(f"[Bridge] No targets for {channel or 'global'} broadcast. Waiting...")
        for _ in range(5):  # wait up to ~5 seconds total
            await asyncio.sleep(1)
            targets = (
                CHANNEL_REGISTRY.get(channel.lower(), [])
                if channel
                else ACTIVE_CONNECTIONS
            )
            if targets:
                break
        if not targets:
            print(f"[Bridge] Still no targets after wait, skipping broadcast.")
            return

    msg = json.dumps(payload)
    print(f"[Bridge] 📡 Sending → {payload}")

    try:
        await asyncio.gather(*(ws.send(msg) for ws in list(targets)))
        print("[Bridge] ✓ Broadcast sent successfully.")
    except Exception as e:
        print(f"[Bridge] ✗ broadcast error: {e}")


# --- Connection Handler ---
async def handler(websocket):
    await register(websocket)
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                print(f"[Bridge] Invalid JSON (truncated): {message[:120]}")
                continue

            event = data.get("event")

            if event == "register":
                channel = data.get("channel", "").lower()
                if channel:
                    CHANNEL_REGISTRY.setdefault(channel, []).append(websocket)
                    print(f"[Bridge] ✓ Channel registered: {channel}")

            elif event == "unregister":
                channel = data.get("channel", "").lower()
                if channel and channel in CHANNEL_REGISTRY:
                    if websocket in CHANNEL_REGISTRY[channel]:
                        CHANNEL_REGISTRY[channel].remove(websocket)
                        print(f"[Bridge] ✗ Channel unregistered: {channel}")
                        if not CHANNEL_REGISTRY[channel]:
                            del CHANNEL_REGISTRY[channel]

            elif event == "mood_update":
                mood = data.get("mood")
                channel = data.get("channel")
                await broadcast({"event": "mood_update", "mood": mood}, channel)

            else:
                print(f"[Bridge] Unknown event: {data}")

    finally:
        await unregister(websocket)


# --- ✅ Async Server Runner (safe for FastAPI) ---
async def run_server(host="0.0.0.0", port=8765):
    """Run the WebSocket bridge server inside an existing asyncio loop."""
    print(f"[Bridge] Listening on ws://{host}:{port}")
    async with websockets.serve(handler, host, port):
        await asyncio.Future()  # run forever


# --- Optional standalone entrypoint ---
if __name__ == "__main__":
    asyn
