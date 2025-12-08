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
import winsound

from MedlarTV.core.fuzzy_trigger import should_respond
from MedlarTV.core.command_handlers import execute_command
from MedlarTV.core.moderation import check_message, execute_timeout, execute_ban, execute_delete
from MedlarTV.core.twitch_events import (
    detect_raid, detect_subscription, detect_channel_point_redemption, detect_bits,
)
from MedlarTV.core.llm_brain import generate_response
from MedlarTV.core.interaction_logger import log_interaction
from MedlarTV.core.time_lookup import should_lookup_time, get_times_for_location, get_default_local_time
from MedlarTV.core.web_search import search_intelligently, search_web
from MedlarTV.core.settings import is_enabled

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
        data = {"copilots": {"active": []}}
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
        return {"copilots": {"active": []}}

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

def _username_for_model(username: str) -> str:
    try:
        channel_name = CHANNEL.lstrip("#").lower()
        if username.lower() == channel_name:
            return "Pilot"
        return username
    except Exception:
        return username

def _sanitize_reply_text(text: str, username: str) -> str:
    try:
        t = str(text)
        # normalize spacing and zero-widths
        t = t.replace("\u00a0", " ").replace("\u200b", "").replace("\u2009", " ")
        t = t.lstrip()
        import re
        # Remove leading speaker label
        t = re.sub(r"^(?i)(medlartv|medlar)\s*:\s*", "", t)
        # Remove leading duplicates of the addressed username
        uname = re.escape(username)
        patterns = [
            # Direct leading name or @name with punctuation/space
            rf"^(?i)\s*@?\s*{uname}\b[^A-Za-z0-9]*\s*",
            # Greeting followed by name (allow emojis/punct between)
            rf"^(?i)\s*(hey|hi|hello|yo|hiya|hey there|sup|what's up|whats up)\b[^A-Za-z0-9@]*@?\s*{uname}\b[^A-Za-z0-9]*\s*",
        ]
        for p in patterns:
            t = re.sub(p, "", t)
        return t.lstrip()
    except Exception:
        return text

def _is_pilot(username: str) -> bool:
    try:
        return username.lower() == CHANNEL.lstrip("#").lower()
    except Exception:
        return False

def _prefix_for_llm_reply(username: str) -> str:
    try:
        if _is_pilot(username):
            return ""
        return _role_prefix(username)
    except Exception:
        return _role_prefix(username)

_TIMERS_FILE = Path(__file__).resolve().parents[1] / "config" / "timers.yaml"

def _load_timers_yaml() -> List[Dict[str, Any]]:
    try:
        with _TIMERS_FILE.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return list(data.get("timers", []))
    except Exception:
        return []

def _get_commands_link() -> str:
    try:
        cfg = Path(__file__).resolve().parents[1] / "config" / "commands.yaml"
        with cfg.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        info = (data.get("commands") or {}).get("commands") or {}
        resp = str(info.get("response", ""))
        import re
        m = re.search(r"https?://[^\s]+", resp)
        if m:
            return m.group(0)
    except Exception:
        pass
    return os.getenv("MEDLAR_COMMANDS_URL", "https://DevilMedlar.github.io/medlar-commands-site/")

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
    uname = username
    if uname.lower() not in [u.lower() for u in active]:
        active.append(uname)
        # Persist active list only; write event to logs
        _save_copilots({"copilots": {"active": active}})
        log.info("[Copilot] add user=%s ts=%f", uname, time.time())
        return True
    return False

def _remove_copilot(username: str) -> bool:
    username = username.strip()
    if not username:
        return False
    data = _load_copilots()
    active = data.setdefault("copilots", {}).setdefault("active", [])
    idx = None
    for i, u in enumerate(active):
        if u.lower() == username.lower():
            idx = i
            break
    if idx is not None:
        removed = active.pop(idx)
        # Persist active list only; write event to logs
        _save_copilots({"copilots": {"active": active}})
        log.info("[Copilot] remove user=%s ts=%f", removed, time.time())
        return True
    return False

