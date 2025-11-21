"""
MedlarTV Unified Command Handler (Refactored)
-------------------------------------------
Single source of truth for all bot commands.
This version is cleaned up, type-hinted, and aligned with the
updated MedlarTV.core.stream_management module.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Callable, Dict, Optional
from MedlarTV.core.interaction_logger import log_command
from MedlarTV.core.time_lookup import get_times_for_location
from MedlarTV.core.time_lookup import world_clock_summary, list_timezones
from MedlarTV.core.web_search import search_web, search_wikipedia
from MedlarTV.core.translation_command import handle_t_command, handle_tlang_command, HELP as TRANSLATE_HELP

log = logging.getLogger("commands")
log.setLevel(logging.DEBUG)
log.debug("[DEBUG] command_handlers loaded and logging active")

# =============================================================================
# Type Aliases
# =============================================================================

CommandContext = Dict[str, Any]
CommandHandler = Callable[[str, str, CommandContext], str]

# =============================================================================
# COMMAND HANDLERS
# =============================================================================

def handle_ping(username: str, args: str, context: CommandContext) -> str:
    """!ping - Show bot latency based on message timestamp."""
    now = time.time()
    last_ts = context.get("message_timestamp", now)
    latency_ms = int((now - last_ts) * 1000)
    return f"🏓 Pong! Latency: {latency_ms}ms — Online and responsive!"

def handle_status(username: str, args: str, context: CommandContext) -> str:
    """!status - Check health of major subsystems."""
    systems: list[str] = []

    # IRC connection
    systems.append("IRC:OK" if context.get("socket_connected", False) else "IRC:FAILED")

    try:
        from MedlarTV.avatar.bridge.client import is_bridge_available
        systems.append("Bridge:OK" if is_bridge_available() else "Bridge:FAILED")
    except Exception:
        systems.append("Bridge:FAILED")

    # Emotional system
    try:
        from MedlarTV.core.emotional_system import get_emotional_system

        if get_emotional_system():
            systems.append("Emotions:OK")
        else:
            systems.append("Emotions:FAILED")
    except Exception:
        systems.append("Emotions:FAILED")

    # Memory system
    try:
        from MedlarTV.core.memory import load_memory

        if load_memory():
            systems.append("Memory:OK")
        else:
            systems.append("Memory:FAILED")
    except Exception:
        systems.append("Memory:FAILED")

    # Moderation system
    try:
        from MedlarTV.core.moderation import check_message  # noqa: F401

        systems.append("Moderation:OK")
    except Exception:
        systems.append("Moderation:FAILED")

    # Translation system
    try:
        from MedlarTV.core.translation import translate_text  # noqa: F401

        systems.append("Translation:OK")
    except Exception:
        systems.append("Translation:FAILED")

    # Stream management (uses app token)
    try:
        from MedlarTV.core.stream_management import get_access_token

        token = get_access_token()
        systems.append("StreamAPI:OK" if token else "StreamAPI:FAILED")
    except Exception:
        systems.append("StreamAPI:FAILED")

    status_str = ", ".join(systems)
    bot_nick = context.get("bot_nick", "MedlarTV")
    return f"⚙️ System Status: {status_str} | Connected as {bot_nick}"


_EMOJI_MAP: Dict[str, str] = {
    "happiness": "😊",
    "excitement": "🔥",
    "gratitude": "💖",
    "chill": "😌",
    "supportive": "🤗",
    "sadness": "😢",
    "anger": "😠",
    "fear": "😰",
    "snarky": "😏",
    "energetic": "⚡",
    "tired": "😴",
    "stressed": "😫",
    "lonely": "😔",
    "connected": "🤝",
    "pride": "👑",
    "jealousy": "😒",
}

def handle_emotion(username: str, args: str, context: CommandContext) -> str:
    """!emotion - Show current dominant emotion."""
    try:
        from MedlarTV.core.emotional_system import get_emotional_system

        system = get_emotional_system()
        dominant = system.get_dominant_emotion()
        value = float(system.emotions.get(dominant, 0.0))

        emoji = _EMOJI_MAP.get(dominant, "💭")
        pct = int(value * 100)
        return f"{emoji} Current emotion: {dominant.capitalize()} ({pct}%)"

    except Exception as e:  # pragma: no cover - defensive
        log.error(f"[Emotion] Error: {e}")
        return "❌ Failed to retrieve emotional state."


def handle_emotions(username: str, args: str, context: CommandContext) -> str:
    """!emotions - Show top 3 emotions with percentages."""
    try:
        from MedlarTV.core.emotional_system import get_emotional_system

        system = get_emotional_system()
        top_3 = system.get_top_emotions(3)

        parts: list[str] = []
        for name, val in top_3.items():
            pct = int(float(val) * 100)
            parts.append(f"{name.capitalize()} {pct}%")

        if not parts:
            return "📊 No emotions available yet."

        return f"📊 Top emotions: {' | '.join(parts)}"

    except Exception as e:  # pragma: no cover - defensive
        log.error(f"[Emotions] Error: {e}")
        return "❌ Failed to retrieve emotional state."

def handle_feelstate(username: str, args: str, context: CommandContext) -> str:
    """!feelstate - Show detailed emotional description."""
    try:
        from MedlarTV.core.emotional_system import get_emotional_system

        system = get_emotional_system()
        desc = system.get_mood_description()
        return f"🧠 Emotional State: {desc}"

    except Exception as e:  # pragma: no cover
        log.error(f"[Feelstate] Error: {e}")
        return "❌ Failed to retrieve emotional state."

def handle_resetemotions(username: str, args: str, context: CommandContext) -> str:
    """!resetemotions - Reset all emotions to baseline (Pilot/Mod only)."""
    try:
        from MedlarTV.core.emotional_system import get_emotional_system

        system = get_emotional_system()
        system.reset_to_baseline()
        return "✅ Emotions reset to baseline. All weights returned to default values."

    except Exception as e:  # pragma: no cover
        log.error(f"[ResetEmotions] Error: {e}")
        return "❌ Failed to reset emotions."

def handle_streaminfo(username: str, args: str, context: CommandContext) -> str:
    """!streaminfo - Show current stream information."""
    try:
        from MedlarTV.core.stream_management import get_stream_info, format_stream_info

        info = get_stream_info()
        return format_stream_info(info)

    except Exception as e:  # pragma: no cover
        log.error(f"[StreamInfo] Error: {e}")
        return "❌ Failed to retrieve stream information."

def handle_title(username: str, args: str, context: CommandContext) -> str:
    """!title [new title] - Get or set stream title.

    - If args provided: attempt to set title (permission enforced in executor).
    - If no args: read current title from channel info.
    """
    try:
        from MedlarTV.core.stream_management import get_channel_info, update_stream_title

        if args.strip():
            # Setting title (broadcaster token is used inside stream_management)
            success = update_stream_title(args.strip())
            if success:
                return f"✅ Stream title updated to: {args.strip()}"
            return "❌ Failed to update stream title."

        # Getting title
        channel = get_channel_info()
        if channel:
            return f"📺 Current title: {channel['title']}"
        return "❌ Failed to retrieve channel info."

    except Exception as e:  # pragma: no cover
        log.error(f"[Title] Error: {e}")
        return "❌ Failed to process title command."

def handle_game(username: str, args: str, context: CommandContext) -> str:
    """!game [new category] - Get or set stream category/game."""
    try:
        from MedlarTV.core.stream_management import get_channel_info, update_stream_category

        if args.strip():
            success = update_stream_category(args.strip())
            if success:
                return f"✅ Category updated to: {args.strip()}"
            return "❌ Failed to update category. Make sure the game name is correct."

        channel = get_channel_info()
        if channel:
            return f"🎮 Current category: {channel['game_name']}"
        return "❌ Failed to retrieve channel info."

    except Exception as e:  # pragma: no cover
        log.error(f"[Game] Error: {e}")
        return "❌ Failed to process game command."

def handle_commands(username: str, args: str, context: CommandContext) -> str:
    url = os.getenv("COMMANDS_URL")
    if not url:
        host = os.getenv("COMMANDS_HOST", "127.0.0.1")
        port = os.getenv("COMMANDS_PORT", "8080")
        if host in {"127.0.0.1", "localhost"}:
            try:
                import socket
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
                host = ip or host
            except Exception:
                pass
        url = f"http://{host}:{port}/"
    return f"📋 Command catalog: {url}"

    return f"📋 Command catalog: {url}"

# =============================================================================
# COMMAND REGISTRY / PERMISSIONS
# =============================================================================

PERMISSION_EVERYONE = "everybody"
PERMISSION_PILOT = "pilot"
PERMISSION_MOD = "mod"
PERMISSION_COPILOT = "copilot"
PERMISSION_VIP = "vip"


 

# =============================================================================
# COMMAND EXECUTION ENGINE
# =============================================================================

def check_permission(username: str, role: str, required_permissions: list[str]) -> bool:
    """Return True if a user with `role` can execute a command.

    - Everyone can run commands that include PERMISSION_EVERYONE.
    - Pilot always has access to everything.
    - Otherwise, role must be in required_permissions.
    """
    if PERMISSION_EVERYONE in required_permissions:
        return True
    if role == PERMISSION_PILOT:
        return True
    return role in required_permissions

def execute_command(
    command: str,
    username: str,
    role: str,
    args: str,
    context: CommandContext,
) -> Optional[str]:
    """Execute a command and return a response string.

    Returns None if the command does not exist.
    """
    # Unknown command → let other systems (YAML, etc.) handle it
    if command not in COMMAND_REGISTRY:
        return None
    log.debug(f"[DEBUG] Command recognized: !{command} | User={username} | Role={role} | Args='{args}'")

    cmd_info = COMMAND_REGISTRY[command]

    # Permission gate
    if not check_permission(username, role, cmd_info.get("permissions", [])):
        role_names = {
            "pilot": "Broadcaster",
            "mod": "Moderator",
            "copilot": "Co-Pilot",
            "vip": "VIP",
            "user": "Viewer",
        }
        allowed_names = [role_names.get(p, p) for p in cmd_info.get("permissions", [])]
        required = ", ".join(allowed_names)
        return f"@{username} ❌ Permission denied. This command requires: {required}"

    # Extra protection for mutating stream commands: title/game SET requires pilot/copilot
    if command in {"title", "game"} and args.strip():
        if role not in {PERMISSION_PILOT, PERMISSION_COPILOT}:
            return f"@{username} ❌ Only Broadcaster and Co-Pilots can change the {command}."

    try:
        handler: CommandHandler = cmd_info["handler"]
        log.debug(f"[DEBUG] Executing handler for !{command}: {handler.__name__}")
        log.debug(f"[DEBUG] Context passed: {context}")

        response = handler(username, args, context)

        log.debug(f"[DEBUG] Handler returned: {response}")
        log.info(f"[Command] {username} executed !{command}")
        try:
            log_command(username, f"!{command}", success=True)
        except Exception:
            pass

        return response

    except Exception as e:  # pragma: no cover
        log.error(f"[Command] Error executing !{command}: {e}")
        log.debug("[DEBUG] Exception occurred inside command handler")

        import traceback
        traceback.print_exc()

        try:
            log_command(username, f"!{command}", success=False, error=str(e))
        except Exception:
            pass
        return f"❌ Command failed: {command}"


def get_command_help(command: str | None = None) -> str:
    """Return help text for a specific command or a categorized list."""
    if command:
        if command in COMMAND_REGISTRY:
            info = COMMAND_REGISTRY[command]
            text = f"!{command} - {info['description']}"
            usage = info.get("usage")
            if usage:
                text += f"\nUsage: {usage}"
            return text
        return f"Command !{command} not found."

    categories: Dict[str, list[str]] = {
        "System": ["ping", "status"],
        "Emotions": ["emotion", "emotions", "feelstate", "resetemotions"],
        "Stream": ["streaminfo", "title", "game"],
    }

    lines: list[str] = ["Available Commands:"]
    for cat, cmds in categories.items():
        lines.append(f"\n{cat}:")
        for name in cmds:
            if name in COMMAND_REGISTRY:
                info = COMMAND_REGISTRY[name]
                lines.append(f"  !{name} - {info['description']}")

    return "\n".join(lines)


"""Quick template for adding new commands:

