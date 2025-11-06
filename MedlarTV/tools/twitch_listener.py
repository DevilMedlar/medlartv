import os
import socket
import time
import yaml
import requests
import logging
from dotenv import load_dotenv
from pathlib import Path

from MedlarTV.core.translation_command import handle_translate_command, get_supported_languages_list
from MedlarTV.core.memory import record_mood, get_dominant_weighted_mood
from MedlarTV.core.expression import blended_phrase
from MedlarTV.core.context import record_session_mood
from MedlarTV.core.fuzzy_trigger import should_respond as fuzzy_should_respond, find_triggers_in_message
from MedlarTV.avatar.bridge_client import register_channel, send_mood_update, ws_send
from MedlarTV.core.translation import detect_language, get_multilingual_greeting, add_language_indicator
from MedlarTV.core.response_templates import get_smart_response
from MedlarTV.core.interaction_logger import log_interaction, log_command, log_mood_change, log_error
from MedlarTV.core.moderation import (
    check_message,
    execute_timeout,
    execute_ban,
    handle_mod_command,
    is_mod_command
)
from MedlarTV.core.stream_management import (
    get_stream_info,
    get_channel_info,
    update_stream_title,
    update_stream_category,
    format_stream_info
)
from MedlarTV.core.twitch_events import (
    detect_raid,
    detect_subscription,
    detect_channel_point_redemption,
    detect_bits,
    get_raid_response,
    get_sub_response,
    get_channel_point_response,
    get_bits_response,
    add_random_emote
)
from MedlarTV.core.content_filter import (
    filter_message,
    should_enable_all_caps,
    get_safety_response
)

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
    raise EnvironmentError("Missing TWITCH_TOKEN, TWITCH_NICK, or TWITCH_CHANNEL in .env")

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

# Track the socket globally so we can use it in remove_copilot
SOCKET = None

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
    log.info(f"Loaded {len(CO_PILOTS)} co-pilots: {', '.join(CO_PILOTS) if CO_PILOTS else 'none'}")


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
    """Add a co-pilot, join their channel, and register with bridge."""
    global SOCKET
    username = username.lower()
    
    if username in CO_PILOTS:
        return False
    
    CO_PILOTS.add(username)
    save_copilots()
    
    # Join the co-pilot's channel
    if SOCKET:
        copilot_channel = f"#{username}"
        try:
            SOCKET.send(f"JOIN {copilot_channel}\r\n".encode("utf-8"))
            log.info(f"✅ Joined channel: {copilot_channel}")
            
            # Register with WebSocket bridge
            try:
                register_channel(copilot_channel)
                log.info(f"✅ Registered with bridge: {copilot_channel}")
            except Exception as e:
                log.warning(f"[Bridge] Failed to register {copilot_channel}: {e}")
            
            log.info(f"✅ Co-Pilot added: {username}")
            
        except Exception as e:
            log.error(f"Failed to join channel {copilot_channel}: {e}")
            # Rollback if join failed
            CO_PILOTS.remove(username)
            save_copilots()
            return False
    else:
        log.info(f"✅ Co-Pilot added: {username} (socket not ready, will join on next connect)")
    
    return True


def remove_copilot(username: str) -> bool:
    """Remove a co-pilot, leave their channel, and unregister from bridge."""
    global SOCKET
    username = username.lower()
    
    if username not in CO_PILOTS:
        return False
    
    CO_PILOTS.remove(username)
    save_copilots()
    
    # PART (leave) the co-pilot's channel
    if SOCKET:
        copilot_channel = f"#{username}"
        try:
            SOCKET.send(f"PART {copilot_channel}\r\n".encode("utf-8"))
            log.info(f"❌ Left channel: {copilot_channel}")
            
            # Unregister from WebSocket bridge
            try:
                ws_send({
                    "event": "unregister",
                    "platform": "twitch",
                    "channel": copilot_channel
                })
                log.info(f"❌ Unregistered from bridge: {copilot_channel}")
            except Exception as e:
                log.warning(f"[Bridge] Failed to unregister {copilot_channel}: {e}")
            
            log.info(f"❌ Co-Pilot removed: {username}")
            
        except Exception as e:
            log.error(f"Failed to leave channel {copilot_channel}: {e}")
    else:
        log.info(f"❌ Co-Pilot removed: {username} (socket not ready)")
    
    return True