# ----------------------------------------------------------------------------
# Firebot-like Events & Effects
# ----------------------------------------------------------------------------

_seen_users: set[str] = set()

def _load_event_rules() -> list[dict[str, Any]]:
    cfg = Path(__file__).resolve().parents[1] / "config" / "events.yaml"
    try:
        with cfg.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return list(data.get("events", []))
    except Exception:
        return []

def _is_ignored(username: str) -> bool:
    try:
        cfg = Path(__file__).resolve().parents[1] / "config" / "events.yaml"
        with cfg.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        ignore = set(str(u).lower() for u in (data.get("ignored_users") or []))
        return username.lower() in ignore
    except Exception:
        return False

def _play_local_sound(path: str, duration_ms: int = 0) -> bool:
    p = Path(path)
    if not p.exists():
        return False
    # simple cooldown per file to avoid echo/retrigger
    try:
        with _audio_lock:
            last = _last_audio_play.get(str(p), 0.0)
            now = time.time()
            delta = now - last
            if delta < 1.0:
                try:
                    log.info(f"[SoundEffect] cooldown skip path={str(p)} delta={delta:.2f}s")
                except Exception:
                    pass
                return False
            _last_audio_play[str(p)] = now
            try:
                log.info(f"[SoundEffect] cooldown pass path={str(p)}")
            except Exception:
                pass
    except Exception:
        pass

    if p.suffix.lower() == ".wav":
        try:
            try:
                log.info(f"[SoundEffect] playing wav path={str(p)}")
            except Exception:
                pass
            winsound.PlaySound(str(p), winsound.SND_FILENAME | winsound.SND_ASYNC)
            return True
        except Exception:
            try:
                log.error(f"[SoundEffect] wav playback failed path={str(p)}")
            except Exception:
                pass
            return False
    if p.suffix.lower() in {".mp3", ".m4a", ".aac"}:
        try:
            import subprocess
            sleep_ms = int(duration_ms) if duration_ms and duration_ms > 0 else 10000
            ps = (
                "Add-Type -AssemblyName presentationCore; "
                "$p = New-Object System.Windows.Media.MediaPlayer; "
                f"$p.Open(\"{str(p)}\"); $p.Volume=1; $p.Play(); "
                f"Start-Sleep -Milliseconds {sleep_ms}"
            )
            try:
                log.info(f"[SoundEffect] playing via MediaPlayer path={str(p)}")
            except Exception:
                pass
            subprocess.Popen(["powershell", "-NoProfile", "-Command", ps])
            return True
        except Exception:
            try:
                log.error(f"[SoundEffect] MediaPlayer playback failed path={str(p)}")
            except Exception:
                pass
            pass
    try:
        try:
            log.info(f"[SoundEffect] opening default player path={str(p)}")
        except Exception:
            pass
        os.startfile(str(p))
        return True
    except Exception:
        try:
            log.error(f"[SoundEffect] default player open failed path={str(p)}")
        except Exception:
            pass
        return False

