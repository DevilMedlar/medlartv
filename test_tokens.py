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

# Load .env
load_dotenv()

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

print("\n--- Validating broadcaster token with Twitch ---")

try:
    response = requests.get(
        "https://id.twitch.tv/oauth2/validate",
        headers={"Authorization": f"OAuth {TWITCH_USER_TOKEN.replace('oauth:', '')}"},
        timeout=10,
    )

    print(f"Validation status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        login = data.get("login")
        scopes = data.get("scopes", [])

        print(f"Token user: {login}")
        print(f"Scopes: {scopes}")

        has_scope = "channel:manage:broadcast" in scopes
        print(f"Has channel:manage:broadcast: {has_scope}")

        if not has_scope:
            print("❌ TOKEN IS MISSING THE REQUIRED SCOPE! Generate a new one with that scope.")

    else:
        print("❌ Token validation failed:", response.text)

except Exception as e:
    print(f"❌ Error validating token: {e}")
