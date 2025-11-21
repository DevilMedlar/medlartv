"""
MedlarTV Stream Management (fixed tokens & headers)
---------------------------------------------------
Uses:
  - APP_TWITCH_CLIENT_ID + APP_SECRET_ID for APP access token
  - DEVILMEDLAR_TWITCH_CLIENT_ID + DEVILMEDLAR_TWITCH_TOKEN for
    broadcaster actions (title/category updates)
Matches the behaviour of test_api_direct.py you ran.
"""

from __future__ import annotations

import os
import time
import logging
from typing import Optional, Dict, Any

import requests

log = logging.getLogger("stream")

print("[DEBUG stream_management] Loaded stream_management.py")

TWITCH_AUTH_BASE = "https://id.twitch.tv/oauth2"
TWITCH_API_BASE = "https://api.twitch.tv/helix"

# --- ENV / CONFIG -----------------------------------------------------------

APP_CLIENT_ID = os.getenv("APP_TWITCH_CLIENT_ID", "").strip()
APP_CLIENT_SECRET = os.getenv("APP_SECRET_ID", "").strip()

BROADCASTER_CLIENT_ID = os.getenv("DEVILMEDLAR_TWITCH_CLIENT_ID", "").strip()
BROADCASTER_TOKEN_RAW = os.getenv("DEVILMEDLAR_TWITCH_TOKEN", "").strip()

print(f"[DEBUG stream_management] ENV loaded: "
      f"APP_CLIENT_ID_set={bool(APP_CLIENT_ID)} "
      f"APP_CLIENT_SECRET_set={bool(APP_CLIENT_SECRET)} "
      f"BROADCASTER_CLIENT_ID_set={bool(BROADCASTER_CLIENT_ID)} "
      f"BROADCASTER_TOKEN_RAW_set={bool(BROADCASTER_TOKEN_RAW)}")

# Strip leading "oauth:" if present
if BROADCASTER_TOKEN_RAW.startswith("oauth:"):
    BROADCASTER_TOKEN = BROADCASTER_TOKEN_RAW.split("oauth:", 1)[1]
    print("[DEBUG stream_management] Stripped 'oauth:' prefix from BROADCASTER_TOKEN_RAW")
else:
    BROADCASTER_TOKEN = BROADCASTER_TOKEN_RAW
    print("[DEBUG stream_management] BROADCASTER_TOKEN_RAW used as-is (no 'oauth:' prefix)")

CHANNEL_NAME = os.getenv("TWITCH_CHANNEL", "#devilmedlar").lstrip("#")
print(f"[DEBUG stream_management] CHANNEL_NAME resolved to='{CHANNEL_NAME}'")

# --- INTERNAL STATE ---------------------------------------------------------

_app_token: Optional[str] = None
_app_token_expiry: float = 0.0
_broadcaster_id: Optional[str] = None


# --- HELPERS ----------------------------------------------------------------

