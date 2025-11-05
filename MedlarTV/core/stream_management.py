"""
MedlarTV Stream Management Module
Twitch API integration for changing title, category, reading stream info, etc.
"""

import os
import requests
from typing import Optional, Dict, List
from datetime import datetime, timedelta

# Twitch API credentials
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID", "")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET", "")
TWITCH_CHANNEL = os.getenv("TWITCH_CHANNEL", "").lstrip("#")

# API endpoints
TWITCH_API_BASE = "https://api.twitch.tv/helix"
TWITCH_AUTH_URL = "https://id.twitch.tv/oauth2/token"

# Cache
_access_token = None
_token_expires_at = None
_broadcaster_id = None


def get_access_token() -> Optional[str]:
    """Get or refresh OAuth access token for Twitch API"""
    global _access_token, _token_expires_at
    
    # Return cached token if still valid
    if _access_token and _token_expires_at and datetime.now() < _token_expires_at:
        return _access_token
    
    if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
        print("[Stream] Missing Twitch API credentials in .env")
        return None
    
    try:
        response = requests.post(TWITCH_AUTH_URL, params={
            "client_id": TWITCH_CLIENT_ID,
            "client_secret": TWITCH_CLIENT_SECRET,
            "grant_type": "client_credentials"
        })
        
        if response.status_code == 200:
            data = response.json()
            _access_token = data["access_token"]
            expires_in = data["expires_in"]
            _token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)  # 5 min buffer
            print("[Stream] Got new access token")
            return _access_token
        else:
            print(f"[Stream] Failed to get access token: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"[Stream] Error getting access token: {e}")
        return None


def get_broadcaster_id() -> Optional[str]:
    """Get broadcaster ID for the configured channel"""
    global _broadcaster_id
    
    if _broadcaster_id:
        return _broadcaster_id
    
    token = get_access_token()
    if not token:
        return None
    
    try:
        headers = {
            "Client-ID": TWITCH_CLIENT_ID,
            "Authorization": f"Bearer {token}"
        }
        
        response = requests.get(
            f"{TWITCH_API_BASE}/users",
            headers=headers,
            params={"login": TWITCH_CHANNEL}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data["data"]:
                _broadcaster_id = data["data"][0]["id"]
                print(f"[Stream] Got broadcaster ID: {_broadcaster_id}")
                return _broadcaster_id
        
        print(f"[Stream] Failed to get broadcaster ID: {response.status_code}")
        return None
        
    except Exception as e:
        print(f"[Stream] Error getting broadcaster ID: {e}")
        return None


def get_stream_info() -> Optional[Dict]:
    """
    Get current stream information (title, category, viewer count, etc.)
    
    Returns:
        Dict with stream info or None if offline/error
    """
    token = get_access_token()
    broadcaster_id = get_broadcaster_id()
    
    if not token or not broadcaster_id:
        return None
    
    try:
        headers = {
            "Client-ID": TWITCH_CLIENT_ID,
            "Authorization": f"Bearer {token}"
        }
        
        response = requests.get(
            f"{TWITCH_API_BASE}/streams",
            headers=headers,
            params={"user_id": broadcaster_id}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data["data"]:
                stream = data["data"][0]
                return {
                    "is_live": True,
                    "title": stream["title"],
                    "game_name": stream["game_name"],
                    "game_id": stream["game_id"],
                    "viewer_count": stream["viewer_count"],
                    "started_at": stream["started_at"],
                    "language": stream["language"],
                    "thumbnail_url": stream["thumbnail_url"]
                }
            else:
                return {"is_live": False}
        
        print(f"[Stream] Failed to get stream info: {response.status_code}")
        return None
        
    except Exception as e:
        print(f"[Stream] Error getting stream info: {e}")
        return None


def get_channel_info() -> Optional[Dict]:
    """
    Get channel information (always available, even when offline)
    
    Returns:
        Dict with channel info
    """
    token = get_access_token()
    broadcaster_id = get_broadcaster_id()
    
    if not token or not broadcaster_id:
        return None
    
    try:
        headers = {
            "Client-ID": TWITCH_CLIENT_ID,
            "Authorization": f"Bearer {token}"
        }
        
        response = requests.get(
            f"{TWITCH_API_BASE}/channels",
            headers=headers,
            params={"broadcaster_id": broadcaster_id}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data["data"]:
                channel = data["data"][0]
                return {
                    "broadcaster_name": channel["broadcaster_name"],
                    "broadcaster_language": channel["broadcaster_language"],
                    "game_name": channel["game_name"],
                    "game_id": channel["game_id"],
                    "title": channel["title"],
                    "delay": channel.get("delay", 0)
                }
        
        print(f"[Stream] Failed to get channel info: {response.status_code}")
        return None
        
    except Exception as e:
        print(f"[Stream] Error getting channel info: {e}")
        return None


def update_stream_title(new_title: str) -> bool:
    """
    Update the stream title
    
    Args:
        new_title: New stream title (max 140 characters)
    
    Returns:
        True if successful
    """
    token = get_access_token()
    broadcaster_id = get_broadcaster_id()
    
    if not token or not broadcaster_id:
        return False
    
    # Truncate title if too long
    if len(new_title) > 140:
        new_title = new_title[:137] + "..."
    
    try:
        headers = {
            "Client-ID": TWITCH_CLIENT_ID,
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        response = requests.patch(
            f"{TWITCH_API_BASE}/channels",
            headers=headers,
            params={"broadcaster_id": broadcaster_id},
            json={"title": new_title}
        )
        
        if response.status_code == 204:
            print(f"[Stream] Updated title to: {new_title}")
            return True
        
        print(f"[Stream] Failed to update title: {response.status_code}")
        return False
        
    except Exception as e:
        print(f"[Stream] Error updating title: {e}")
        return False


def update_stream_category(game_name: str) -> bool:
    """
    Update the stream category/game
    
    Args:
        game_name: Name of the game/category
    
    Returns:
        True if successful
    """
    token = get_access_token()
    broadcaster_id = get_broadcaster_id()
    
    if not token or not broadcaster_id:
        return False
    
    # First, get the game ID
    game_id = search_game(game_name)
    if not game_id:
        print(f"[Stream] Game not found: {game_name}")
        return False
    
    try:
        headers = {
            "Client-ID": TWITCH_CLIENT_ID,
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        response = requests.patch(
            f"{TWITCH_API_BASE}/channels",
            headers=headers,
            params={"broadcaster_id": broadcaster_id},
            json={"game_id": game_id}
        )
        
        if response.status_code == 204:
            print(f"[Stream] Updated category to: {game_name}")
            return True
        
        print(f"[Stream] Failed to update category: {response.status_code}")
        return False
        
    except Exception as e:
        print(f"[Stream] Error updating category: {e}")
        return False


def search_game(game_name: str) -> Optional[str]:
    """
    Search for a game by name and return its ID
    
    Args:
        game_name: Name of the game to search
    
    Returns:
        Game ID or None
    """
    token = get_access_token()
    if not token:
        return None
    
    try:
        headers = {
            "Client-ID": TWITCH_CLIENT_ID,
            "Authorization": f"Bearer {token}"
        }
        
        response = requests.get(
            f"{TWITCH_API_BASE}/games",
            headers=headers,
            params={"name": game_name}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data["data"]:
                return data["data"][0]["id"]
        
        return None
        
    except Exception as e:
        print(f"[Stream] Error searching game: {e}")
        return None


def get_top_games(limit: int = 10) -> List[Dict]:
    """Get list of top games on Twitch"""
    token = get_access_token()
    if not token:
        return []
    
    try:
        headers = {
            "Client-ID": TWITCH_CLIENT_ID,
            "Authorization": f"Bearer {token}"
        }
        
        response = requests.get(
            f"{TWITCH_API_BASE}/games/top",
            headers=headers,
            params={"first": limit}
        )
        
        if response.status_code == 200:
            data = response.json()
            return [
                {
                    "name": game["name"],
                    "id": game["id"]
                }
                for game in data["data"]
            ]
        
        return []
        
    except Exception as e:
        print(f"[Stream] Error getting top games: {e}")
        return []


def format_stream_info(info: Dict) -> str:
    """Format stream info for chat display"""
    if not info:
        return "Could not retrieve stream info."
    
    if not info.get("is_live", False):
        # Show channel info even when offline
        channel = get_channel_info()
        if channel:
            return f"📺 Stream is OFFLINE | Title: {channel['title']} | Category: {channel['game_name']}"
        return "📺 Stream is currently offline."
    
    title = info["title"]
    game = info["game_name"]
    viewers = info["viewer_count"]
    
    # Calculate uptime
    started_at = datetime.fromisoformat(info["started_at"].replace("Z", "+00:00"))
    uptime = datetime.now().astimezone() - started_at
    hours = int(uptime.total_seconds() // 3600)
    minutes = int((uptime.total_seconds() % 3600) // 60)
    
    return f"🔴 LIVE | {title} | {game} | 👥 {viewers} viewers | ⏱️ {hours}h {minutes}m"


# Example usage and testing
if __name__ == "__main__":
    print("=" * 60)
    print("MedlarTV Stream Management - Testing")
    print("=" * 60)
    
    print("\n--- Getting Access Token ---")
    token = get_access_token()
    print(f"Token: {token[:20] if token else 'None'}...")
    
    print("\n--- Getting Broadcaster ID ---")
    broadcaster_id = get_broadcaster_id()
    print(f"Broadcaster ID: {broadcaster_id}")
    
    print("\n--- Getting Stream Info ---")
    stream_info = get_stream_info()
    if stream_info:
        print(format_stream_info(stream_info))
    else:
        print("No stream info available")
    
    print("\n--- Getting Channel Info ---")
    channel_info = get_channel_info()
    if channel_info:
        print(f"Channel: {channel_info['broadcaster_name']}")
        print(f"Title: {channel_info['title']}")
        print(f"Game: {channel_info['game_name']}")
    
    print("\n--- Searching for Games ---")
    test_games = ["Minecraft", "Just Chatting", "League of Legends"]
    for game in test_games:
        game_id = search_game(game)
        print(f"{game}: {game_id}")
    
    print("\n--- Top Games ---")
    top_games = get_top_games(5)
    for i, game in enumerate(top_games, 1):
        print(f"{i}. {game['name']}")