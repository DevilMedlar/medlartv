import asyncio
import json
import websockets
import time
from colorama import init, Fore, Style

print("[DEBUG avatar_client] Import complete, initializing colorama")
init(autoreset=True)

MOOD_COLORS = {
    "hype": Fore.RED + Style.BRIGHT,
    "chill": Fore.CYAN,
    "snarky": Fore.MAGENTA,
    "supportive": Fore.YELLOW + Style.BRIGHT
}

MOOD_ANIMATIONS = {
    "hype": "*pumps fist in the air* LET'S GOOOO!!!",
    "chill": "*leans back, calm and steady* just vibin'...",
    "snarky": "*rolls eyes, smirking slightly* lol sure",
    "supportive": "*offers a warm nod and a smile* You got this!"
}

print("[DEBUG avatar_client] Mood dictionaries initialized")


async def listen():
    print("[DEBUG avatar_client] listen() STARTED")
    uri = "ws://localhost:8765"
    print(f"[DEBUG avatar_client] Using WebSocket URI={uri!r}")

    print(Fore.GREEN + "[MedlarTV] Connecting to Avatar Bridge...")
    print(Fore.GREEN + "[MedlarTV] 'Processing data at light speed. Calculating emotion vectors.'")

    print(f"[DEBUG avatar_client] Attempting websocket connection to {uri}")
    async with websockets.connect(uri) as ws:
        print("[DEBUG avatar_client] WebSocket connection established")
        print(Fore.GREEN + "[MedlarTV] Connected to bridge, all systems operational...")

        while True:
            print("[DEBUG avatar_client] WAITING for ws.recv()…")
            try:
                msg = await ws.recv()
                print(f"[DEBUG avatar_client] Raw ws.recv() message={msg!r}")

                print("[DEBUG avatar_client] Attempting json.loads()…")
                data = json.loads(msg)
                print(f"[DEBUG avatar_client] JSON decoded successfully: {data}")

                event = data.get("event")
                print(f"[DEBUG avatar_client] event={event!r}")

                if event == "handshake":
                    print("[DEBUG avatar_client] Handshake event detected")
                    print(Fore.GREEN + "[MedlarTV] Handshake confirmed")

                elif event == "mood_update":
                    print("[DEBUG avatar_client] mood_update event detected")

                    mood = data.get("mood")
                    print(f"[DEBUG avatar_client] mood={mood!r}")

                    color = MOOD_COLORS.get(mood, Fore.WHITE)
                    animation = MOOD_ANIMATIONS.get(mood, "")

                    print(f"[DEBUG avatar_client] Selected color={repr(color)}")
                    print(f"[DEBUG avatar_client] Selected animation={animation!r}")

                    timestamp = time.strftime('%H:%M:%S')
                    print(f"[DEBUG avatar_client] timestamp={timestamp}")

                    print("\n" + "=" * 60)
                    print(color + f"[{timestamp}] MedlarTV MODE SHIFT → {mood.upper()}")
                    print(color + animation)
                    print("=" * 60 + "\n")

                else:
                    print(f"[DEBUG avatar_client] Unknown event type encountered: {event!r}")

            except json.JSONDecodeError:
                print(f"[DEBUG avatar_client] JSONDecodeError caught — msg={msg!r}")
                print(Fore.RED + f"[ERROR] Invalid JSON received: {msg}")

            except Exception as e:
                print(f"[DEBUG avatar_client] GENERAL EXCEPTION in listen(): {e}")
                print(Fore.RED + f"[ERROR] {e}")
                break


if __name__ == "__main__":
    print("[DEBUG avatar_client] __main__ block executing")
    try:
        print("[DEBUG avatar_client] Calling asyncio.run(listen())")
        asyncio.run(listen())
    except KeyboardInterrupt:
        print("[DEBUG avatar_client] KeyboardInterrupt caught, shutting down")
        print("\n" + Fore.YELLOW + "[MedlarTV] Shutting down avatar client. Standing by…")
    except Exception as e:
        print(f"[DEBUG avatar_client] Fatal exception in __main__: {e}")
        raise