def _apply_event_rules(event_name: str, username: str, send_message: callable, sock) -> None:
    if _is_ignored(username):
        try:
            log.info(f"[Events] ignored user={username} for trigger={event_name}")
        except Exception:
            pass
        return
    rules = _load_event_rules()

    # Exclusive handling: if any rule explicitly targets this username, only run those
    try:
        exact_rules = []
        for rr in rules:
            if str(rr.get("trigger", "")) != event_name:
                continue
            fl = rr.get("filters", {}) or {}
            eq = str(fl.get("username_equals", ""))
            if eq and eq.lower() == username.lower():
                exact_rules.append(rr)
        if exact_rules:
            rules_to_run = exact_rules
        else:
            rules_to_run = [r for r in rules if str(r.get("trigger", "")) == event_name]
    except Exception:
        rules_to_run = [r for r in rules if str(r.get("trigger", "")) == event_name]

    for r in rules_to_run:
        if str(r.get("trigger", "")) != event_name:
            continue
        flt = r.get("filters", {}) or {}
        uname_eq = str(flt.get("username_equals", ""))
        if uname_eq and uname_eq.lower() != username.lower():
            continue
        try:
            exclude_list = flt.get("username_not_in", []) or []
            exclude_norm = set(str(u).lower().lstrip("@") for u in exclude_list)
            if username.lower().lstrip("@") in exclude_norm:
                continue
        except Exception:
            pass
        effects = r.get("effects", []) or []
        try:
            log.info(f"[Events] trigger={event_name} user={username} matched rule={r.get('name','')} effects={len(effects)}")
        except Exception:
            pass
        for eff in effects:
            try:
                delay_ms = int(eff.get("delay_ms", 0))
            except Exception:
                delay_ms = 0
            if delay_ms > 0:
                try:
                    time.sleep(delay_ms / 1000.0)
                except Exception:
                    pass
            t = str(eff.get("type", ""))
            if t == "chat":
                msg = str(eff.get("message", ""))
                if msg:
                    try:
                        formatted = msg
                        formatted = formatted.replace("@{username}", f"@{username}")
                        formatted = formatted.replace("{username}", username)
                    except Exception:
                        formatted = msg
                    send_message(formatted)
            elif t == "twitch_shoutout":
                target = str(eff.get("target", username))
                try:
                    from MedlarTV.core.stream_management import send_shoutout
                    ok = send_shoutout(target)
                except Exception:
                    ok = False
                if not ok:
                    from MedlarTV.core.moderation import execute_shoutout
                    try:
                        execute_shoutout(sock, CHANNEL, target)
                    except Exception:
                        pass
                try:
                    log.info(f"[Events] shoutout effect target={target} api_ok={ok}")
                except Exception:
                    pass
            elif t == "play_sound":
                path = str(eff.get("path", ""))
                if path:
                    try:
                        duration_ms = int(eff.get("duration_ms", 0))
                    except Exception:
                        duration_ms = 0
                    _play_local_sound(path, duration_ms)

# ----------------------------------------------------------------------------
# IRC CLIENT CLASS
# ----------------------------------------------------------------------------