def get_user_role(username: str, badges: dict = None) -> str:
    """
    Determine user's role: pilot, mod, copilot, vip, or user.
    
    Args:
        username: Username to check
        badges: Twitch badges dict (optional, for mod/vip detection)
    
    Returns:
        Role string: "pilot", "mod", "copilot", "vip", or "user"
    """
    username = username.lower()
    
    # Check if user is broadcaster (highest priority)
    if username == PILOT:
        return "pilot"
    
    # Check if user is a Twitch moderator (from badges)
    if badges and "moderator" in badges:
        return "mod"
    
    # Check if user is a VIP (from badges)
    if badges and "vip" in badges:
        return "vip"
    
    # Check if user is a co-pilot
    if username in CO_PILOTS:
        return "copilot"
    
    # Default to regular user
    return "user"

def check_command_permission(username: str, cmd_config: dict, badges: dict = None) -> tuple:
    """
    Check if user has permission to use a command.
    
    Args:
        username: Username attempting command
        cmd_config: Command configuration from commands.yaml
        badges: Twitch badges dict (optional)
    
    Returns:
        Tuple of (has_permission: bool, denial_reason: str)
    """
    # Get user's role
    user_role = get_user_role(username, badges)
    
    # Get allowed roles for this command (default to everybody if not specified)
    allowed_roles = cmd_config.get("allowed_roles", ["everybody"])
    
    # If "everybody" is in allowed_roles, everyone can use it
    if "everybody" in allowed_roles:
        return True, ""
    
    # Pilot always has access to everything
    if user_role == "pilot":
        return True, ""
    
    # Check if user's role is in allowed roles
    if user_role in allowed_roles:
        return True, ""
    
    # Permission denied - create helpful message
    role_names = {
        "pilot": "Broadcaster",
        "mod": "Moderator",
        "copilot": "Co-Pilot",
        "vip": "VIP",
        "user": "Viewer"
    }
    
    allowed_names = [role_names.get(role, role) for role in allowed_roles]
    required = ", ".join(allowed_names)
    
    return False, f"This command requires: {required}"

def extract_badges_from_irc(irc_message: str) -> dict:
    """
    Extract Twitch badges from IRC message tags.
    
    Args:
        irc_message: Raw IRC message with tags
    
    Returns:
        Dict of badges (e.g., {"moderator": "1", "vip": "1"})
    """
    badges = {}
    
    if not irc_message.startswith("@"):
        return badges
    
    try:
        # Extract tags section
        tags_section = irc_message.split(" ", 1)[0][1:]  # Remove @ prefix
        
        # Parse tags
        for tag in tags_section.split(";"):
            if "=" in tag:
                key, value = tag.split("=", 1)
                
                # Parse badges tag
                if key == "badges":
                    if value:
                        for badge in value.split(","):
                            if "/" in badge:
                                badge_name, badge_version = badge.split("/", 1)
                                badges[badge_name] = badge_version
    except Exception as e:
        log.warning(f"[Badges] Failed to parse badges: {e}")
    
    return badges

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
    prefix = "Auto" if auto else "manual"
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