def _ensure_app_token() -> Optional[str]:
    """
    Get (and cache) an APP access token using client_credentials.

    Uses APP_TWITCH_CLIENT_ID + APP_SECRET_ID exactly like test_api_direct.py.
    """
    print("[DEBUG stream_management] _ensure_app_token() called")
    global _app_token, _app_token_expiry

    now = time.time()
    print(f"[DEBUG stream_management] _app_token_set={bool(_app_token)} "
          f"now={now} expiry={_app_token_expiry}")

    if _app_token and now < _app_token_expiry - 60:
        print("[DEBUG stream_management] Using cached APP token")
        return _app_token

    if not APP_CLIENT_ID or not APP_CLIENT_SECRET:
        print("[DEBUG stream_management] Missing APP_CLIENT_ID or APP_CLIENT_SECRET")
        log.error("[Stream] Missing APP_TWITCH_CLIENT_ID or APP_SECRET_ID in environment")
        return None

    data = {
        "client_id": APP_CLIENT_ID,
        "client_secret": APP_CLIENT_SECRET,
        "grant_type": "client_credentials",
    }

    print(f"[DEBUG stream_management] Requesting new APP token at {TWITCH_AUTH_BASE}/token")
    try:
        resp = requests.post(f"{TWITCH_AUTH_BASE}/token", data=data, timeout=15)
    except Exception as e:  # pragma: no cover
        print(f"[DEBUG stream_management] Exception while requesting app token: {e}")
        log.error(f"[Stream] Error requesting app token: {e}")
        return None

    print(f"[DEBUG stream_management] App token response status={resp.status_code}")
    if resp.status_code != 200:
        print(f"[DEBUG stream_management] App token failure body={resp.text[:500]}")
        log.error(f"[Stream] App token failed: {resp.status_code} - {resp.text}")
        return None

    body = resp.json()
    _app_token = body.get("access_token")
    expires_in = int(body.get("expires_in", 3600))
    _app_token_expiry = now + expires_in

    print(f"[DEBUG stream_management] New APP token acquired: token_set={bool(_app_token)} "
          f"expires_in={expires_in}s new_expiry={_app_token_expiry}")
    log.info("[Stream] Got new APP access token")
    return _app_token


def get_access_token() -> Optional[str]:
    """
    Public helper used by !status.
    Returns current APP token or None.
    """
    print("[DEBUG stream_management] get_access_token() called")
    token = _ensure_app_token()
    print(f"[DEBUG stream_management] get_access_token() returning token_set={bool(token)}")
    return token


def _app_headers(token: Optional[str] = None) -> Dict[str, str]:
    print("[DEBUG stream_management] _app_headers() called")
    tok = token or _ensure_app_token()
    print(f"[DEBUG stream_management] _app_headers() tok_set={bool(tok)}")
    if not tok:
        return {}
    headers = {
        "Client-ID": APP_CLIENT_ID,
        "Authorization": f"Bearer {tok}",
    }
    print(f"[DEBUG stream_management] _app_headers() built headers with Client-ID_set={bool(APP_CLIENT_ID)}")
    return headers


def _broadcaster_headers() -> Dict[str, str]:
    print("[DEBUG stream_management] _broadcaster_headers() called")
    if not BROADCASTER_CLIENT_ID or not BROADCASTER_TOKEN:
        print("[DEBUG stream_management] Missing BROADCASTER_CLIENT_ID or BROADCASTER_TOKEN")
        return {}
    headers = {
        "Client-ID": BROADCASTER_CLIENT_ID,
        "Authorization": f"Bearer {BROADCASTER_TOKEN}",
        "Content-Type": "application/json",
    }
    print(f"[DEBUG stream_management] _broadcaster_headers() built headers with "
          f"Client-ID_set={bool(BROADCASTER_CLIENT_ID)} token_set={bool(BROADCASTER_TOKEN)}")
    return headers


# --- BROADCASTER / CHANNEL LOOKUPS -----------------------------------------

def get_broadcaster_id() -> Optional[str]:
    """Get numeric broadcaster_id for CHANNEL_NAME via APP token."""
    print("[DEBUG stream_management] get_broadcaster_id() called")
    global _broadcaster_id

    if _broadcaster_id:
        print(f"[DEBUG stream_management] Using cached broadcaster_id={_broadcaster_id}")
        return _broadcaster_id

    token = _ensure_app_token()
    print(f"[DEBUG stream_management] get_broadcaster_id() token_set={bool(token)}")
    if not token:
        return None

    headers = _app_headers(token)
    params = {"login": CHANNEL_NAME}
    print(f"[DEBUG stream_management] Requesting /users for login='{CHANNEL_NAME}'")

    try:
        resp = requests.get(f"{TWITCH_API_BASE}/users", headers=headers, params=params, timeout=15)
    except Exception as e:  # pragma: no cover
        print(f"[DEBUG stream_management] Exception fetching broadcaster id: {e}")
        log.error(f"[Stream] Error fetching broadcaster id: {e}")
        return None

    print(f"[DEBUG stream_management] /users status={resp.status_code}")
    if resp.status_code != 200:
        print(f"[DEBUG stream_management] /users error body={resp.text[:500]}")
        log.error(f"[Stream] Failed to get broadcaster id: {resp.status_code} - {resp.text}")
        return None

    data = resp.json().get("data", [])
    print(f"[DEBUG stream_management] /users returned {len(data)} records")
    if not data:
        log.error("[Stream] No user data returned for channel '%s'", CHANNEL_NAME)
        return None

    _broadcaster_id = data[0]["id"]
    print(f"[DEBUG stream_management] broadcaster_id resolved to={_broadcaster_id}")
    log.info("[Stream] Broadcaster id resolved: %s", _broadcaster_id)
    return _broadcaster_id


