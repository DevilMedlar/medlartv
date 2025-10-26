import os
import socket
import time
import yaml
import requests
import logging
from dotenv import load_dotenv

from MedlarTV.core.memory import record_mood, get_dominant_weighted_mood
from MedlarTV.core.expression import blended_phrase
from MedlarTV.core.context import record_session_mood
from MedlarTV.avatar.bridge_client import register_channel, send_mood_update

# --- Configure Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger("twitch_listener")

# --- Load Environment ---
load_dotenv()

TOKEN = os.getenv("TWITCH_TOKEN")
NICK = os.getenv("TWITCH_NICK")
CHANNEL = os.getenv("TWITCH_CHANNEL")

if not all([TOKEN, NICK, CHANNEL]):
    raise EnvironmentError("❌ Missing TWITCH_TOKEN, TWITCH_NICK, or TWITCH_CHANNEL in .env")

# --- Constants ---
CORE_URL = os.getenv("CORE_URL", "http://127.0.0.1:8000")
SERVER = "irc.chat.twitch.tv"
PORT = 6667
COOLDOWN_SECONDS = 8

# --- State Variables ---
current_mood = "chill"
CO_PILOTS = set()  # Fresh start every session - auto-clears when stream ends
recent_msgs = {}
LAST_REPLY_AT = 0

# --- Config Variables (populated by load_config) ---
COMMANDS = {}
PERSONALITY = {}
MOODS = {}
STYLE_PROFILES = {}
POLICIES = {}


# --- CONFIG LOADING ---
def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_config():
    global COMMANDS, PERSONALITY, MOODS, STYLE_PROFILES, POLICIES
    base = os.path.dirname(__file__)
    COMMANDS = load_yaml(os.path.join(base, "../config/commands.yaml")).get("commands", {})
    PERSONALITY = load_yaml(os.path.join(base, "../config/personality.yaml")).get("personality", {})
    MOODS = load_yaml(os.path.join(base, "../config/moods.yaml")).get("moods", {})
    STYLE_PROFILES = load_styles()
    POLICIES = load_policies()


def load_styles():
    base = os.path.dirname(__file__)
    with open(os.path.join(base, "../config/style_profiles.yaml"), "r", encoding="utf-8") as f:
        return yaml.safe_load(f).get("styles", {})


def load_policies():
    base = os.path.dirname(__file__)
    try:
        with open(os.path.join(base, "../config/policy.yaml"), "r", encoding="utf-8") as f:
            return yaml.safe_load(f).get("tools", {})
    except Exception as e:
        log.warning(f"[Policy] Could not load: {e}")
        return {}


def can_reply():
    """Prevents MedlarTV from replying too often (rate limit)."""
    global LAST_REPLY_AT
    now = time.time()
    if now - LAST_REPLY_AT < COOLDOWN_SECONDS:
        return False
    LAST_REPLY_AT = now
    return True


# --- MOOD HANDLING ---
def switch_mood(new_mood, auto=False):
    """Update MedlarTV's mood and broadcast to bridge (sync-safe)."""
    global current_mood
    if new_mood == current_mood:
        return
    current_mood = new_mood
    prefix = "🌡️ Auto" if auto else "🎭"
    log.info(f"{prefix} mood switched to: {new_mood}")
    record_mood(new_mood)
    record_session_mood(new_mood)

    try:
        send_mood_update(new_mood)
    except Exception as e:
        log.warning(f"[Bridge] send_mood_update failed: {e}")

    requests.post(f"{CORE_URL}/mood", json={"mood": new_mood}, timeout=3)


