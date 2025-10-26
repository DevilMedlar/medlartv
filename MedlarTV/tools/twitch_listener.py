import os
import socket
import time
import yaml
import requests
import logging
from dotenv import load_dotenv
from pathlib import Path

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
CO_PILOTS = set()  # Active co-pilots (usernames)
PILOT = CHANNEL.lstrip("#").lower()  # Channel owner is the Pilot
recent_msgs = {}
LAST_REPLY_AT = 0
COPILOT_CONFIG_PATH = Path("MedlarTV/config/copilots.yaml")

# --- Config Variables (populated by load_config) ---
COMMANDS = {}
PERSONALITY = {}
MOODS = {}
STYLE_PROFILES = {}
POLICIES = {}


# --- CO-PILOT MANAGEMENT ---
def load_copilots():
    """Load co-pilots from config file."""
    global CO_PILOTS
    if not COPILOT_CONFIG_PATH.exists():
        # Create default config
        default_config = {"copilots": {"active": [], "history": []}}
        COPILOT_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(COPILOT_CONFIG_PATH, 'w', encoding='utf-8') as f:
            yaml.safe_dump(default_config, f)
        return
    
    with open(COPILOT_CONFIG_PATH, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}
    
    active = data.get("copilots", {}).get("active", [])
    CO_PILOTS = {entry["username"].lower() for entry in active}
    log.info(f"📋 Loaded {len(CO_PILOTS)} co-pilots: {', '.join(CO_PILOTS) if CO_PILOTS else 'none'}")


