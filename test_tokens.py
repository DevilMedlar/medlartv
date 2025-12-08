"""
Token Debug Test (Refactored)
-----------------------------

Shows exactly which Twitch-related env vars are set and verifies
whether the broadcaster token contains the `channel:manage:broadcast` scope.

Aligned with your real .env layout.
"""

import os
import requests
from dotenv import load_dotenv
from pathlib import Path
import sys
import atexit

# Load .env
load_dotenv()

_log_path = Path("token_results.txt")
_log_file = _log_path.open("w", encoding="utf-8")

class _Tee:
    def __init__(self, *writers):
        self._writers = writers
    def write(self, s):
        for w in self._writers:
            w.write(s)
    def flush(self):
        for w in self._writers:
            try:
                w.flush()
            except Exception:
                pass

sys.stdout = _Tee(sys.stdout, _log_file)
atexit.register(_log_file.close)

print("=" * 60)
print("TOKEN DEBUG TEST")
print("=" * 60)

# ---------------------------------------------------------------------------
# ENVIRONMENT VALUES (masked)
# ---------------------------------------------------------------------------

medlar_token = os.getenv("MEDLARTV_TWITCH_TOKEN", "")
devil_token = os.getenv("DEVILMEDLAR_TWITCH_TOKEN", "")

client_id = os.getenv(
    "DEVILMEDLAR_TWITCH_CLIENT_ID",
    os.getenv("MEDLARTV_TWITCH_CLIENT_ID", "")
)

print(f"\nMEDLARTV_TWITCH_TOKEN: "
      f"{medlar_token[:20] + '...' if medlar_token else 'MISSING'}")

print(f"DEVILMEDLAR_TWITCH_TOKEN: "
      f"{devil_token[:20] + '...' if devil_token else 'MISSING'}")

print(f"DEVILMEDLAR_TWITCH_CLIENT_ID: "
      f"{client_id[:20] + '...' if client_id else 'MISSING'}")

# ---------------------------------------------------------------------------
# Determine which token stream_management will use
# ---------------------------------------------------------------------------

TWITCH_USER_TOKEN = devil_token or medlar_token

print(f"\nTWITCH_USER_TOKEN (broadcaster): "
      f"{TWITCH_USER_TOKEN[:20] + '...' if TWITCH_USER_TOKEN else 'MISSING'}")

print(f"Length: {len(TWITCH_USER_TOKEN) if TWITCH_USER_TOKEN else 0}")

if not TWITCH_USER_TOKEN:
    print("\n❌ No broadcaster token found. Set DEVILMEDLAR_TWITCH_TOKEN in .env.")
    raise SystemExit(1)

# ---------------------------------------------------------------------------
# Validate broadcaster token via Twitch
# ---------------------------------------------------------------------------