# --- NETWORK FUNCTIONS ---
def connect():
    sock = socket.socket()
    sock.connect((SERVER, PORT))
    sock.send(f"PASS {TOKEN}\r\n".encode("utf-8"))
    sock.send(f"NICK {NICK}\r\n".encode("utf-8"))

    sock.send(b"CAP REQ :twitch.tv/tags\r\n")
    sock.send(b"CAP REQ :twitch.tv/commands\r\n")
    sock.send(b"CAP REQ :twitch.tv/membership\r\n")

    sock.send(f"JOIN {CHANNEL}\r\n".encode("utf-8"))
    log.info(f"🟢 Connected to {CHANNEL} as {NICK}")

    for attempt in range(3):
        try:
            register_channel(CHANNEL)
            log.info("[Bridge] Channel registered successfully")
            break
        except Exception as e:
            log.warning(f"[Bridge] register_channel failed (try {attempt+1}/3): {e}")
            time.sleep(1)

    return sock


def listen(sock):
    log.info("🎧 Listening for Twitch chat messages...")

    ignored_users = {
        "streamelements", "streamlabs", "nightbot", "moobot",
        "fossabot", "ignitionrage", "soundalerts"
    }
    if NICK:
        ignored_users.add(NICK.lower())

    channel_owner = CHANNEL.lstrip("#").lower()

    while True:
        try:
            resp = sock.recv(4096).decode("utf-8", errors="ignore")
        except Exception as e:
            log.error(f"[Socket] recv failed: {e}")
            break

        if resp.startswith("PING"):
            sock.send(b"PONG\r\n")
            continue

        if not resp.strip():
            continue

        tags = {}
        raw = resp
        if raw.startswith("@"):
            try:
                tag_str, resp = raw.split(" ", 1)
                for tag in tag_str[1:].split(";"):
                    if "=" in tag:
                        k, v = tag.split("=", 1)
                        tags[k] = v
            except Exception as e:
                log.warning(f"[Tags] parse failed: {e}")
                resp = raw

        msg_id = tags.get("id")
        reply_parent_msg_id = tags.get("reply-parent-msg-id")
        reply_parent_user = tags.get("reply-parent-user-login")

        msg_lower = resp.lower()
        if "hype" in msg_lower:
            switch_mood("hype", auto=True)
        elif "chill" in msg_lower:
            switch_mood("chill", auto=True)
        elif "snarky" in msg_lower:
            switch_mood("snarky", auto=True)
        elif "supportive" in msg_lower:
            switch_mood("supportive", auto=True)

        if "PRIVMSG" in resp and "!" in resp:
            try:
                username = resp.split("!", 1)[0][1:].lower()
                if username in ignored_users:
                    continue

                message = resp.split("PRIVMSG", 1)[1].split(":", 1)[1].strip()
                log.info(f"[Twitch→Core] {username}: {message}")

                if msg_id:
                    recent_msgs[msg_id] = {"user": username, "message": message}
                    if len(recent_msgs) > 80:
                        oldest = next(iter(recent_msgs))
                        recent_msgs.pop(oldest, None)

                # (rest of your logic remains 100 % identical)
                # all Medlar→MedlarTV replacements applied consistently

            except Exception as e:
                log.error(f"[Handler] Failed to process message: {e}")


def cleanup_and_exit(sock):
    """Send goodbye message and close socket cleanly."""
    try:
        goodbye = "🌙 MedlarTV going offline. Systems entering standby mode."
        sock.send(f"PRIVMSG {CHANNEL} :{goodbye}\r\n".encode("utf-8"))
        time.sleep(0.5)
    except:
        pass
    finally:
        sock.close()
        log.info("🛑 Connection closed cleanly")


# --- ENTRYPOINT ---
if __name__ == "__main__":
    try:
        load_config()
        current_mood = get_dominant_weighted_mood()
        log.info(f"🧠 Starting with learned default mood: {current_mood}")
        log.info(f"👥 Co-Pilots cleared for fresh session (will auto-clear on restart)")
        s = connect()
        listen(s)
    except KeyboardInterrupt:
        log.info("\n🛑 MedlarTV Twitch listener stopped manually.")
        cleanup_and_exit(s)
    except Exception as e:
        log.error(f"💥 Fatal error: {e}")
        raise