def get_channel_info() -> Optional[Dict[str, Any]]:
    """Return /channels info for the broadcaster (title, game, tags, etc.)."""
    print("[DEBUG stream_management] get_channel_info() called")
    token = _ensure_app_token()
    bid = get_broadcaster_id()
    print(f"[DEBUG stream_management] get_channel_info() token_set={bool(token)} bid={bid}")
    if not (token and bid):
        return None

    headers = _app_headers(token)
    params = {"broadcaster_id": bid}
    print(f"[DEBUG stream_management] Requesting /channels for broadcaster_id={bid}")

    try:
        resp = requests.get(f"{TWITCH_API_BASE}/channels", headers=headers, params=params, timeout=15)
    except Exception as e:  # pragma: no cover
        print(f"[DEBUG stream_management] Exception fetching channel info: {e}")
        log.error(f"[Stream] Error fetching channel info: {e}")
        return None

    print(f"[DEBUG stream_management] /channels status={resp.status_code}")
    if resp.status_code != 200:
        print(f"[DEBUG stream_management] /channels error body={resp.text[:500]}")
        log.error(f"[Stream] Failed to get channel info: {resp.status_code} - {resp.text}")
        return None

    items = resp.json().get("data", [])
    print(f"[DEBUG stream_management] /channels returned {len(items)} records")
    return items[0] if items else None


def get_stream_info() -> Optional[Dict[str, Any]]:
    """Return /streams info (live status, viewer count, etc.)."""
    print("[DEBUG stream_management] get_stream_info() called")
    token = _ensure_app_token()
    bid = get_broadcaster_id()
    print(f"[DEBUG stream_management] get_stream_info() token_set={bool(token)} bid={bid}")
    if not (token and bid):
        return None

    headers = _app_headers(token)
    params = {"user_id": bid}
    print(f"[DEBUG stream_management] Requesting /streams for user_id={bid}")

    try:
        resp = requests.get(f"{TWITCH_API_BASE}/streams", headers=headers, params=params, timeout=15)
    except Exception as e:  # pragma: no cover
        print(f"[DEBUG stream_management] Exception fetching stream info: {e}")
        log.error(f"[Stream] Error fetching stream info: {e}")
        return None

    print(f"[DEBUG stream_management] /streams status={resp.status_code}")
    if resp.status_code != 200:
        print(f"[DEBUG stream_management] /streams error body={resp.text[:500]}")
        log.error(f"[Stream] Failed to get stream info: {resp.status_code} - {resp.text}")
        return None

    items = resp.json().get("data", [])
    print(f"[DEBUG stream_management] /streams returned {len(items)} records")
    return items[0] if items else None

# --- USER LOOKUP & SHOUTOUT -------------------------------------------------