1. Define a handler:

   def handle_mycommand(username: str, args: str, context: CommandContext) -> str:
       
       return "Response message"

2. Register it in COMMAND_REGISTRY:

   COMMAND_REGISTRY["mycommand"] = {
       "handler": handle_mycommand,
       "permissions": [PERMISSION_EVERYONE],  # or [PERMISSION_PILOT, PERMISSION_MOD]
       "description": "Does something cool",
       "usage": "!mycommand [optional args]",  # optional
   }

That's it. The unified handler will start routing !mycommand automatically.
"""
def handle_time(username: str, args: str, context: CommandContext) -> str:
    q = (args or "").strip()
    if not q:
        from MedlarTV.core.time_lookup import get_default_local_time
        res = get_default_local_time()
        if res:
            return res
        return "Unable to get local time"
    res = get_times_for_location(q)
    if not res:
        return f"Location not found: {q}"
    if isinstance(res, str) and res.lower().startswith("current time in"):
        return res
    return f"Current time in {q}: {res}"

def handle_worldclock(username: str, args: str, context: CommandContext) -> str:
    summary = world_clock_summary()
    return summary

def handle_timezones(username: str, args: str, context: CommandContext) -> str:
    f = (args or "").strip() or None
    zones = list_timezones(f)
    if not zones:
        return "No timezones found"
    count = len(zones)
    sample = ", ".join(zones[:12])
    if f:
        return f"{count} zones match '{f}': {sample}"
    return f"{count} zones available: {sample}"

def handle_search(username: str, args: str, context: CommandContext) -> str:
    q = (args or "").strip()
    if not q:
        return "Usage: !search <query>"
    try:
        results = search_web(q, max_results=2)
    except Exception:
        results = []
    if not results:
        return f"No results for: {q}"
    parts = []
    for r in results[:2]:
        t = r.get("title", "N/A")
        u = r.get("href", "")
        if u:
            parts.append(f"{t} — {u}")
        else:
            parts.append(t)
    return " | ".join(parts)

def handle_wiki(username: str, args: str, context: CommandContext) -> str:
    q = (args or "").strip()
    if not q:
        return "Usage: !wiki <topic>"
    try:
        res = search_wikipedia(q, sentences=2)
    except Exception:
        res = None
    if not res:
        return f"No Wikipedia page found for: {q}"
    title = res.get("title", q)
    summary = res.get("summary", "")
    url = res.get("url", "")
    msg = f"{title}: {summary}"
    if len(msg) > 280:
        msg = msg[:277] + "..."
    if url:
        return f"{msg} | {url}"
    return msg

def handle_t(username: str, args: str, context: CommandContext) -> str:
    return handle_t_command(args, username)

def handle_tlang(username: str, args: str, context: CommandContext) -> str:
    return handle_tlang_command()

def handle_thelp(username: str, args: str, context: CommandContext) -> str:
    return TRANSLATE_HELP

COMMAND_REGISTRY: Dict[str, Dict[str, Any]] = {
    "ping": {
        "handler": handle_ping,
        "permissions": [PERMISSION_EVERYONE],
        "description": "Check bot latency and responsiveness",
    },
    "status": {
        "handler": handle_status,
        "permissions": [PERMISSION_EVERYONE],
        "description": "Check status of all bot systems",
    },
    "emotion": {
        "handler": handle_emotion,
        "permissions": [PERMISSION_EVERYONE],
        "description": "Show MedlarTV's current dominant emotion",
    },
    "emotions": {
        "handler": handle_emotions,
        "permissions": [PERMISSION_EVERYONE],
        "description": "Show top 3 emotions with percentages",
    },
    "feelstate": {
        "handler": handle_feelstate,
        "permissions": [PERMISSION_EVERYONE],
        "description": "Show detailed emotional state description",
    },
    "time": {
        "handler": handle_time,
        "permissions": [PERMISSION_EVERYONE],
        "description": "Get current time for a location/country",
        "usage": "!time <location>",
    },
    "search": {
        "handler": handle_search,
        "permissions": [PERMISSION_EVERYONE],
        "description": "Web search via DuckDuckGo",
        "usage": "!search <query>",
    },
    "wiki": {
        "handler": handle_wiki,
        "permissions": [PERMISSION_EVERYONE],
        "description": "Wikipedia lookup",
        "usage": "!wiki <topic>",
    },
    "worldclock": {
        "handler": handle_worldclock,
        "permissions": [PERMISSION_EVERYONE],
        "description": "World clock summary across major cities",
    },
    "timezones": {
        "handler": handle_timezones,
        "permissions": [PERMISSION_EVERYONE],
        "description": "List available timezones (optional filter)",
        "usage": "!timezones [filter]",
    },
    "t": {
        "handler": handle_t,
        "permissions": [PERMISSION_EVERYONE],
        "description": "Translate text to another language",
        "usage": "!t <lang> <text>",
    },
    "tlang": {
        "handler": handle_tlang,
        "permissions": [PERMISSION_EVERYONE],
        "description": "Show supported translation languages",
    },
    "thelp": {
        "handler": handle_thelp,
        "permissions": [PERMISSION_EVERYONE],
        "description": "Show translation command usage",
    },
    "resetemotions": {
        "handler": handle_resetemotions,
        "permissions": [PERMISSION_PILOT, PERMISSION_MOD],
        "description": "Reset all emotions to baseline (Pilot/Mod only)",
    },
    "streaminfo": {
        "handler": handle_streaminfo,
        "permissions": [PERMISSION_EVERYONE],
        "description": "Get current stream information (title, game, viewers, uptime)",
    },
    "title": {
        "handler": handle_title,
        "permissions": [PERMISSION_EVERYONE],
        "description": "Get or set stream title",
        "usage": "!title [new title] - Leave blank to view, provide title to set",
    },
    "game": {
        "handler": handle_game,
        "permissions": [PERMISSION_EVERYONE],
        "description": "Get or set stream category/game",
        "usage": "!game [new game] - Leave blank to view, provide game name to set",
    },
    "commands": {
        "handler": handle_commands,
        "permissions": [PERMISSION_EVERYONE],
        "description": "Show all available commands",
    },
}