def save_copilots():
    """Save co-pilots to config file."""
    data = {"copilots": {"active": [], "history": []}}
    
    if COPILOT_CONFIG_PATH.exists():
        with open(COPILOT_CONFIG_PATH, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or data
    
    # Update active list
    data["copilots"]["active"] = [
        {"username": username, "added_at": int(time.time())}
        for username in CO_PILOTS
    ]
    
    with open(COPILOT_CONFIG_PATH, 'w', encoding='utf-8') as f:
        yaml.safe_dump(data, f)


def add_copilot(username: str) -> bool:
    """Add a co-pilot."""
    username = username.lower()
    if username in CO_PILOTS:
        return False
    CO_PILOTS.add(username)
    save_copilots()
    log.info(f"✅ Co-Pilot added: {username}")
    return True


def remove_copilot(username: str) -> bool:
    """Remove a co-pilot."""
    username = username.lower()
    if username not in CO_PILOTS:
        return False
    CO_PILOTS.remove(username)
    save_copilots()
    log.info(f"❌ Co-Pilot removed: {username}")
    return True


def get_user_role(username: str) -> str:
    """Determine user's role: pilot, copilot, or user."""
    username = username.lower()
    if username == PILOT:
        return "pilot"
    elif username in CO_PILOTS:
        return "copilot"
    else:
        return "user"


def format_username(username: str) -> str:
    """Format username based on role."""
    role = get_user_role(username)
    if role == "pilot":
        return "Pilot"
    elif role == "copilot":
        return f"Co-Pilot {username}"
    else:
        return f"@{username}"


# --- CONFIG LOADING ---
def load_yaml_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_config():
    global COMMANDS, PERSONALITY, MOODS, STYLE_PROFILES, POLICIES
    base = os.path.dirname(__file__)
    COMMANDS = load_yaml_file(os.path.join(base, "../config/commands.yaml")).get("commands", {})
    PERSONALITY = load_yaml_file(os.path.join(base, "../config/personality.yaml")).get("personality", {})
    MOODS = load_yaml_file(os.path.join(base, "../config/moods.yaml")).get("moods", {})
    STYLE_PROFILES = load_styles()
    POLICIES = load_policies()
    load_copilots()  # Load co-pilots


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

    try:
        requests.post(f"{CORE_URL}/mood", json={"mood": new_mood}, timeout=3)
    except Exception as e:
        log.warning(f"[Core] Mood update failed: {e}")


def send_reply(sock, message, reply_to_msg_id=None):
    """Send a message to Twitch chat with optional reply threading."""
    if reply_to_msg_id:
        sock.send(f"@reply-parent-msg-id={reply_to_msg_id} PRIVMSG {CHANNEL} :{message}\r\n".encode("utf-8"))
    else:
        sock.send(f"PRIVMSG {CHANNEL} :{message}\r\n".encode("utf-8"))
    log.info(f"[MedlarTV→Twitch] {message}")


def handle_command(sock, username, message, msg_id=None):
    """Handle ! commands from chat."""
    parts = message.split()
    cmd = parts[0][1:].lower()  # Remove the !
    
    if cmd not in COMMANDS:
        return False
    
    cmd_config = COMMANDS[cmd]
    
    # Check if command requires pilot permission
    if cmd_config.get("requires_pilot", False):
        if get_user_role(username) != "pilot":
            send_reply(sock, f"@{username} ⛔ This command is restricted to Pilot only.", msg_id)
            return True
    
    response = cmd_config.get("response", "")
    
    # Format the response with user role
    formatted_user = format_username(username)
    response = response.replace("{user}", formatted_user)
    response = response.replace("{nick}", NICK)
    
    # Special command handling
    if cmd == "moodnumbers":
        from MedlarTV.core.memory import load_memory
        data = load_memory()
        moods = data["personality_memory"]["mood_weights"]
        response = f"{formatted_user} 📊 Mood Stats: " + " | ".join([f"{m}: {v}" for m, v in moods.items()])
    
    elif cmd == "mood":
        response = f"{formatted_user} Current mood: {current_mood} {MOODS.get(current_mood, {}).get('emoji', [''])[0]}"
    
    elif cmd == "addcopilot":
        if len(parts) < 2:
            response = f"{formatted_user} Usage: !addcopilot username"
        else:
            target = parts[1].lstrip("@").lower()
            if add_copilot(target):
                response = response.replace("{target}", target)
            else:
                response = f"{formatted_user} {target} is already a Co-Pilot!"
    
    elif cmd == "removecopilot":
        if len(parts) < 2:
            response = f"{formatted_user} Usage: !removecopilot username"
        else:
            target = parts[1].lstrip("@").lower()
            if remove_copilot(target):
                response = response.replace("{target}", target)
            else:
                response = f"{formatted_user} {target} is not a Co-Pilot!"
    
    elif cmd == "listcopilots":
        if CO_PILOTS:
            copilot_list = ", ".join(sorted(CO_PILOTS))
            response = response.replace("{copilots}", copilot_list)
        else:
            response = f"{formatted_user} No active Co-Pilots."
    
    send_reply(sock, response, msg_id)
    return True


def detect_mood_from_message(message):
    """Detect if message should trigger a mood change."""
    msg_lower = message.lower()
    
    for mood_name, mood_config in MOODS.items():
        triggers = mood_config.get("triggers", [])
        for trigger in triggers:
            if trigger in msg_lower:
                return mood_name
    
    return None


def should_respond_to_message(username, message):
    """Determine if MedlarTV should respond to this message."""
    msg_lower = message.lower()
    
    # Always respond if mentioned directly
    personality_triggers = PERSONALITY.get("trigger_keywords", [])
    for trigger in personality_triggers:
        if trigger.lower() in msg_lower:
            return True
    
    # Respond to @mentions
    if f"@{NICK.lower()}" in msg_lower:
        return True
    
    # Respond to questions directed at bot
    if "?" in message and any(word in msg_lower for word in ["medlar", "bot", "ai"]):
        return True
    
    return False


def get_llm_response(username, message):
    """Get AI response from the Core API."""
    try:
        # Pass the formatted role instead of raw username
        role = get_user_role(username)
        sender = format_username(username) if role != "user" else username
        
        response = requests.post(
            f"{CORE_URL}/chat",
            json={"prompt": message, "sender": sender},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("reply", "")
        else:
            log.error(f"[Core] API returned {response.status_code}")
            return None
            
    except requests.exceptions.Timeout:
        log.error("[Core] Request timed out")
        return None
    except Exception as e:
        log.error(f"[Core] Error getting LLM response: {e}")
        return None


def format_reply_with_mood(reply):
    """Add mood-based styling to reply."""
    style = STYLE_PROFILES.get(current_mood, {})
    prefix = style.get("prefix", "")
    suffix = style.get("suffix", "")
    
    # Don't double-add styling if it's already there
    if prefix and not reply.startswith(prefix):
        reply = f"{prefix} {reply}"
    if suffix and not reply.endswith(suffix):
        reply = f"{reply} {suffix}"
    
    return reply


# --- NETWORK FUNCTIONS ---
def connect():
    """Connect to Twitch IRC and join all relevant channels."""
    sock = socket.socket()
    sock.connect((SERVER, PORT))
    sock.send(f"PASS {TOKEN}\r\n".encode("utf-8"))
    sock.send(f"NICK {NICK}\r\n".encode("utf-8"))

    sock.send(b"CAP REQ :twitch.tv/tags\r\n")
    sock.send(b"CAP REQ :twitch.tv/commands\r\n")
    sock.send(b"CAP REQ :twitch.tv/membership\r\n")

    # Join main channel (Pilot's channel)
    sock.send(f"JOIN {CHANNEL}\r\n".encode("utf-8"))
    log.info(f"🟢 Connected to {CHANNEL} as {NICK} (Pilot: {PILOT})")

    # Join all co-pilot channels
    for copilot in CO_PILOTS:
        copilot_channel = f"#{copilot}"
        sock.send(f"JOIN {copilot_channel}\r\n".encode("utf-8"))
        log.info(f"🔗 Joined Co-Pilot channel: {copilot_channel}")

    # Register with bridge
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

    while True:
        try:
            resp = sock.recv(4096).decode("utf-8", errors="ignore")
        except Exception as e:
            log.error(f"[Socket] recv failed: {e}")
            break

        if resp.startswith("PING"):
            sock.send(b"PONG :tmi.twitch.tv\r\n")
            continue

        if not resp.strip():
            continue

        # Parse IRC tags
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

        # Auto mood detection from keywords
        msg_lower = resp.lower()
        detected_mood = None
        if "hype" in msg_lower or "let's go" in msg_lower or "pog" in msg_lower:
            detected_mood = "hype"
        elif "chill" in msg_lower or "relax" in msg_lower or "vibe" in msg_lower:
            detected_mood = "chill"
        elif "lol" in msg_lower or "lmao" in msg_lower or "bruh" in msg_lower:
            detected_mood = "snarky"
        elif "sad" in msg_lower or "help" in msg_lower or "aww" in msg_lower:
            detected_mood = "supportive"
        
        if detected_mood:
            switch_mood(detected_mood, auto=True)

        # Process PRIVMSG (actual chat messages)
        if "PRIVMSG" in resp and "!" in resp:
            try:
                username = resp.split("!", 1)[0][1:].lower()
                if username in ignored_users:
                    continue

                message = resp.split("PRIVMSG", 1)[1].split(":", 1)[1].strip()
                
                # Log with role
                role = get_user_role(username)
                role_tag = {"pilot": "[PILOT]", "copilot": "[CO-PILOT]", "user": ""}.get(role, "")
                log.info(f"[Twitch→Core] {role_tag} {username}: {message}")

                # Store message in recent history
                if msg_id:
                    recent_msgs[msg_id] = {"user": username, "message": message}
                    if len(recent_msgs) > 80:
                        oldest = next(iter(recent_msgs))
                        recent_msgs.pop(oldest, None)

                # Handle commands first (! commands)
                if message.startswith("!"):
                    if handle_command(sock, username, message, msg_id):
                        continue  # Command handled, don't process further

                # Check if we should respond to this message
                if not should_respond_to_message(username, message):
                    # Even if not responding, still detect mood
                    mood = detect_mood_from_message(message)
                    if mood:
                        switch_mood(mood, auto=True)
                    continue

                # Rate limiting
                if not can_reply():
                    log.info("[Cooldown] Skipping reply (rate limited)")
                    continue

                # Get LLM response
                log.info(f"[LLM] Generating response for {username}...")
                llm_reply = get_llm_response(username, message)
                
                if llm_reply:
                    # Format with mood styling
                    formatted_reply = format_reply_with_mood(llm_reply)
                    
                    # Send the reply (always to main channel only)
                    send_reply(sock, formatted_reply, msg_id if reply_parent_msg_id else None)
                else:
                    log.warning("[LLM] No response generated")

            except Exception as e:
                log.error(f"[Handler] Failed to process message: {e}")
                import traceback
                traceback.print_exc()


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
        log.info(f"👤 Pilot: {PILOT}")
        log.info(f"👥 Co-Pilots: {', '.join(CO_PILOTS) if CO_PILOTS else 'none'}")
        s = connect()
        listen(s)
    except KeyboardInterrupt:
        log.info("\n🛑 MedlarTV Twitch listener stopped manually.")
        cleanup_and_exit(s)
    except Exception as e:
        log.error(f"💥 Fatal error: {e}")
        import traceback
        traceback.print_exc()
        raise