def get_user_id(login: str) -> Optional[str]:
    """Resolve a user's numeric id by login using APP token."""
    print(f"[DEBUG stream_management] get_user_id() called login={login!r}")
    token = _ensure_app_token()
    print(f"[DEBUG stream_management] get_user_id() token_set={bool(token)}")
    if not token:
        return None
    headers = _app_headers(token)
    params = {"login": login}
    print(f"[DEBUG stream_management] Requesting /users for login={login!r}")
    try:
        resp = requests.get(f"{TWITCH_API_BASE}/users", headers=headers, params=params, timeout=15)
    except Exception as e:
        print(f"[DEBUG stream_management] Exception fetching user id: {e}")
        log.error(f"[Stream] Error fetching user id: {e}")
        return None
    print(f"[DEBUG stream_management] /users status={resp.status_code}")
    if resp.status_code != 200:
        print(f"[DEBUG stream_management] /users error body={resp.text[:500]}")
        log.error(f"[Stream] Failed to get user id: {resp.status_code} - {resp.text}")
        return None
    data = resp.json().get("data", [])
    print(f"[DEBUG stream_management] /users returned {len(data)} records")
    return (data[0]["id"] if data else None)

def send_shoutout(target_login: str) -> bool:
    """Send a Helix Shoutout using broadcaster token and required scope."""
    try:
        log.info("[Stream] send_shoutout target_login=%s", target_login)
        from_id = get_broadcaster_id()
        to_id = get_user_id(target_login)
        print(f"[DEBUG stream_management] send_shoutout() from_id={from_id} to_id={to_id}")
        if not (from_id and to_id):
            log.error("[Stream] Missing ids for shoutout: from_id=%s to_id=%s", from_id, to_id)
            return False
        headers = _broadcaster_headers()
        print(f"[DEBUG stream_management] send_shoutout() headers_set={bool(headers)}")
        if not headers:
            log.error("[Stream] Missing broadcaster headers (client id/token)")
            return False
        params = {
            "from_broadcaster_id": from_id,
            "to_broadcaster_id": to_id,
            "moderator_id": from_id,
        }
        print(f"[DEBUG stream_management] POST /chat/shoutouts params={params}")
        try:
            resp = requests.post(f"{TWITCH_API_BASE}/chat/shoutouts", headers=headers, params=params, timeout=15)
        except Exception as e:
            print(f"[DEBUG stream_management] Exception sending shoutout: {e}")
            log.error("[Stream] Error sending shoutout: %s", e)
            return False
        print(f"[DEBUG stream_management] send_shoutout() status={resp.status_code}")
        if 200 <= resp.status_code < 300:
            log.info("[Stream] Helix shoutout success to=%s status=%s", target_login, resp.status_code)
            return True
        print(f"[DEBUG stream_management] send_shoutout() error body={resp.text[:500]}")
        log.error("[Stream] Helix shoutout failed status=%s body=%s", resp.status_code, resp.text[:500])
        return False
    except Exception:
        return False


def search_game(game_name: str) -> Optional[str]:
    """Search game/category by name and return its game_id."""
    print(f"[DEBUG stream_management] search_game() called with game_name={game_name!r}")
    token = _ensure_app_token()
    print(f"[DEBUG stream_management] search_game() token_set={bool(token)}")
    if not token:
        return None

    headers = _app_headers(token)
    params = {"query": game_name, "first": 1}
    print(f"[DEBUG stream_management] Requesting /search/categories query={game_name!r}")

    try:
        resp = requests.get(f"{TWITCH_API_BASE}/search/categories", headers=headers, params=params, timeout=15)
    except Exception as e:  # pragma: no cover
        print(f"[DEBUG stream_management] Exception searching game: {e}")
        log.error(f"[Stream] Error searching game: {e}")
        return None

    print(f"[DEBUG stream_management] /search/categories status={resp.status_code}")
    if resp.status_code != 200:
        print(f"[DEBUG stream_management] /search/categories error body={resp.text[:500]}")
        log.error(f"[Stream] Failed to search game: {resp.status_code} - {resp.text}")
        return None

    data = resp.json().get("data", [])
    print(f"[DEBUG stream_management] /search/categories returned {len(data)} records")
    if not data:
        return None

    game_id = data[0]["id"]
    print(f"[DEBUG stream_management] search_game() resolved game_id={game_id}")
    return game_id


