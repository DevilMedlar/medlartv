import asyncio
import websockets
import json
import time

print("[DEBUG bridge_server] Module import started")

ACTIVE_CONNECTIONS = set()
CHANNEL_REGISTRY = {}

print("[DEBUG bridge_server] ACTIVE_CONNECTIONS initialized (empty set)")
print("[DEBUG bridge_server] CHANNEL_REGISTRY initialized (empty dict)")


# --- Client Management ---
async def register(websocket):
    print("[DEBUG register] Called with websocket:", websocket)
    ACTIVE_CONNECTIONS.add(websocket)
    print(f"[DEBUG register] ACTIVE_CONNECTIONS size is now {len(ACTIVE_CONNECTIONS)}")
    payload = {"event": "handshake", "msg": "connected"}
    print(f"[DEBUG register] Sending handshake payload: {payload}")
    await websocket.send(json.dumps(payload))
    print("[DEBUG register] Handshake sent successfully")


async def unregister(websocket):
    print("[DEBUG unregister] Called with websocket:", websocket)
    if websocket in ACTIVE_CONNECTIONS:
        print("[DEBUG unregister] Websocket is active, removing")
        ACTIVE_CONNECTIONS.remove(websocket)
        print(f"[DEBUG unregister] ACTIVE_CONNECTIONS size after removal: {len(ACTIVE_CONNECTIONS)}")

        # Remove from channels
        print("[DEBUG unregister] Checking CHANNEL_REGISTRY for websocket entries")
        for channel, sockets in list(CHANNEL_REGISTRY.items()):
            print(f"[DEBUG unregister] Inspecting channel '{channel}' with {len(sockets)} sockets")
            if websocket in sockets:
                print(f"[DEBUG unregister] Found websocket in channel '{channel}', removing")
                sockets.remove(websocket)
                if not sockets:
                    print(f"[DEBUG unregister] Channel '{channel}' now empty, deleting")
                    del CHANNEL_REGISTRY[channel]
    else:
        print("[DEBUG unregister] Websocket was not in ACTIVE_CONNECTIONS")

    print(f"[DEBUG unregister] Unregister complete; active={len(ACTIVE_CONNECTIONS)}")


# --- Broadcasting ---
async def broadcast(payload: dict, channel: str | None = None):
    print("[DEBUG broadcast] Called with payload:", payload, "channel:", channel)

    if channel:
        key = channel.lower()
        print(f"[DEBUG broadcast] Looking for channel '{key}'")
        targets = CHANNEL_REGISTRY.get(key, [])
        print(f"[DEBUG broadcast] Found {len(targets)} channel targets")
    else:
        print("[DEBUG broadcast] Global broadcast mode")
        targets = ACTIVE_CONNECTIONS
        print(f"[DEBUG broadcast] Global targets={len(targets)}")

    # Zero-target wait logic
    if not targets:
        print(f"[DEBUG broadcast] No targets for {channel or 'global'} broadcast. Entering wait loop.")
        for i in range(5):
            print(f"[DEBUG broadcast] Wait iteration {i+1}/5")
            await asyncio.sleep(1)
            if channel:
                targets = CHANNEL_REGISTRY.get(channel.lower(), [])
            else:
                targets = ACTIVE_CONNECTIONS
            print(f"[DEBUG broadcast] Re-check found {len(targets)} targets")
            if targets:
                break

        if not targets:
            print("[DEBUG broadcast] Still no targets after wait; aborting broadcast")
            return

    msg = json.dumps(payload)
    print(f"[DEBUG broadcast] Final send target count: {len(targets)}")
    print(f"[DEBUG broadcast] Serialized message: {msg}")

    try:
        print("[DEBUG broadcast] Sending to all targets via asyncio.gather")
        await asyncio.gather(*(ws.send(msg) for ws in list(targets)))
        print("[DEBUG broadcast] Broadcast completed successfully")
    except Exception as e:
        print(f"[DEBUG broadcast] ERROR during broadcast: {e}")


# --- Connection Handler ---
async def handler(websocket):
    print("[DEBUG handler] New websocket connection:", websocket)
    await register(websocket)
    print("[DEBUG handler] Register complete, entering receive loop")

    try:
        async for message in websocket:
            print(f"[DEBUG handler] Received raw message: {message!r}")
            try:
                data = json.loads(message)
                print("[DEBUG handler] JSON decoded:", data)
            except json.JSONDecodeError:
                print(f"[DEBUG handler] Invalid JSON (showing first 120 chars): {message[:120]}")
                continue

            event = data.get("event")
            print("[DEBUG handler] Event extracted:", event)

            if event == "register":
                channel = data.get("channel", "").lower()
                print("[DEBUG handler] register event, channel:", channel)
                if channel:
                    CHANNEL_REGISTRY.setdefault(channel, []).append(websocket)
                    print(f"[DEBUG handler] Channel '{channel}' registry now has {len(CHANNEL_REGISTRY[channel])} sockets")

            elif event == "unregister":
                channel = data.get("channel", "").lower()
                print("[DEBUG handler] unregister event, channel:", channel)
                if channel and channel in CHANNEL_REGISTRY:
                    if websocket in CHANNEL_REGISTRY[channel]:
                        CHANNEL_REGISTRY[channel].remove(websocket)
                        print(f"[DEBUG handler] Channel '{channel}' websocket removed")
                        if not CHANNEL_REGISTRY[channel]:
                            print(f"[DEBUG handler] Channel '{channel}' now empty, deleting")
                            del CHANNEL_REGISTRY[channel]

            elif event == "mood_update":
                mood = data.get("mood")
                channel = data.get("channel")
                print(f"[DEBUG handler] mood_update event → mood={mood}, channel={channel}")
                await broadcast({"event": "mood_update", "mood": mood}, channel)

            else:
                print(f"[DEBUG handler] UNKNOWN EVENT received: {data}")

    finally:
        print("[DEBUG handler] Connection ended, calling unregister")
        await unregister(websocket)
        print("[DEBUG handler] unregister complete")


# --- Async Server Runner ---
async def run_server(host="0.0.0.0", port=8765):
    print(f"[DEBUG run_server] Called → host={host} port={port}")
    print(f"[DEBUG run_server] Starting WebSocket server at ws://{host}:{port}")
    async with websockets.serve(handler, host, port):
        print("[DEBUG run_server] Server started, entering infinite wait")
        await asyncio.Future()


# --- Standalone Entrypoint ---
if __name__ == "__main__":
    print("[DEBUG __main__] Running standalone server mode")
    import asyncio
    asyncio.run(run_server())
    print("[DEBUG __main__] Server shutdown")
