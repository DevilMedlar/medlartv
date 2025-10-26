import asyncio
import json
import websockets
import time  # FIX: Added missing import
from colorama import init, Fore, Style

init(autoreset=True)

MOOD_COLORS = {
    "hype": Fore.RED + Style.BRIGHT,
    "chill": Fore.CYAN,
    "snarky": Fore.MAGENTA,
    "supportive": Fore.YELLOW + Style.BRIGHT
}

MOOD_ANIMATIONS = {
    "hype": "💥 *pumps fist in the air* LET'S GOOOO!!!",
    "chill": "😌 *leans back, calm and steady* just vibin'...",
    "snarky": "😏 *rolls eyes, smirking slightly* lol sure",
    "supportive": "🌟 *offers a warm nod and a smile* You got this!"
}


async def listen():
    uri = "ws://localhost:8765"
    print(Fore.GREEN + "[MedlarTV] Connecting to Avatar Bridge...")
    print(Fore.GREEN + "[MedlarTV] 'Processing data at light speed. Calculating emotion vectors.' ⚡")

    async with websockets.connect(uri) as ws:
        print(Fore.GREEN + "[MedlarTV] Connected to bridge, all systems operational...")

        while True:
            try:
                msg = await ws.recv()
                data = json.loads(msg)

                if data.get("event") == "handshake":
                    print(Fore.GREEN + "[MedlarTV] ✅ Handshake confirmed")

                elif data.get("event") == "mood_update":
                    mood = data.get("mood")
                    color = MOOD_COLORS.get(mood, Fore.WHITE)
                    timestamp = time.strftime('%H:%M:%S')

                    print("\n" + "=" * 60)
                    print(color + f"[{timestamp}] 🧠 MedlarTV MODE SHIFT → {mood.upper()}")
                    print(color + MOOD_ANIMATIONS.get(mood, ""))
                    print("=" * 60 + "\n")

            except json.JSONDecodeError:
                print(Fore.RED + f"[ERROR] Invalid JSON received: {msg}")
            except Exception as e:
                print(Fore.RED + f"[ERROR] {e}")
                break


if __name__ == "__main__":
    try:
        asyncio.run(listen())
    except KeyboardInterrupt:
        print("\n" + Fore.YELLOW + "[MedlarTV] Shutting down avatar client. Standing by.")
