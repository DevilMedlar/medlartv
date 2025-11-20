"""
Direct Twitch API Test (Final Professional Version)
---------------------------------------------------

This utility script performs two independent checks:

1. **APP TOKEN TEST**
   Uses:
      - APP_TWITCH_CLIENT_ID
      - APP_SECRET_ID
   Purpose:
      - Verifies your Twitch Developer Application credentials
      - Retrieves an app access token
      - Fetches the broadcaster ID from Twitch API

2. **BROADCASTER TOKEN TEST**
   Uses:
      - DEVILMEDLAR_TWITCH_CLIENT_ID
      - DEVILMEDLAR_TWITCH_TOKEN
   Purpose:
      - Verifies your user OAuth token (broadcaster token)
      - Validates token scopes
      - Attempts to update the stream title

Run with:
    python test_api_direct.py
"""

import os
import requests
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# ---------------------------------------------------------------------------
# APP Credentials (Client Credentials Flow)
# ---------------------------------------------------------------------------
APP_CLIENT_ID = os.getenv("APP_TWITCH_CLIENT_ID", "")
APP_SECRET = os.getenv("APP_SECRET_ID", "")

# ---------------------------------------------------------------------------
# Broadcaster Credentials (User OAuth Token)
# ---------------------------------------------------------------------------
BROADCASTER_CLIENT_ID = os.getenv("DEVILMEDLAR_TWITCH_CLIENT_ID", "")
BROADCASTER_TOKEN = os.getenv("DEVILMEDLAR_TWITCH_TOKEN", "").replace("oauth:", "")
CHANNEL = os.getenv("TWITCH_CHANNEL", "").lstrip("#")

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

print("=" * 60)
print("DIRECT TWITCH API TEST – FINAL PROFESSIONAL VERSION")
print("=" * 60)

print("\n🔹 APP Client ID:", APP_CLIENT_ID[:20] + "...")
print("🔹 Broadcaster Client ID:", BROADCASTER_CLIENT_ID[:20] + "...")
print("🔹 Broadcaster Token:", BROADCASTER_TOKEN[:20] + "...")
print("🔹 Channel:", CHANNEL or "MISSING")

# Validation
missing = []
if not APP_CLIENT_ID: missing.append("APP_TWITCH_CLIENT_ID")
if not APP_SECRET: missing.append("APP_SECRET_ID")
if not BROADCASTER_CLIENT_ID: missing.append("DEVILMEDLAR_TWITCH_CLIENT_ID")
if not BROADCASTER_TOKEN: missing.append("DEVILMEDLAR_TWITCH_TOKEN")
if not CHANNEL: missing.append("TWITCH_CHANNEL")

if missing:
    print("\n❌ Missing required environment variables:")
    for m in missing:
        print("   -", m)
    raise SystemExit(1)

# ---------------------------------------------------------------------------
# STEP 1 — APP TOKEN & BROADCASTER ID
# ---------------------------------------------------------------------------

print("\n" + "-"*60)
print("STEP 1 — Fetching App Token & Broadcaster ID")
print("-"*60)

app_token_response = requests.post(
    "https://id.twitch.tv/oauth2/token",
    params={
        "client_id": APP_CLIENT_ID,
        "client_secret": APP_SECRET,
        "grant_type": "client_credentials",
    },
    timeout=10,
)

print(f"\nApp Token Status: {app_token_response.status_code}")

if app_token_response.status_code != 200:
    print("❌ App token error:", app_token_response.text)
    raise SystemExit(1)

app_token = app_token_response.json()["access_token"]

# Resolve broadcaster login -> broadcaster ID
user_response = requests.get(
    "https://api.twitch.tv/helix/users",
    headers={
        "Client-ID": APP_CLIENT_ID,
        "Authorization": f"Bearer {app_token}",
    },
    params={"login": CHANNEL},
    timeout=10,
)

if user_response.status_code != 200:
    print("❌ Failed to fetch broadcaster ID:", user_response.text)
    raise SystemExit(1)

user_data = user_response.json().get("data", [])
if not user_data:
    print("❌ No user found for:", CHANNEL)
    raise SystemExit(1)

broadcaster_id = user_data[0]["id"]
print(f"Broadcaster ID: {broadcaster_id}")

# ---------------------------------------------------------------------------
# STEP 2 — TITLE UPDATE VIA BROADCASTER TOKEN
# ---------------------------------------------------------------------------

print("\n" + "-"*60)
print("STEP 2 — Updating Stream Title (Broadcaster Token)")
print("-"*60)

headers = {
    "Client-ID": BROADCASTER_CLIENT_ID,  # IMPORTANT FIX
    "Authorization": f"Bearer {BROADCASTER_TOKEN}",
    "Content-Type": "application/json",
}

print("\nHeaders being sent:")
for k, v in headers.items():
    if k == "Authorization":
        print(f"  {k}: Bearer {BROADCASTER_TOKEN[:20]}...")
    else:
        print(f"  {k}: {v}")

response = requests.patch(
    "https://api.twitch.tv/helix/channels",
    headers=headers,
    params={"broadcaster_id": broadcaster_id},
    json={"title": "API Test via Python Script – Final Version"},
    timeout=10,
)

print(f"\nResponse Status: {response.status_code}")
print("Response Body:", response.text)

if response.status_code == 204:
    print("\n✅ SUCCESS! Title updated!")

elif response.status_code == 401:
    print("\n❌ Unauthorized — Validating token...")
    val = requests.get(
        "https://id.twitch.tv/oauth2/validate",
        headers={"Authorization": f"OAuth {BROADCASTER_TOKEN}"},
        timeout=10,
    )
    print("\nValidation Response:", val.status_code, val.text)

else:
    print("\n❌ Unexpected error:", response.status_code)
    try:
        print("JSON:", response.json())
    except:
        pass
