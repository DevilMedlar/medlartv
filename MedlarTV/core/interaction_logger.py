import os
DEBUG = os.getenv("MEDLARTV_DEBUG", "false").lower() == "true"
if DEBUG:
    print("[DEBUG interaction_logger] Loaded interaction_logger.py")

"""
MedlarTV Interaction Logger
Logs chat interactions, commands, mood changes, and errors for analytics.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Configuration
ENABLE_LOGGING = os.getenv("ENABLE_INTERACTION_LOGGING", "true").lower() == "true"
LOG_DIRECTORY = os.getenv("LOG_DIRECTORY", "logs")

def _now_iso() -> str:
    """Return current UTC time in ISO format."""
    ts = datetime.utcnow().isoformat() + "Z"
    if DEBUG:
        print(f"[DEBUG interaction_logger] _now_iso() → {ts}")
    return ts

def ensure_log_directory() -> Path:
    """
    Ensure the log directory exists and return it as a Path object.
    """
    log_path = Path(LOG_DIRECTORY)
    if DEBUG:
        print(f"[DEBUG interaction_logger] ensure_log_directory() using path={log_path}")
    log_path.mkdir(parents=True, exist_ok=True)
    if DEBUG:
        print(f"[DEBUG interaction_logger] Directory ensured: {log_path.exists()}")
    return log_path

def _append_jsonl(filename: str, entry: Dict[str, Any]) -> None:
    if DEBUG:
        print(f"[DEBUG interaction_logger] _append_jsonl() called for file={filename}")
    """
    Append a single JSON object as a line to a .jsonl log file.
    """
    if not ENABLE_LOGGING:
        return

    try:
        log_path = ensure_log_directory()
        if DEBUG:
            print(f"[DEBUG interaction_logger] Logging path resolved → {log_path}")
        log_file = log_path / filename

        if DEBUG:
            print(f"[DEBUG interaction_logger] Writing entry to {log_file}")
            print(f"[DEBUG interaction_logger] Entry data: {entry}")

        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    except Exception as e:
        if DEBUG:
            print(f"[DEBUG interaction_logger] ERROR inside _append_jsonl: {e}")
        print(f"[Logger] Failed to write to {filename}: {e}")

# ---------------------------------------------------------------------------
# PUBLIC LOGGING APIS
# ---------------------------------------------------------------------------

def log_interaction(
    user: str,
    message: str,
    response: Optional[str] = None,
    mood: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    if DEBUG:
        print(f"[DEBUG interaction_logger] log_interaction() user={user} message={message} mood={mood}")
    """
    Log a basic chat interaction between a user and MedlarTV.
    """
    if not ENABLE_LOGGING:
        return

    entry: Dict[str, Any] = {
        "ts": _now_iso(),
        "type": "interaction",
        "user": user,
        "message": message,
        "response": response,
        "mood": mood,
    }
    if context:
        entry["context"] = context

    if DEBUG:
        print(f"[DEBUG interaction_logger] log_interaction() entry={entry}")
    _append_jsonl("interactions.jsonl", entry)

def log_command(
    user: str,
    command: str,
    args: Optional[Dict[str, Any]] = None,
    success: bool = True,
    error: Optional[str] = None,
) -> None:
    if DEBUG:
        print(f"[DEBUG interaction_logger] log_command() user={user} command={command} success={success}")
    """
    Log a command invocation (e.g., !title, !so).
    """
    if not ENABLE_LOGGING:
        return

    entry: Dict[str, Any] = {
        "ts": _now_iso(),
        "type": "command",
        "user": user,
        "command": command,
        "success": success,
    }
    if args:
        entry["args"] = args
    if error:
        entry["error"] = error

    if DEBUG:
        print(f"[DEBUG interaction_logger] log_command() entry={entry}")
    _append_jsonl("commands.jsonl", entry)

def log_mood_change(
    old_mood: str,
    new_mood: str,
    reason: str,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    if DEBUG:
        print(f"[DEBUG interaction_logger] log_mood_change() {old_mood} → {new_mood}, reason={reason}")
    """
    Log when the emotional system changes dominant mood.
    """
    if not ENABLE_LOGGING:
        return

    entry: Dict[str, Any] = {
        "ts": _now_iso(),
        "type": "mood_change",
        "from": old_mood,
        "to": new_mood,
        "reason": reason,
    }
    if extra:
        entry["extra"] = extra

    if DEBUG:
        print(f"[DEBUG interaction_logger] log_mood_change() entry={entry}")
    _append_jsonl("mood_changes.jsonl", entry)

def log_error(
    error_type: str,
    error_message: str,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    if DEBUG:
        print(f"[DEBUG interaction_logger] log_error() type={error_type} msg={error_message}")
    """
    Log an internal error for debugging.
    """
    if not ENABLE_LOGGING:
        return

    entry: Dict[str, Any] = {
        "ts": _now_iso(),
        "type": "error",
        "error_type": error_type,
        "message": error_message,
    }
    if context:
        entry["context"] = context

    if DEBUG:
        print(f"[DEBUG interaction_logger] log_error() entry={entry}")
    _append_jsonl("errors.jsonl", entry)


def get_interaction_stats() -> Dict[str, Any]:
    if DEBUG:
        print("[DEBUG interaction_logger] get_interaction_stats() called")
    """
    Basic stats summary based on log file counts.
    """
    stats = {
        "interactions": 0,
        "commands": 0,
        "mood_changes": 0,
        "errors": 0,
    }

    try:
        log_path = ensure_log_directory()
        files = {
            "interactions.jsonl": "interactions",
            "commands.jsonl": "commands",
            "mood_changes.jsonl": "mood_changes",
            "errors.jsonl": "errors",
        }

        for filename, key in files.items():
            fpath = log_path / filename
            if fpath.exists():
                if DEBUG:
                    print(f"[DEBUG interaction_logger] Counting lines in → {fpath}")
                with fpath.open("r", encoding="utf-8") as f:
                    stats[key] = sum(1 for _ in f)
                if DEBUG:
                    print(f"[DEBUG interaction_logger] {key} count updated → {stats[key]}")

    except Exception as e:
        if DEBUG:
            print(f"[DEBUG interaction_logger] ERROR in get_interaction_stats: {e}")
        print(f"[Logger] Failed to compute stats: {e}")

    return stats

# ---------------------------------------------------------------------------
# SELF-TEST
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("[Logger] Running self-test...")
    log_interaction("test_user", "Hello Medlar!", "Hey there, pilot.", "hype")
    log_command("test_user", "!title", {"title": "New Stream Title"}, success=True)
    log_mood_change("chill", "hype", "test_reason")
    log_error("test_error", "Something went wrong", {"foo": "bar"})
    print(json.dumps(get_interaction_stats(), indent=2))
    print("[Logger] Self-test complete.")
 
