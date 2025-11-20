# Refactored twitch_listener.py
# Clean, stable, updated for new command handlers & OAuth-safe stream management

import os
import socket
import ssl
import time
import threading
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import yaml

from MedlarTV.core.fuzzy_trigger import should_respond
from MedlarTV.core.command_handlers import execute_command
from MedlarTV.core.moderation import check_message, execute_timeout, execute_ban, execute_delete
from MedlarTV.core.twitch_events import (
    detect_raid, detect_subscription, detect_channel_point_redemption, detect_bits,
)
from MedlarTV.core.llm_brain import generate_response

log = logging.getLogger("twitch_listener")

# ----------------------------------------------------------------------------
# IRC Connection Setup
# ----------------------------------------------------------------------------

TWITCH_SERVER = "irc.chat.twitch.tv"
TWITCH_PORT = 6697

# IMPORTANT:
# IRC login MUST use the BOT token, not broadcaster token.
OAUTH_TOKEN = os.getenv("MEDLARTV_TWITCH_TOKEN", "")

# Bot nickname
BOT_NICK = os.getenv("TWITCH_NICK", "MedlarTV")

# Twitch channel
CHANNEL = os.getenv("TWITCH_CHANNEL", "#devilmedlar")

# Clean oauth format
if OAUTH_TOKEN.startswith("oauth:"):
    IRC_TOKEN = OAUTH_TOKEN
else:
    IRC_TOKEN = f"oauth:{OAUTH_TOKEN}"

# ----------------------------------------------------------------------------
# Co-Pilot management
# ----------------------------------------------------------------------------

_COPILOTS_FILE = Path(__file__).resolve().parents[1] / "config" / "copilots.yaml"

def _ensure_copilots_file() -> None:
    if not _COPILOTS_FILE.exists():
        data = {"copilots": {"active": [], "history": []}}
        _COPILOTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with _COPILOTS_FILE.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)

def _load_copilots() -> Dict[str, Any]:
    _ensure_copilots_file()
    try:
        with _COPILOTS_FILE.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return data
    except Exception:
        return {"copilots": {"active": [], "history": []}}

def _save_copilots(data: Dict[str, Any]) -> None:
    _COPILOTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with _COPILOTS_FILE.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f)

def _get_active_copilots() -> List[str]:
    data = _load_copilots()
    return list(map(str, data.get("copilots", {}).get("active", [])))

def _role_prefix(username: str) -> str:
    try:
        channel_name = CHANNEL.lstrip("#").lower()
        if username.lower() == channel_name:
            return "Pilot "
        if username.lower() in [u.lower() for u in _get_active_copilots()]:
            return f"Co-Pilot @{username} "
        return f"@{username} "
    except Exception:
        return f"@{username} "

def _prepare_msg(text: str) -> str:
    try:
        return " ".join(text.splitlines())
    except Exception:
        return text

def _add_copilot(username: str) -> bool:
    username = username.strip()
    if not username:
        return False
    data = _load_copilots()
    active = data.setdefault("copilots", {}).setdefault("active", [])
    history = data["copilots"].setdefault("history", [])
    uname = username
    if uname.lower() not in [u.lower() for u in active]:
        active.append(uname)
        history.append({"action": "add", "user": uname, "ts": time.time()})
        _save_copilots(data)
        return True
    return False

def _remove_copilot(username: str) -> bool:
    username = username.strip()
    if not username:
        return False
    data = _load_copilots()
    active = data.setdefault("copilots", {}).setdefault("active", [])
    history = data["copilots"].setdefault("history", [])
    idx = None
    for i, u in enumerate(active):
        if u.lower() == username.lower():
            idx = i
            break
    if idx is not None:
        removed = active.pop(idx)
        history.append({"action": "remove", "user": removed, "ts": time.time()})
        _save_copilots(data)
        return True
    return False

# ----------------------------------------------------------------------------
# IRC CLIENT CLASS
# ----------------------------------------------------------------------------