class TwitchIRC:
    def __init__(self):
        self.sock: Optional[socket.socket] = None
        self.connected: bool = False
        self.stop_flag: bool = False
        self.available_emotes: List[str] = []
        self.user_emotes: List[str] = []
        self._timers: List[Dict[str, Any]] = []
        self._chat_count: int = 0
        self._next_chat_due: Dict[str, int] = {}
        self._next_time_due: Dict[str, float] = {}
        self._timer_stop: threading.Event = threading.Event()
        self._timer_thread: Optional[threading.Thread] = None

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

        try:
            names = _get_active_copilots()
            for uname in names:
                n = str(uname).strip().lstrip("@")
                if not n:
                    continue
                chan = f"#{n.lower()}"
                if chan != CHANNEL:
                    self._send_raw(f"JOIN {chan}")
                    try:
                        log.info("[IRC] Joining copilot channel %s", chan)
                    except Exception:
                        pass
        except Exception:
            pass

        self.connected = True
        log.info(f"[IRC] Connected as {BOT_NICK} to {CHANNEL}")

        try:
            self._init_emotes()
        except Exception:
            pass

        try:
            self._timers = _load_timers_yaml()
            self._init_timers()
        except Exception:
            pass

        try:
            if os.getenv("ENABLE_ONLINE_OFFLINE_MSGS", "true").lower() == "true":
                self._send_raw(f"PRIVMSG {CHANNEL} :MedlarTV online")
        except Exception:
            pass

    # ------------------------------------------------------------------
    def _send_raw(self, text: str):
        if not self.sock:
            return
        self.sock.send((text + "\r\n").encode("utf-8"))

    def send_message(self, msg: str):
        if not self.connected:
            return
        try:
            try:
                if is_enabled("content_filter"):
                    from MedlarTV.core.content_filter import filter_message, get_safety_response
                    ok, filtered, reason = filter_message(msg, None)
                    base_msg = filtered if ok and filtered is not None else get_safety_response()
                else:
                    base_msg = msg
            except Exception:
                base_msg = msg
            try:
                final = self._decorate_message(base_msg)
            except Exception:
                final = base_msg
        except Exception:
            final = msg
        self._send_raw(f"PRIVMSG {CHANNEL} :{final}")

    def _init_emotes(self) -> None:
        try:
            self.available_emotes = []
            self.user_emotes = []
            try:
                log.info("[IRC] Emotes will be loaded from USERSTATE emote-sets for bot account")
            except Exception:
                pass
        except Exception:
            pass

    def _decorate_message(self, msg: str) -> str:
        try:
            if os.getenv("ENABLE_EMOTE_RESPONSES", "true").lower() != "true":
                return _prepare_msg(msg)
            avail = self.user_emotes or []
            try:
                from MedlarTV.core.emotional_system import get_current_emotion
                from MedlarTV.core.emotion_emote_selector import add_emotion_emote
                emotion = get_current_emotion()
                base = _prepare_msg(msg)
                return add_emotion_emote(base, emotion, avail)
            except Exception:
                pass
            try:
                from MedlarTV.core.twitch_events import add_random_emote
                base = _prepare_msg(msg)
                return add_random_emote(base, avail)
            except Exception:
                pass
            return _prepare_msg(msg)
        except Exception:
            return _prepare_msg(msg)

    def _load_timers(self) -> List[Dict[str, Any]]:
        try:
            return _load_timers_yaml()
        except Exception:
            return []

    def _init_timers(self) -> None:
        try:
            now = time.time()
            self._next_chat_due.clear()
            self._next_time_due.clear()
            for t in self._timers:
                if not t.get("enabled"):
                    continue
                typ = str(t.get("type", "")).lower()
                k = str(t.get("id", "")) or str(hash(t.get("message", "")))
                if typ == "chats":
                    n = int(t.get("interval_chats", 0))
                    if n > 0:
                        self._next_chat_due[k] = n
                elif typ == "time":
                    m = int(t.get("interval_minutes", 0))
                    if m > 0:
                        self._next_time_due[k] = now + m * 60
            if self._next_time_due:
                self._timer_stop.clear()
                self._timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
                self._timer_thread.start()
        except Exception:
            pass

    def _timer_loop(self) -> None:
        while not self._timer_stop.is_set():
            try:
                now = time.time()
                for t in self._timers:
                    if not t.get("enabled"):
                        continue
                    if str(t.get("type", "")).lower() != "time":
                        continue
                    k = str(t.get("id", "")) or str(hash(t.get("message", "")))
                    m = int(t.get("interval_minutes", 0))
                    if m <= 0:
                        continue
                    due_ts = self._next_time_due.get(k)
                    if due_ts is None:
                        self._next_time_due[k] = now + m * 60
                        continue
                    if now >= due_ts:
                        self.send_message(str(t.get("message", "")))
                        self._next_time_due[k] = now + m * 60
            except Exception:
                pass
            time.sleep(1.0)

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
        try:
            if self.sock and os.getenv("ENABLE_ONLINE_OFFLINE_MSGS", "true").lower() == "true":
                self._send_raw(f"PRIVMSG {CHANNEL} :MedlarTV offline")
        except Exception:
            pass
        self.connected = False
        if self.sock:
            self.sock.close()
        try:
            self._timer_stop.set()
        except Exception:
            pass

    # ------------------------------------------------------------------
    def _handle_raw_message(self, line: str):
        if line.startswith("PING"):
            self._send_raw("PONG :tmi.twitch.tv")
            return

        try:
            if " USERSTATE " in line and "emote-sets=" in line:
                idx = line.find("emote-sets=")
                if idx != -1:
                    seg = line[idx:].split(";", 1)[0]
                    val = seg.split("=", 1)[1]
                    sets = [s.strip() for s in val.split(",") if s.strip()]
                    if sets:
                        self._fetch_emote_sets(sets)
            if " GLOBALUSERSTATE " in line and "emote-sets=" in line:
                idx = line.find("emote-sets=")
                if idx != -1:
                    seg = line[idx:].split(";", 1)[0]
                    val = seg.split("=", 1)[1]
                    sets = [s.strip() for s in val.split(",") if s.strip()]
                    if sets:
                        self._fetch_emote_sets(sets)
        except Exception:
            pass

        if " JOIN " in line:
            try:
                prefix = line.split(" JOIN ", 1)[0]
                if "!" in prefix:
                    username = prefix.split("!", 1)[0].lstrip(":")
                    key = username.lower()
                    if key not in _arrived_users:
                        _arrived_users.add(key)
                        _apply_event_rules("viewer_arrived", username, self.send_message, self.sock)
            except Exception:
                pass
            return

        self._process_incoming(line)

    def _fetch_emote_sets(self, set_ids: List[str]) -> None:
        try:
            token = os.getenv("DEVILMEDLAR_TWITCH_TOKEN", "").replace("oauth:", "")
            client_id = os.getenv("APP_TWITCH_CLIENT_ID", "")
            if not token or not client_id:
                return
            import requests
            headers = {"Client-ID": client_id, "Authorization": f"Bearer {token}"}
            names: List[str] = []
            for sid in set_ids:
                try:
                    r = requests.get(
                        "https://api.twitch.tv/helix/chat/emotes",
                        headers=headers,
                        params={"emote_set_id": sid},
                        timeout=10,
                    )
                    if r.status_code == 200:
                        data = r.json().get("data", [])
                        for em in data:
                            n = em.get("name")
                            if n:
                                names.append(str(n))
                except Exception:
                    pass
            if names:
                # Use only the bot's accessible emotes from USERSTATE
                self.user_emotes = sorted(set(names))
                self.available_emotes = list(self.user_emotes)
                try:
                    log.info(f"[IRC] Bot emotes loaded from emote-sets, total available={len(self.user_emotes)}")
                except Exception:
                    pass
        except Exception:
            pass

    # ------------------------------------------------------------------
    def _process_incoming(self, raw: str):
        # Parse tags & username
        tags, username, message = self._parse_message(raw)
        log.debug(f"[DEBUG] RAW PARSED: user={username}, msg={message}, raw={raw}")

        if username is None or message is None:
            return

        try:
            key = username.lower()
            if key not in _arrived_users:
                _arrived_users.add(key)
                _apply_event_rules("viewer_arrived", username, self.send_message, self.sock)
        except Exception:
            pass

        try:
            self._learn_emotes_from_message(tags, message)
        except Exception:
            pass

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

    def _learn_emotes_from_message(self, tags: Dict[str, Any], message: str) -> None:
        try:
            emtag = tags.get("emotes", "")
            if not emtag:
                return
            pieces: List[str] = []
            for grp in emtag.split("/"):
                if ":" not in grp:
                    continue
                _, ranges = grp.split(":", 1)
                for r in ranges.split(","):
                    if "-" not in r:
                        continue
                    s, e = r.split("-", 1)
                    try:
                        start = int(s)
                        end = int(e)
                        if 0 <= start <= end < len(message):
                            pieces.append(message[start:end+1])
                    except Exception:
                        continue
            # Do not learn emotes from others unless the bot can use them
            if pieces:
                allowed = set(self.user_emotes)
                learned = [p for p in pieces if p in allowed]
                if learned:
                    merged = sorted(set(self.user_emotes + learned))
                    self.user_emotes = merged
                    self.available_emotes = list(self.user_emotes)
                    try:
                        log.info(f"[IRC] Learned permitted emotes from chat, total available={len(self.user_emotes)}")
                    except Exception:
                        pass
        except Exception:
            pass

    # ------------------- REGULAR CHAT ----------------------
    def _handle_regular_message(self, username: str, msg: str, ctx: Dict[str, Any], tags: Dict[str, Any]):
        log.debug(f"[DEBUG] Incoming chat: @{username}: {msg}")
        try:
            if username and username.lower() == BOT_NICK.lower():
                return
        except Exception:
            pass
        try:
            self._chat_count += 1
            for t in self._timers:
                if not t.get("enabled"):
                    continue
                if str(t.get("type", "")).lower() == "chats":
                    k = str(t.get("id", "")) or str(hash(t.get("message", "")))
                    n = int(t.get("interval_chats", 0))
                    if n > 0:
                        due = self._next_chat_due.get(k, n)
                        if self._chat_count >= due:
                            self.send_message(str(t.get("message", "")))
                            self._next_chat_due[k] = due + n
        except Exception:
            pass

        # Auto-moderation disabled for user messages; only Medlar follows rules
        result = {"is_allowed": True}

        try:
            if username and username.lower() == "pokemoncommunitygame":
                ml = msg.strip().lower()
                bot_mention = f"@{BOT_NICK.lower()}"
                mentions_bot = (bot_mention in ml) or ("@medlartv" in ml)
                if not is_enabled("pcg_auto_catch"):
                    return
                # Ignore catch-success announcements
                catch_phrases = [
                    "has been caught by",
                    "has been caught",
                    "was caught by",
                    "catch successful",
                    "has been captured",
                ]
                if any(p in ml for p in catch_phrases):
                    return
                if ("a wild" in ml) and ("catch it using !pokecatch" in ml):
                    self._send_raw(f"PRIVMSG {CHANNEL} :!pokecatch ultraball")
                    return
                if ("don’t own that ball" in ml) or ("don't own that ball" in ml):
                    if mentions_bot:
                        self._send_raw(f"PRIVMSG {CHANNEL} :!pokeshop ultraball 1")
                    return
                if "purchase successful" in ml:
                    if mentions_bot:
                        self._send_raw(f"PRIVMSG {CHANNEL} :!pokecatch ultraball")
                    return
                # Ignore any other PokemonCommunityGame messages
                return
        except Exception:
            pass

        try:
            if _is_ignored(username):
                return
            lookup, location = should_lookup_time(msg)
        except Exception:
            lookup, location = False, None
        if lookup and location:
            try:
                ti = get_times_for_location(location)
            except Exception:
                ti = None
            if ti:
                final = _prepare_msg(_role_prefix(username) + ti)
                self.send_message(final)
                try:
                    log_interaction(username, msg, ti)
                except Exception:
                    pass
                return
            else:
                not_found = f"Location not found: {location}"
                final = _prepare_msg(_role_prefix(username) + not_found)
                self.send_message(final)
                try:
                    log_interaction(username, msg, not_found)
                except Exception:
                    pass
                return

        if lookup and not location:
            try:
                ti = get_default_local_time()
            except Exception:
                ti = None
            if ti:
                final = _prepare_msg(_role_prefix(username) + ti)
                self.send_message(final)
                try:
                    log_interaction(username, msg, ti)
                except Exception:
                    pass
                return

        try:
            ml = msg.strip().lower()
            kwords = ["medlar", "medlartv", BOT_NICK.lower()]
            asks = ["do you have", "any", "what", "show", "list"]
            if ("command" in ml) and any(a in ml for a in asks) and any(k in ml for k in kwords):
                link = _get_commands_link()
                text = f"Yeah i have commands, here is the link {link} — if you use !commands i will send link as well"
                final = _prepare_msg(_role_prefix(username) + text)
                self.send_message(final)
                try:
                    log_interaction(username, msg, text)
                except Exception:
                    pass
                return
        except Exception:
            pass

        # ------------------------------------------
        # Fuzzy-triggered Medlar response (IMPORTANT)
        # ------------------------------------------

        log.debug(f"[DEBUG] Running should_respond() for msg='{msg}'")

        decision = should_respond(msg)

        log.debug(f"[DEBUG] should_respond() returned: {decision}")

        if decision:
            if not is_enabled("llm_brain"):
                return
            log.debug(
                f"[DEBUG] Calling generate_response(user={username}, msg={msg})"
            )

            try:
                search_context = search_intelligently(msg)
            except Exception:
                search_context = ""
            enriched = msg + ("\n" + search_context if search_context else "")
            reply = generate_response(enriched, _username_for_model(username))

            log.debug(f"[DEBUG] generate_response() output: {reply}")

            if reply:
                ml = msg.strip().lower()
                wants_links = False
                try:
                    wants_links = (
                        ("find" in ml or "search" in ml or "lookup" in ml) and (
                            "twitch" in ml or "youtube" in ml or "twitter" in ml or "reddit" in ml or "channel" in ml
                        )
                    ) or ("on twitch" in ml)
                except Exception:
                    wants_links = False

                link_suffix = ""
                if wants_links:
                    try:
                        results = search_web(msg, max_results=2)
                    except Exception:
                        results = []
                    parts = []
                    if results:
                        for r in results[:2]:
                            t = r.get("title", "N/A")
                            u = r.get("href", "")
                            parts.append(f"{t} — {u}" if u else t)
                    if not parts:
                        try:
                            import re
                            target = None
                            m = re.search(r"find\s+@?([A-Za-z0-9_]+)\s+on\s+twitch", ml)
                            if not m:
                                m = re.search(r"@?([A-Za-z0-9_]+)\s+(?:on\s+)?twitch", ml)
                            if m:
                                target = m.group(1)
                            if target:
                                parts.append(f"{target} — https://www.twitch.tv/{target}")
                        except Exception:
                            pass
                    if parts:
                        link_suffix = " | ".join(parts)

                base_reply = _sanitize_reply_text(reply, _username_for_model(username))
                composed = base_reply if not link_suffix else f"{base_reply} — {link_suffix}"
                final = _prepare_msg(_prefix_for_llm_reply(username) + composed)
                self.send_message(final)
                try:
                    log_interaction(username, msg, composed if composed else reply)
                except Exception:
                    pass

        # viewer_arrived now handled via JOIN and gated by _arrived_users

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

        if cmd in {"pokecatch", "pokeshop"} and username.lower() != BOT_NICK.lower() and is_enabled("ignore_viewer_pokecatch"):
            return

        response = execute_command(cmd, username, role, args, ctx)

        if response:
            try:
                if cmd == "roulette" and ("BANG" in response or response.startswith("💥")):
                    try:
                        from MedlarTV.core.moderation import execute_timeout
                        execute_timeout(self.sock, CHANNEL, username, 30, "roulette")
                    except Exception:
                        pass
            except Exception:
                pass
            final = _prepare_msg(_role_prefix(username) + response)
            self.send_message(final)
            try:
                log_interaction(username, full, response)
            except Exception:
                pass
        else:
            log.debug(
                f"[DEBUG] Command fallback to generate_response(user={username}, msg={full})"
            )
            reply = generate_response(full, _username_for_model(username))
            log.debug(f"[DEBUG] generate_response() command output: {reply}")
            if reply:
                final = _prepare_msg(_prefix_for_llm_reply(username) + _sanitize_reply_text(reply, _username_for_model(username)))
                self.send_message(final)
                try:
                    log_interaction(username, full, reply)
                except Exception:
                    pass


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

    try:
        _arrived_users.clear()
        _last_audio_play.clear()
        log.info("[Listener] Session state cleared (arrivals, audio)")
    except Exception:
        pass

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

def trigger_event_for_testing(username: str) -> None:
    class Dummy:
        def send(self, b):
            print(b.decode())
    sock = Dummy()
    def send_msg(m):
        print(f"CHAT_SEND: {m}")
    _apply_event_rules("viewer_arrived", username, send_msg, sock)

_arrived_users: set[str] = set()
_audio_lock = threading.Lock()
_last_audio_play: dict[str, float] = {}