def handle_command(sock, username, message, msg_id=None, badges=None):
    """Handle ! commands from chat with flexible role-based permissions."""
    parts = message.split()
    cmd = parts[0][1:].lower()
    args = " ".join(parts[1:]) if len(parts) > 1 else ""
    
    if cmd not in COMMANDS:
        return False
    
    cmd_config = COMMANDS[cmd]
    
    # Check flexible role-based permissions
    has_permission, denial_reason = check_command_permission(username, cmd_config, badges)
    
    if not has_permission:
        send_reply(sock, f"@{username} ❌ {denial_reason}", msg_id)
        log.info(f"[Command] {username} denied access to !{cmd}: {denial_reason}")
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
     
     # Translation Command
    elif cmd in ["t", "translate", "trans"]:
        response = handle_translate_command(args, username)
        send_reply(SOCKET, response, msg_id)
        log_command(username, cmd, args, response)
        return
    
    # NEW: Translation Help
    elif cmd in ["tlang", "translatelangs", "languages"]:
        langs = get_supported_languages_list()
        response = f"@{username} Supported languages: {langs}"
        send_reply(SOCKET, response, msg_id)
        return
    
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
    
    # Use fuzzy trigger detection
    if fuzzy_should_respond(message, strict=False):
        return True
    
    # Respond to @mentions
    if f"@{NICK.lower()}" in msg_lower:
        return True
    
    # Respond to questions directed at bot
    if "?" in message and fuzzy_should_respond(message, strict=True):
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
            reply = data.get("reply", "")
            
            # Limit response to 500 characters (Twitch message limit)
            if len(reply) > 500:
                reply = reply[:497] + "..."
                log.warning(f"[LLM] Response truncated to 500 chars")
            
            return reply
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
    global SOCKET
    
    sock = socket.socket()
    sock.connect((SERVER, PORT))
    sock.send(f"PASS {TOKEN}\r\n".encode("utf-8"))
    sock.send(f"NICK {NICK}\r\n".encode("utf-8"))

    sock.send(b"CAP REQ :twitch.tv/tags\r\n")
    sock.send(b"CAP REQ :twitch.tv/commands\r\n")
    sock.send(b"CAP REQ :twitch.tv/membership\r\n")

    # Join main channel (Pilot's channel)
    sock.send(f"JOIN {CHANNEL}\r\n".encode("utf-8"))
    log.info(f"Connected to {CHANNEL} as {NICK} (Pilot: {PILOT})")

    # Store socket globally first so add_copilot can use it
    SOCKET = sock

    # Join all co-pilot channels
    for copilot in CO_PILOTS:
        copilot_channel = f"#{copilot}"
        sock.send(f"JOIN {copilot_channel}\r\n".encode("utf-8"))
        log.info(f"Joined Co-Pilot channel: {copilot_channel}")

        # Register each co-pilot channel with bridge
        try:
            register_channel(copilot_channel)
            log.info(f"Registered with bridge: {copilot_channel}")
        except Exception as e:
            log.warning(f"[Bridge] Failed to register {copilot_channel}: {e}")

    # Register main channel with bridge
    for attempt in range(3):
        try:
            register_channel(CHANNEL)
            log.info("[Bridge] Main channel registered successfully")
            break
        except Exception as e:
            log.warning(f"[Bridge] register_channel failed (try {attempt+1}/3): {e}")
            time.sleep(1)

    return sock