class TwitchIRC:
    def __init__(self):
        self.sock: Optional[socket.socket] = None
        self.connected: bool = False
        self.stop_flag: bool = False

    # ---------------------------- CONNECT ----------------------------
    def connect(self):
        log.info("[IRC] Connecting to Twitch IRC…")
        base_sock = socket.socket()
        self.sock = ssl.wrap_socket(base_sock)
        self.sock.connect((TWITCH_SERVER, TWITCH_PORT))

        # Login
        self._send_raw(f"PASS {IRC_TOKEN}")
        self._send_raw(f"NICK {BOT_NICK}")
        self._send_raw(f"JOIN {CHANNEL}")
        self._send_raw("CAP REQ :twitch.tv/commands twitch.tv/tags twitch.tv/membership")

        self.connected = True
        log.info(f"[IRC] Connected as {BOT_NICK} to {CHANNEL}")

    # ------------------------------------------------------------------
    def _send_raw(self, text: str):
        if not self.sock:
            return
        self.sock.send((text + "\r\n").encode("utf-8"))

    def send_message(self, msg: str):
        if not self.connected:
            return
        self._send_raw(f"PRIVMSG {CHANNEL} :{msg}")

    # ------------------------------ LOOP ------------------------------
    def listen(self):
        buffer = ""
        while not self.stop_flag:
            try:
                if not self.sock:
                    break

                data = self.sock.recv(2048).decode("utf-8", errors="ignore")
                if not data:
                    continue

                buffer += data
                lines = buffer.split("\r\n")
                buffer = lines.pop()

                for line in lines:
                    self._handle_raw_message(line)

            except Exception as e:
                log.error(f"[IRC] Error: {e}")
                time.sleep(1)

    def stop(self):
        self.stop_flag = True
        self.connected = False
        if self.sock:
            self.sock.close()

    # ------------------------------------------------------------------
    def _handle_raw_message(self, line: str):
        if line.startswith("PING"):
            self._send_raw("PONG :tmi.twitch.tv")
            return

        # PRIVMSG, USERNOTICE, JOIN/PART events etc.
        self._process_incoming(line)

    # ------------------------------------------------------------------
    def _process_incoming(self, raw: str):
        # Parse tags & username
        tags, username, message = self._parse_message(raw)
        log.debug(f"[DEBUG] RAW PARSED: user={username}, msg={message}, raw={raw}")

        if username is None or message is None:
            return

        ctx: Dict[str, Any] = {
            "bot_nick": BOT_NICK,
            "socket_connected": self.connected,
            "bridge_connected": False,
            "message_timestamp": time.time(),
        }

        # ------------------ EVENT DETECTION ------------------

        # Raid
        raid_info = detect_raid(raw)
        if raid_info:
            self.send_message(
                f"⚡ RAID from {raid_info['raider']} with {raid_info['viewer_count']} viewers!"
            )
            return

        # Sub, resub, gift
        sub_info = detect_subscription(raw)
        if sub_info:
            from MedlarTV.core.twitch_events import get_sub_response
            self.send_message(get_sub_response(sub_info))
            return

        # Channel points
        redeem = detect_channel_point_redemption(raw)
        if redeem:
            from MedlarTV.core.twitch_events import get_channel_point_response
            self.send_message(get_channel_point_response(redeem))
            return

        # Bits
        bits = detect_bits(raw)
        if bits:
            self.send_message(f"💎 {bits['user']} cheered {bits['amount']} bits!")
            return

        # ------------------ CHAT MESSAGE ------------------

        if message.startswith("!"):
            self._handle_command(username, message, ctx, tags)
        else:
            self._handle_regular_message(username, message, ctx, tags)

    # ----------------------------------------------------------------------------
    def _parse_message(self, raw: str):
        # Twitch IRC with tags
        # Format: @tags :username!something PRIVMSG #chan :message
        try:
            tags = {}
            username = None
            message = None

            if raw.startswith("@"):  # has tags
                tag_str, rest = raw[1:].split(" ", 1)
                for t in tag_str.split(";"):
                    if "=" in t:
                        k, v = t.split("=", 1)
                        tags[k] = v
                raw = rest

            if "PRIVMSG" in raw:
                parts = raw.split("PRIVMSG", 1)
                prefix = parts[0]
                msg_part = parts[1]

                # Extract username
                if "!" in prefix:
                    username = prefix.split("!", 1)[0].lstrip(":")

                # Extract message
                if " :" in msg_part:
                    message = msg_part.split(" :", 1)[1]

            return tags, username, message

        except Exception:
            return {}, None, None

    # ------------------- REGULAR CHAT ----------------------
    def _handle_regular_message(self, username: str, msg: str, ctx: Dict[str, Any], tags: Dict[str, Any]):
        log.debug(f"[DEBUG] Incoming chat: @{username}: {msg}")

        # Auto-moderation
        result = check_message(username, msg, tags)
        if not result["is_allowed"]:
            action = result.get("action")
            duration = result.get("duration", 0)
            reason = result.get("reason", "violation")

            if action == "timeout":
                execute_timeout(self.sock, CHANNEL, username, duration, reason)
            elif action == "ban":
                execute_ban(self.sock, CHANNEL, username, reason)
            elif action == "delete":
                msg_id = result.get("msg_id")
                if msg_id:
                    execute_delete(self.sock, CHANNEL, msg_id)
            elif action == "warn":
                self.send_message(f"@{username} ⚠️ {reason}")
            return

        # ------------------------------------------
        # Fuzzy-triggered Medlar response (IMPORTANT)
        # ------------------------------------------

        log.debug(f"[DEBUG] Running should_respond() for msg='{msg}'")

        decision = should_respond(msg)

        log.debug(f"[DEBUG] should_respond() returned: {decision}")

        if decision:
            log.debug(
                f"[DEBUG] Calling generate_response(user={username}, msg={msg})"
            )

            reply = generate_response(msg, username)

            log.debug(f"[DEBUG] generate_response() output: {reply}")

            if reply:
                self.send_message(_prepare_msg(_role_prefix(username) + reply))

    # ------------------- COMMAND HANDLING ----------------------
    def _handle_command(self, username: str, full: str, ctx: Dict[str, Any], tags: Dict[str, Any]):
        parts = full.split(" ", 1)
        cmd = parts[0].lstrip("!").lower()
        args = parts[1] if len(parts) > 1 else ""

        # Determine role
        role = "user"
        if tags.get("mod") == "1":
            role = "mod"
        if username.lower() == CHANNEL.lstrip("#").lower():
            role = "pilot"
        if tags.get("vip") == "1":
            role = "vip"

        if role not in {"pilot", "mod"}:
            try:
                if username.lower() in [u.lower() for u in _get_active_copilots()]:
                    role = "copilot"
            except Exception:
                pass

        if cmd in {"addcopilot", "removecopilot", "listcopilots"}:
            if cmd == "addcopilot":
                target = args.strip().split(" ")[0] if args.strip() else ""
                if role not in {"pilot", "mod"}:
                    self.send_message(f"@{username} ❌ Only Broadcaster and Mods can add co-pilots.")
                    return
                if not target:
                    self.send_message(f"@{username} ❌ Usage: !addcopilot <username>")
                    return
                ok = _add_copilot(target)
                if ok:
                    self.send_message(f"Co-Pilot {target} registered! Welcome to the squad! 🚀")
                else:
                    self.send_message(f"@{username} ⚠️ {target} is already a Co-Pilot.")
                return
            if cmd == "removecopilot":
                target = args.strip().split(" ")[0] if args.strip() else ""
                if role not in {"pilot", "mod", "copilot"}:
                    self.send_message(f"@{username} ❌ Only Broadcaster, Mods, or Co-Pilots can remove co-pilots.")
                    return
                if not target:
                    self.send_message(f"@{username} ❌ Usage: !removecopilot <username>")
                    return
                ok = _remove_copilot(target)
                if ok:
                    self.send_message(f"Co-Pilot {target} unregistered. Thanks for flying with us! o7")
                else:
                    self.send_message(f"@{username} ⚠️ {target} is not currently a Co-Pilot.")
                return
            if cmd == "listcopilots":
                names = _get_active_copilots()
                listing = ", ".join(names) if names else "none"
                self.send_message(f"Active Co-Pilots: {listing}")
                return

        response = execute_command(cmd, username, role, args, ctx)

        if response:
            self.send_message(_prepare_msg(_role_prefix(username) + response))
        else:
            log.debug(
                f"[DEBUG] Command fallback to generate_response(user={username}, msg={full})"
            )
            reply = generate_response(full, username)
            log.debug(f"[DEBUG] generate_response() command output: {reply}")
            if reply:
                self.send_message(_prepare_msg(_role_prefix(username) + reply))


# ----------------------------------------------------------------------------
# THREAD CONTROL
# ----------------------------------------------------------------------------

_listener_instance: Optional[TwitchIRC] = None
_listener_thread: Optional[threading.Thread] = None


def start_listener():
    global _listener_instance, _listener_thread

    if _listener_instance and _listener_instance.connected:
        log.info("[Listener] Already running.")
        return

    _listener_instance = TwitchIRC()
    _listener_instance.connect()

    _listener_thread = threading.Thread(target=_listener_instance.listen, daemon=True)
    _listener_thread.start()

    log.info("[Listener] Twitch listener started.")


def stop_listener():
    global _listener_instance
    if _listener_instance:
        _listener_instance.stop()
        log.info("[Listener] Stopped.")