def validate_token(label: str, raw_token: str) -> None:
    print(f"\n--- Validating {label} with Twitch ---")
    if not raw_token:
        print("MISSING")
        return
    try:
        token = raw_token.replace("oauth:", "")
        response = requests.get(
            "https://id.twitch.tv/oauth2/validate",
            headers={"Authorization": f"OAuth {token}"},
            timeout=10,
        )
        print(f"Validation status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            login = data.get("login")
            scopes = data.get("scopes", [])
            print(f"Token user: {login}")
            print(f"Scopes: {scopes}")
            print(f"Has channel:manage:broadcast: {'channel:manage:broadcast' in scopes}")
            scopes_info = {
                "analytics:read:extensions": ("Analytics", "Read extensions analytics"),
                "analytics:read:games": ("Analytics", "Read games analytics"),
                "bits:read": ("Monetization", "Read Bits usage"),
                "channel:edit:commercial": ("Monetization", "Run commercials"),
                "channel:manage:ads": ("Monetization", "Manage ads"),
                "channel:read:ads": ("Monetization", "Read ads data"),
                "clips:edit": ("Content", "Create and edit clips"),
                "channel:manage:videos": ("Content", "Manage channel videos"),
                "chat:read": ("Chat", "Read chat"),
                "chat:edit": ("Chat", "Send chat messages"),
                "user:read:chat": ("Chat", "Read chat as user"),
                "user:write:chat": ("Chat", "Write chat as user"),
                "channel:moderate": ("Moderation", "Moderate channel"),
                "moderation:read": ("Moderation", "Read moderation data"),
                "moderator:manage:banned_users": ("Moderation", "Manage bans"),
                "moderator:manage:chat_messages": ("Moderation", "Manage chat messages"),
                "moderator:read:unban_requests": ("Moderation", "Read unban requests"),
                "moderator:manage:unban_requests": ("Moderation", "Manage unban requests"),
                "moderator:read:suspicious_users": ("Moderation", "Read suspicious users"),
                "moderator:manage:warnings": ("Moderation", "Manage warnings"),
                "moderator:manage:announcements": ("Moderation", "Manage announcements"),
                "moderator:read:followers": ("Moderation", "Read followers"),
                "moderator:read:chatters": ("Moderation", "Read chatters"),
                "moderator:read:shield_mode": ("Moderation", "Read Shield Mode"),
                "moderator:manage:shield_mode": ("Moderation", "Manage Shield Mode"),
                "moderator:read:blocked_terms": ("Moderation", "Read blocked terms"),
                "moderator:manage:blocked_terms": ("Moderation", "Manage blocked terms"),
                "moderator:read:chat_settings": ("Moderation", "Read chat settings"),
                "moderator:manage:chat_settings": ("Moderation", "Manage chat settings"),
                "moderator:manage:automod": ("Moderation", "Manage AutoMod"),
                "moderator:read:automod_settings": ("Moderation", "Read AutoMod settings"),
                "moderator:manage:automod_settings": ("Moderation", "Manage AutoMod settings"),
                "user:manage:chat_color": ("Chat", "Manage chat color"),
                "whispers:read": ("Whispers", "Read whispers"),
                "whispers:edit": ("Whispers", "Send whispers"),
                "user:manage:whispers": ("Whispers", "Manage whispers"),
                "channel:manage:broadcast": ("Channel", "Update stream title/category"),
                "channel:read:stream_key": ("Channel", "Read stream key"),
                "channel:manage:extensions": ("Channel", "Manage channel extensions"),
                "channel:manage:moderators": ("Channel", "Manage moderators"),
                "channel:read:vips": ("Channel", "Read VIPs"),
                "channel:manage:vips": ("Channel", "Manage VIPs"),
                "channel:manage:raids": ("Channel", "Manage raids"),
                "channel:read:charity": ("Channel", "Read charity campaigns"),
                "channel:read:guest_star": ("Guest Star", "Read Guest Star"),
                "channel:manage:guest_star": ("Guest Star", "Manage Guest Star"),
                "moderator:read:guest_star": ("Guest Star", "Read Guest Star moderator"),
                "moderator:manage:guest_star": ("Guest Star", "Manage Guest Star moderator"),
                "channel:manage:schedule": ("Channel", "Manage stream schedule"),
                "channel:read:goals": ("Channel", "Read channel goals"),
                "channel:read:hype_train": ("Channel", "Read Hype Train data"),
                "channel:read:redemptions": ("Channel Points", "Read channel point redemptions"),
                "channel:manage:redemptions": ("Channel Points", "Manage channel point rewards"),
                "channel:manage:polls": ("Engagement", "Manage polls"),
                "channel:read:polls": ("Engagement", "Read polls"),
                "channel:manage:predictions": ("Engagement", "Manage predictions"),
                "channel:read:predictions": ("Engagement", "Read predictions"),
                "user:edit": ("User", "Edit user profile"),
                "user:edit:broadcast": ("User", "Edit user broadcast settings"),
                "user:read:broadcast": ("User", "Read user broadcast settings"),
                "user:read:email": ("User", "Read user email"),
                "user:read:follows": ("User", "Read user follows"),
                "user:edit:follows": ("User", "Edit user follows"),
                "user:read:subscriptions": ("User", "Read user subscriptions"),
                "user:read:blocked_users": ("User", "Read blocked users"),
                "user:manage:blocked_users": ("User", "Manage blocked users"),
                "user:read:moderated_channels": ("User", "Read moderated channels"),
                "user:read:emotes": ("User", "Read user emotes"),
                "channel:read:subscriptions": ("Channel", "Read channel subscriptions"),
                "channel:read:editors": ("Channel", "Read channel editors"),
                "channel:bot": ("Bot", "Channel bot capability"),
                "user:bot": ("Bot", "User bot capability"),
            }
            if scopes:
                groups: dict[str, list[tuple[str, str]]] = {}
                for s in scopes:
                    cat, desc = scopes_info.get(s, ("Other", "(unknown scope)"))
                    groups.setdefault(cat, []).append((s, desc))
                print("Abilities:")
                for cat in sorted(groups.keys()):
                    print(f" {cat}:")
                    for s, desc in sorted(groups[cat], key=lambda x: x[0]):
                        print(f"  - {s}: {desc}")
            else:
                print("Abilities: none (no scopes)")
        else:
            print("❌ Token validation failed:", response.text)
    except Exception as e:
        print(f"❌ Error validating token: {e}")

if not (devil_token or medlar_token):
    print("\n❌ No tokens found. Set DEVILMEDLAR_TWITCH_TOKEN and/or MEDLARTV_TWITCH_TOKEN in .env.")
    raise SystemExit(1)

validate_token("DEVILMEDLAR_TWITCH_TOKEN", devil_token)
validate_token("MEDLARTV_TWITCH_TOKEN", medlar_token)