def listen(sock):
    log.info("Listening for Twitch chat messages...")

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
            log_error("socket_error", str(e))
            break

        if resp.startswith("PING"):
            sock.send(b"PONG :tmi.twitch.tv\r\n")
            continue

        if not resp.strip():
            continue

        # Detect Twitch events FIRST (before tags parsing)
        raid_info = detect_raid(resp)
        if raid_info:
            response = get_raid_response(raid_info)
            send_reply(sock, response)
            log_interaction("SYSTEM", "raid", response, current_mood, "en", metadata=raid_info)
            continue

        sub_info = detect_subscription(resp)
        if sub_info:
            response = get_sub_response(sub_info)
            send_reply(sock, response)
            log_interaction("SYSTEM", "subscription", response, current_mood, "en", metadata=sub_info)
            continue

        points_info = detect_channel_point_redemption(resp)
        if points_info:
            response = get_channel_point_response(points_info)
            send_reply(sock, response)
            log_interaction("SYSTEM", "channel_points", response, current_mood, "en", metadata=points_info)
            continue

        bits_info = detect_bits(resp)
        if bits_info:
            response = get_bits_response(bits_info)
            send_reply(sock, response)
            log_interaction("SYSTEM", "bits", response, current_mood, "en", metadata=bits_info)
            continue

        # Parse IRC tags (existing code)
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

        # Auto mood detection (existing code)
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
            old_mood = current_mood
            switch_mood(detected_mood, auto=True)
            log_mood_change(old_mood, detected_mood, "keyword")

        # Process PRIVMSG (actual chat messages)
        if "PRIVMSG" in resp and "!" in resp:
            try:
                # ⭐ NEW: Extract badges from tags (simple inline method)
                badges = {}
                if "badges=" in resp:
                    try:
                        badges_str = resp.split("badges=")[1].split(";")[0]
                        if badges_str:
                            for badge in badges_str.split(","):
                                if "/" in badge:
                                    badge_name, badge_version = badge.split("/", 1)
                                    badges[badge_name] = badge_version
                    except Exception as e:
                        log.warning(f"[Badges] Failed to parse: {e}")
                
                username = resp.split("!", 1)[0][1:].lower()
                if username in ignored_users:
                    continue

                message = resp.split("PRIVMSG", 1)[1].split(":", 1)[1].strip()
                
                # ⭐ UPDATED: Get user role WITH badges
                role = get_user_role(username, badges)
                role_tag = {
                    "pilot": "[PILOT]",
                    "mod": "[MOD]",
                    "copilot": "[CO-PILOT]",
                    "vip": "[VIP]",
                    "user": ""
                }.get(role, "")
                log.info(f"[Twitch→Core] {role_tag} {username}: {message}")

                # Detect language
                detected_language = detect_language(message)

                # Store message in recent history
                if msg_id:
                    recent_msgs[msg_id] = {"user": username, "message": message}
                    if len(recent_msgs) > 80:
                        oldest = next(iter(recent_msgs))
                        recent_msgs.pop(oldest, None)

                # Check moderation FIRST
                mod_check = check_message(username, message, role)
                if not mod_check["is_allowed"]:
                    log.warning(f"[Mod] Blocked message from {username}: {mod_check['reason']}")
                    
                    if mod_check["action"] == "timeout":
                        execute_timeout(sock, CHANNEL, username, mod_check.get("duration", 60), mod_check["reason"])
                    elif mod_check["action"] == "delete":
                        execute_delete(sock, CHANNEL, msg_id)
                    elif mod_check["action"] == "warn":
                        send_reply(sock, f"@{username} {mod_check['reason']}. Please follow chat rules.")
                    
                    continue

                # Handle mod commands
                if is_mod_command(message):
                    mod_response = handle_mod_command(sock, CHANNEL, username, message, role)
                    if mod_response:
                        send_reply(sock, mod_response, msg_id)
                        log_command(username, message.split()[0], success=True)
                    continue

                # Handle regular commands
                if message.startswith("!"):
                    # ⭐ NEW: Try flexible permission commands first (with badges)
                    if handle_command(sock, username, message, msg_id, badges):
                        log_command(username, message.split()[0], success=True)
                        continue
                    
                    # Stream management commands (fallback for special commands)
                    if message.lower().startswith("!streaminfo"):
                        stream_info = get_stream_info()
                        response = format_stream_info(stream_info)
                        send_reply(sock, response, msg_id)
                        log_command(username, "!streaminfo", success=True)
                        continue
                    
                    elif message.lower().startswith("!title") and role in ["pilot", "copilot"]:
                        parts = message.split(maxsplit=1)
                        if len(parts) > 1:
                            new_title = parts[1]
                            if update_stream_title(new_title):
                                send_reply(sock, f"@{username} Stream title updated!", msg_id)
                            else:
                                send_reply(sock, f"@{username} Failed to update title.", msg_id)
                        else:
                            channel_info = get_channel_info()
                            if channel_info:
                                send_reply(sock, f"Current title: {channel_info['title']}", msg_id)
                        log_command(username, "!title", success=True)
                        continue
                    
                    elif message.lower().startswith("!game") and role in ["pilot", "copilot"]:
                        parts = message.split(maxsplit=1)
                        if len(parts) > 1:
                            new_game = parts[1]
                            if update_stream_category(new_game):
                                send_reply(sock, f"@{username} Category updated to {new_game}!", msg_id)
                            else:
                                send_reply(sock, f"@{username} Failed to update category.", msg_id)
                        else:
                            channel_info = get_channel_info()
                            if channel_info:
                                send_reply(sock, f"Current game: {channel_info['game_name']}", msg_id)
                        log_command(username, "!game", success=True)
                        continue

                # Check if we should respond to this message
                if not should_respond_to_message(username, message):
                    mood = detect_mood_from_message(message)
                    if mood:
                        old_mood = current_mood
                        switch_mood(mood, auto=True)
                        log_mood_change(old_mood, mood, "auto")
                    continue

                # Rate limiting
                if not can_reply():
                    log.info("[Cooldown] Skipping reply (rate limited)")
                    continue

                # Try smart template response first
                template_response = get_smart_response(message, username, current_mood)
                
                if template_response:
                    # Add language indicator if needed
                    if detected_language != "en":
                        template_response = add_language_indicator(template_response, detected_language)
                    
                    send_reply(sock, template_response, msg_id)
                    log_interaction(username, message, template_response, current_mood, detected_language)
                    continue

                # Check if user wants all caps mode
                if should_enable_all_caps(message):
                    log.info(f"[Filter] All caps mode activated by {username}")

                # Get LLM response
                log.info(f"[LLM] Generating response for {username}...")
                llm_reply = get_llm_response(username, message)
                
                if not llm_reply:
                    log.warning("[LLM] No response generated")
                    log_error("llm_no_response", f"Failed for {username}: {message}")
                    continue

                # Apply content filter
                is_safe, filtered_reply, reason = filter_message(llm_reply, username)
                
                if not is_safe:
                    log.warning(f"[Filter] Response blocked: {reason}")
                    safe_reply = get_safety_response()
                    send_reply(sock, safe_reply, msg_id if reply_parent_msg_id else None)
                    log_interaction(username, message, safe_reply, current_mood, detected_language)
                    continue

                # Format with mood styling
                formatted_reply = format_reply_with_mood(filtered_reply)
                
                # Add language indicator
                if detected_language != "en":
                    formatted_reply = add_language_indicator(formatted_reply, detected_language)
                
                # Send the filtered reply
                send_reply(sock, formatted_reply, msg_id if reply_parent_msg_id else None)

                # Log the interaction
                log_interaction(username, message, formatted_reply, current_mood, detected_language)

            except Exception as e:
                log.error(f"[Handler] Failed to process message: {e}")
                log_error("message_handler", str(e), {"username": username, "message": message})
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
        log.info("Connection closed cleanly")


# --- ENTRYPOINT ---
if __name__ == "__main__":
    try:
        load_config()
        current_mood = get_dominant_weighted_mood()
        log.info(f"Starting with learned default mood: {current_mood}")
        log.info(f"Pilot: {PILOT}")
        log.info(f"Co-Pilots: {', '.join(CO_PILOTS) if CO_PILOTS else 'none'}")
        s = connect()
        listen(s)
    except KeyboardInterrupt:
        log.info("\n⚡ MedlarTV Twitch listener stopped manually.")
        cleanup_and_exit(s)
    except Exception as e:
        log.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        raise