def get_top_games(limit: int = 5) -> Optional[list[Dict[str, Any]]]:
    """Optional helper: /games/top"""
    print(f"[DEBUG stream_management] get_top_games() called limit={limit}")
    token = _ensure_app_token()
    print(f"[DEBUG stream_management] get_top_games() token_set={bool(token)}")
    if not token:
        return None

    headers = _app_headers(token)
    params = {"first": limit}
    print(f"[DEBUG stream_management] Requesting /games/top first={limit}")

    try:
        resp = requests.get(f"{TWITCH_API_BASE}/games/top", headers=headers, params=params, timeout=15)
    except Exception as e:  # pragma: no cover
        print(f"[DEBUG stream_management] Exception fetching top games: {e}")
        log.error(f"[Stream] Error fetching top games: {e}")
        return None

    print(f"[DEBUG stream_management] /games/top status={resp.status_code}")
    if resp.status_code != 200:
        print(f"[DEBUG stream_management] /games/top error body={resp.text[:500]}")
        log.error(f"[Stream] Failed to get top games: {resp.status_code} - {resp.text}")
        return None

    data = resp.json().get("data", [])
    print(f"[DEBUG stream_management] /games/top returned {len(data)} records")
    return data


# --- MUTATING OPERATIONS (TITLE / CATEGORY) ---------------------------------

def update_stream_title(new_title: str) -> bool:
    """
    Update stream title using BROADCASTER TOKEN.

    This mirrors your direct test:
      Client-ID: DEVILMEDLAR_TWITCH_CLIENT_ID
      Authorization: Bearer DEVILMEDLAR_TWITCH_TOKEN (no 'oauth:')
    """
    print(f"[DEBUG stream_management] update_stream_title() called new_title={new_title!r}")
    bid = get_broadcaster_id()
    print(f"[DEBUG stream_management] update_stream_title() broadcaster_id={bid}")
    if not bid:
        log.error("[Stream] Cannot update title: missing broadcaster id")
        return False

    headers = _broadcaster_headers()
    print(f"[DEBUG stream_management] update_stream_title() headers_set={bool(headers)}")
    if not headers:
        log.error("[Stream] Cannot update title: broadcaster headers missing")
        return False

    params = {"broadcaster_id": bid}
    json_body = {"title": new_title}
    print(f"[DEBUG stream_management] PATCH /channels (title) params={params} body={json_body}")

    try:
        resp = requests.patch(
            f"{TWITCH_API_BASE}/channels",
            headers=headers,
            params=params,
            json=json_body,
            timeout=15,
        )
    except Exception as e:  # pragma: no cover
        print(f"[DEBUG stream_management] Exception updating title: {e}")
        log.error(f"[Stream] Error updating title: {e}")
        return False

    print(f"[DEBUG stream_management] update_stream_title() status={resp.status_code}")
    if resp.status_code in (204, 200):
        log.info("[Stream] ✅ Title updated to: %s", new_title)
        print("[DEBUG stream_management] update_stream_title() SUCCESS")
        return True

    print(f"[DEBUG stream_management] update_stream_title() error body={resp.text[:500]}")
    log.error(f"[Stream] ❌ Failed to update title: {resp.status_code} - {resp.text}")
    return False


