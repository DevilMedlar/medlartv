"""
MedlarTV Twitch Events Module
Detects and responds to raids, subs, channel points, and uses Twitch emotes
"""

import os
import re
import random
import requests
from typing import Optional, Dict, List, Tuple
from datetime import datetime

# Feature flags
ENABLE_RAID_DETECTION = os.getenv("ENABLE_RAID_DETECTION", "true").lower() == "true"
ENABLE_SUB_DETECTION = os.getenv("ENABLE_SUB_DETECTION", "true").lower() == "true"
ENABLE_CHANNEL_POINTS = os.getenv("ENABLE_CHANNEL_POINTS", "true").lower() == "true"
ENABLE_EMOTE_RESPONSES = os.getenv("ENABLE_EMOTE_RESPONSES", "true").lower() == "true"

# Twitch API
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID", "")
TWITCH_API_BASE = "https://api.twitch.tv/helix"

# Emote cache
_global_emotes = None
_channel_emotes = None


def detect_raid(irc_message: str) -> Optional[Dict]:
    """
    Detect raid from IRC message.
    
    IRC Format: @msg-id=raid :tmi.twitch.tv USERNOTICE #channel
    
    Returns:
        Dict with raid info or None
    """
    if not ENABLE_RAID_DETECTION:
        return None
    
    if "msg-id=raid" not in irc_message:
        return None
    
    try:
        # Extract raid info from tags
        tags = {}
        if irc_message.startswith("@"):
            tag_str = irc_message.split(" ", 1)[0][1:]
            for tag in tag_str.split(";"):
                if "=" in tag:
                    key, value = tag.split("=", 1)
                    tags[key] = value
        
        if "msg-param-viewerCount" in tags and "msg-param-displayName" in tags:
            return {
                "type": "raid",
                "raider": tags["msg-param-displayName"],
                "viewer_count": int(tags["msg-param-viewerCount"]),
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        print(f"[Events] Error parsing raid: {e}")
    
    return None


def detect_subscription(irc_message: str) -> Optional[Dict]:
    """
    Detect subscription/resub from IRC message.
    
    IRC Format: @msg-id=sub/resub/subgift :tmi.twitch.tv USERNOTICE #channel
    
    Returns:
        Dict with sub info or None
    """
    if not ENABLE_SUB_DETECTION:
        return None
    
    sub_types = ["msg-id=sub", "msg-id=resub", "msg-id=subgift", "msg-id=submysterygift"]
    if not any(st in irc_message for st in sub_types):
        return None
    
    try:
        # Extract sub info from tags
        tags = {}
        if irc_message.startswith("@"):
            tag_str = irc_message.split(" ", 1)[0][1:]
            for tag in tag_str.split(";"):
                if "=" in tag:
                    key, value = tag.split("=", 1)
                    tags[key] = value
        
        msg_id = tags.get("msg-id", "")
        
        if msg_id in ["sub", "resub"]:
            return {
                "type": "subscription",
                "sub_type": msg_id,
                "subscriber": tags.get("display-name", tags.get("login", "Unknown")),
                "months": int(tags.get("msg-param-cumulative-months", 1)),
                "tier": tags.get("msg-param-sub-plan", "1000"),
                "timestamp": datetime.now().isoformat()
            }
        
        elif msg_id == "subgift":
            return {
                "type": "gift_subscription",
                "gifter": tags.get("display-name", "Anonymous"),
                "recipient": tags.get("msg-param-recipient-display-name", "Unknown"),
                "months": int(tags.get("msg-param-months", 1)),
                "tier": tags.get("msg-param-sub-plan", "1000"),
                "timestamp": datetime.now().isoformat()
            }
        
        elif msg_id == "submysterygift":
            return {
                "type": "mystery_gift",
                "gifter": tags.get("display-name", "Anonymous"),
                "count": int(tags.get("msg-param-sender-count", 1)),
                "tier": tags.get("msg-param-sub-plan", "1000"),
                "timestamp": datetime.now().isoformat()
            }
    
    except Exception as e:
        print(f"[Events] Error parsing subscription: {e}")
    
    return None


def detect_channel_point_redemption(irc_message: str) -> Optional[Dict]:
    """
    Detect channel point redemption from IRC message.
    
    IRC Format: @msg-id=reward-redeemed :tmi.twitch.tv USERNOTICE #channel
    
    Returns:
        Dict with redemption info or None
    """
    if not ENABLE_CHANNEL_POINTS:
        return None
    
    if "msg-id=reward-redeemed" not in irc_message:
        return None
    
    try:
        tags = {}
        if irc_message.startswith("@"):
            tag_str = irc_message.split(" ", 1)[0][1:]
            for tag in tag_str.split(";"):
                if "=" in tag:
                    key, value = tag.split("=", 1)
                    tags[key] = value
        
        return {
            "type": "channel_points",
            "user": tags.get("display-name", "Unknown"),
            "reward_id": tags.get("custom-reward-id", ""),
            "reward_title": tags.get("msg-param-reward-title", ""),
            "reward_cost": int(tags.get("msg-param-reward-cost", 0)),
            "user_input": tags.get("msg-param-user-input", ""),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        print(f"[Events] Error parsing channel points: {e}")
    
    return None


def detect_bits(irc_message: str) -> Optional[Dict]:
    """
    Detect bits/cheering from IRC message.
    
    Returns:
        Dict with bits info or None
    """
    if "bits=" not in irc_message.lower():
        return None
    
    try:
        tags = {}
        if irc_message.startswith("@"):
            tag_str = irc_message.split(" ", 1)[0][1:]
            for tag in tag_str.split(";"):
                if "=" in tag:
                    key, value = tag.split("=", 1)
                    tags[key] = value
        
        if "bits" in tags:
            return {
                "type": "bits",
                "user": tags.get("display-name", "Unknown"),
                "amount": int(tags.get("bits", 0)),
                "timestamp": datetime.now().isoformat()
            }
    
    except Exception as e:
        print(f"[Events] Error parsing bits: {e}")
    
    return None


def get_raid_response(raid_info: Dict) -> str:
    """Generate response for raid"""
    raider = raid_info["raider"]
    viewers = raid_info["viewer_count"]
    
    responses = [
        f"🚨 RAID ALERT! 🚨 Welcome {raider} and {viewers} raiders! PogChamp",
        f"⚡ {raider} just raided with {viewers} viewers! LET'S GOOO! 🔥",
        f"🎉 HUGE raid from {raider}! Welcome {viewers} new friends! devilmeGODMODE",
        f"💥 {raider} brought {viewers} raiders! Thank you so much! 💖",
    ]
    
    return random.choice(responses)


def get_sub_response(sub_info: Dict) -> str:
    """Generate response for subscription"""
    if sub_info["type"] == "subscription":
        subscriber = sub_info["subscriber"]
        months = sub_info["months"]
        
        if months == 1:
            responses = [
                f"🎉 Welcome to the squad, {subscriber}! Thanks for the sub! 💖",
                f"⭐ {subscriber} just subscribed! You're awesome! devilmeGODMODE",
                f"🔥 NEW SUB HYPE! Thanks {subscriber}! PogChamp",
            ]
        else:
            responses = [
                f"🎊 {subscriber} resubbed for {months} months! Legend! 👑",
                f"💖 {months} MONTHS! Thanks for the continued support, {subscriber}!",
                f"⚡ {subscriber} has been here for {months} months! Absolute legend! 🔥",
            ]
        
        return random.choice(responses)
    
    elif sub_info["type"] == "gift_subscription":
        gifter = sub_info["gifter"]
        recipient = sub_info["recipient"]
        
        responses = [
            f"🎁 {gifter} just gifted a sub to {recipient}! So generous! 💖",
            f"⭐ Gift sub from {gifter} to {recipient}! Amazing! PogChamp",
            f"💝 {gifter} spreading the love with a gift sub for {recipient}! 🔥",
        ]
        
        return random.choice(responses)
    
    elif sub_info["type"] == "mystery_gift":
        gifter = sub_info["gifter"]
        count = sub_info["count"]
        
        responses = [
            f"🎁✨ {gifter} just gifted {count} subs! LEGENDARY! 👑",
            f"💖 MASSIVE gift sub bomb from {gifter}! {count} subs! devilmeGODMODE",
            f"🚀 {gifter} is going CRAZY with {count} gift subs! Thank you! 🔥",
        ]
        
        return random.choice(responses)
    
    return f"Thanks for the sub! 💖"


def get_channel_point_response(redemption_info: Dict) -> str:
    """Generate response for channel point redemption"""
    user = redemption_info["user"]
    reward = redemption_info["reward_title"]
    
    return f"⭐ {user} redeemed: {reward}! Thanks for using your points! 💖"


def get_bits_response(bits_info: Dict) -> str:
    """Generate response for bits/cheering"""
    user = bits_info["user"]
    amount = bits_info["amount"]
    
    if amount >= 1000:
        return f"💎 HUGE CHEER! {user} just dropped {amount} bits! You're amazing! 🔥"
    elif amount >= 100:
        return f"⭐ {user} cheered {amount} bits! Thank you so much! PogChamp"
    else:
        return f"💖 Thanks for the {amount} bits, {user}! Appreciate you!"


def load_global_emotes(token: str) -> List[str]:
    """Load global Twitch emotes"""
    global _global_emotes
    
    if _global_emotes:
        return _global_emotes
    
    try:
        headers = {
            "Client-ID": TWITCH_CLIENT_ID,
            "Authorization": f"Bearer {token}"
        }
        
        response = requests.get(
            f"{TWITCH_API_BASE}/chat/emotes/global",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            _global_emotes = [emote["name"] for emote in data["data"]]
            print(f"[Events] Loaded {len(_global_emotes)} global emotes")
            return _global_emotes
        
        return []
    
    except Exception as e:
        print(f"[Events] Error loading global emotes: {e}")
        return []


def load_channel_emotes(token: str, broadcaster_id: str) -> List[str]:
    """Load channel-specific emotes"""
    global _channel_emotes
    
    if _channel_emotes:
        return _channel_emotes
    
    try:
        headers = {
            "Client-ID": TWITCH_CLIENT_ID,
            "Authorization": f"Bearer {token}"
        }
        
        response = requests.get(
            f"{TWITCH_API_BASE}/chat/emotes",
            headers=headers,
            params={"broadcaster_id": broadcaster_id}
        )
        
        if response.status_code == 200:
            data = response.json()
            _channel_emotes = [emote["name"] for emote in data["data"]]
            print(f"[Events] Loaded {len(_channel_emotes)} channel emotes")
            return _channel_emotes
        
        return []
    
    except Exception as e:
        print(f"[Events] Error loading channel emotes: {e}")
        return []


def add_random_emote(message: str, emotes: List[str]) -> str:
    """Add a random Twitch emote to message"""
    if not ENABLE_EMOTE_RESPONSES or not emotes:
        return message
    
    # Common emotes that work well in responses
    good_emotes = [
        "PogChamp", "Kappa", "LUL", "NotLikeThis", "BibleThump",
        "VoHiYo", "CoolCat", "DansGame", "ResidentSleeper", "4Head",
        "devilmeGODMODE"  # Custom emote
    ]
    
    # Use good emotes if available, otherwise random
    available_emotes = [e for e in good_emotes if e in emotes]
    if not available_emotes:
        available_emotes = random.sample(emotes, min(10, len(emotes)))
    
    emote = random.choice(available_emotes)
    return f"{message} {emote}"


def extract_emotes_from_message(message: str, emotes: List[str]) -> List[str]:
    """Extract which emotes were used in a message"""
    found_emotes = []
    for emote in emotes:
        if emote in message:
            found_emotes.append(emote)
    return found_emotes


# Example usage and testing
if __name__ == "__main__":
    print("=" * 60)
    print("MedlarTV Twitch Events - Testing")
    print("=" * 60)
    
    # Test raid detection
    print("\n--- Raid Detection ---")
    raid_msg = "@msg-id=raid;msg-param-displayName=TestRaider;msg-param-viewerCount=50 :tmi.twitch.tv USERNOTICE #channel"
    raid_info = detect_raid(raid_msg)
    if raid_info:
        print(f"Detected: {raid_info}")
        print(f"Response: {get_raid_response(raid_info)}")
    
    # Test sub detection
    print("\n--- Subscription Detection ---")
    sub_msg = "@msg-id=sub;display-name=TestSub;msg-param-cumulative-months=1;msg-param-sub-plan=1000 :tmi.twitch.tv USERNOTICE #channel"
    sub_info = detect_subscription(sub_msg)
    if sub_info:
        print(f"Detected: {sub_info}")
        print(f"Response: {get_sub_response(sub_info)}")
    
    # Test gift sub
    print("\n--- Gift Sub Detection ---")
    gift_msg = "@msg-id=subgift;display-name=Gifter;msg-param-recipient-display-name=Lucky;msg-param-months=1 :tmi.twitch.tv USERNOTICE #channel"
    gift_info = detect_subscription(gift_msg)
    if gift_info:
        print(f"Detected: {gift_info}")
        print(f"Response: {get_sub_response(gift_info)}")
    
    # Test channel points
    print("\n--- Channel Points Detection ---")
    points_msg = "@msg-id=reward-redeemed;display-name=Viewer;msg-param-reward-title=Hydrate;msg-param-reward-cost=100 :tmi.twitch.tv USERNOTICE #channel"
    points_info = detect_channel_point_redemption(points_msg)
    if points_info:
        print(f"Detected: {points_info}")
        print(f"Response: {get_channel_point_response(points_info)}")
    
    # Test bits
    print("\n--- Bits Detection ---")
    bits_msg = "@bits=500;display-name=Cheerer :tmi.twitch.tv PRIVMSG #channel :Cheer500 Let's go!"
    bits_info = detect_bits(bits_msg)
    if bits_info:
        print(f"Detected: {bits_info}")
        print(f"Response: {get_bits_response(bits_info)}")