def update_stream_category(game_name: str) -> bool:
    """Update stream category/game by name."""
    print(f"[DEBUG stream_management] update_stream_category() called game_name={game_name!r}")
    bid = get_broadcaster_id()
    print(f"[DEBUG stream_management] update_stream_category() broadcaster_id={bid}")
    if not bid:
        log.error("[Stream] Cannot update category: missing broadcaster id")
        return False

    game_id = search_game(game_name)
    print(f"[DEBUG stream_management] update_stream_category() game_id={game_id}")
    if not game_id:
        log.error("[Stream] Could not find game/category: %s", game_name)
        return False

    headers = _broadcaster_headers()
    print(f"[DEBUG stream_management] update_stream_category() headers_set={bool(headers)}")
    if not headers:
        log.error("[Stream] Cannot update category: broadcaster headers missing")
        return False

    params = {"broadcaster_id": bid}
    json_body = {"game_id": game_id}
    print(f"[DEBUG stream_management] PATCH /channels (category) params={params} body={json_body}")

    try:
        resp = requests.patch(
            f"{TWITCH_API_BASE}/channels",
            headers=headers,
            params=params,
            json=json_body,
            timeout=15,
        )
    except Exception as e:  # pragma: no cover
        print(f"[DEBUG stream_management] Exception updating category: {e}")
        log.error(f"[Stream] Error updating category: {e}")
        return False

    print(f"[DEBUG stream_management] update_stream_category() status={resp.status_code}")
    if resp.status_code in (204, 200):
        log.info("[Stream] ✅ Category updated to: %s", game_name)
        print("[DEBUG stream_management] update_stream_category() SUCCESS")
        return True

    print(f"[DEBUG stream_management] update_stream_category() error body={resp.text[:500]}")
    log.error(f"[Stream] ❌ Failed to update category: {resp.status_code} - {resp.text}")
    return False


# --- FORMATTING & VALIDATION HELPERS ----------------------------------------

def format_stream_info(info: Optional[Dict[str, Any]]) -> str:
    """Nicely format stream/channel info for chat."""
    print(f"[DEBUG stream_management] format_stream_info() called info_is_none={info is None}")
    if not info:
        return "Could not retrieve stream info."

    title = info.get("title") or info.get("game_name", "Unknown")
    game = info.get("game_name", "Unknown")
    lang = info.get("broadcaster_language", "??").upper()

    formatted = f"📺 Title: {title} | 🎮 Game: {game} | 🌐 Lang: {lang}"
    print(f"[DEBUG stream_management] format_stream_info() -> {formatted!r}")
    return formatted


def verify_twitch_tokens() -> bool:
    """
    Called at startup: make sure broadcaster token is valid and has the right scopes,
    and that we can resolve broadcaster id with APP credentials.
    """
    print("[DEBUG stream_management] verify_twitch_tokens() called")
    ok = True

    if not BROADCASTER_TOKEN:
        print("[DEBUG stream_management] BROADCASTER_TOKEN missing")
        log.error("[Stream] Broadcaster token is missing")
        return False

    # Validate broadcaster token with Twitch
    try:
        headers = {"Authorization": f"OAuth {BROADCASTER_TOKEN}"}
        print(f"[DEBUG stream_management] Validating broadcaster token at {TWITCH_AUTH_BASE}/validate")
        resp = requests.get(f"{TWITCH_AUTH_BASE}/validate", headers=headers, timeout=15)
    except Exception as e:  # pragma: no cover
        print(f"[DEBUG stream_management] Exception validating broadcaster token: {e}")
        log.error(f"[Stream] Error validating broadcaster token: {e}")
        return False

    print(f"[DEBUG stream_management] /validate status={resp.status_code}")
    if resp.status_code != 200:
        print(f"[DEBUG stream_management] /validate error body={resp.text[:500]}")
        log.error(f"[Stream] Broadcaster token validation failed: {resp.status_code} - {resp.text}")
        ok = False
    else:
        data = resp.json()
        scopes = data.get("scopes", [])
        print(f"[DEBUG stream_management] /validate scopes={scopes}")
        if "channel:manage:broadcast" not in scopes:
            print("[DEBUG stream_management] Missing 'channel:manage:broadcast' scope")
            log.error("[Stream] Broadcaster token is missing 'channel:manage:broadcast' scope")
            ok = False

    # Ensure we can fetch broadcaster id using APP token
    bid = get_broadcaster_id()
    print(f"[DEBUG stream_management] verify_twitch_tokens() broadcaster_id={bid}")
    if not bid:
        ok = False

    if ok:
        log.info("[Stream] ✅ Twitch tokens verified")
        print("[DEBUG stream_management] verify_twitch_tokens() -> True")
    else:
        log.error("[Stream] ❌ Twitch token verification FAILED")
        print("[DEBUG stream_management] verify_twitch_tokens() -> False")

    return ok
