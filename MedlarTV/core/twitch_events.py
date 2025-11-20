"""
MedlarTV Twitch Events Module
Detects and responds to raids, subs, channel points, and uses Twitch emotes
"""

print("[DEBUG twitch_events] Loaded twitch_events.py")

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
TWITCH_CLIENT_ID = os.getenv("APP_TWITCH_CLIENT_ID", "")
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
    print(f"[DEBUG twitch_events] detect_raid() called with msg='{irc_message[:200]}'")

    if not ENABLE_RAID_DETECTION:
        print("[DEBUG twitch_events] detect_raid() → feature disabled (ENABLE_RAID_DETECTION=false)")
        return None
    
    if "msg-id=raid" not in irc_message:
        print("[DEBUG twitch_events] detect_raid() → 'msg-id=raid' not found in message")
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
        print(f"[DEBUG twitch_events] detect_raid() parsed tags={tags}")
        
        if "msg-param-viewerCount" in tags and "msg-param-displayName" in tags:
            raid_info = {
                "type": "raid",
                "raider": tags["msg-param-displayName"],
                "viewer_count": int(tags["msg-param-viewerCount"]),
                "timestamp": datetime.now().isoformat()
            }
            print(f"[DEBUG twitch_events] detect_raid() → detected raid: {raid_info}")
            return raid_info
        else:
            print("[DEBUG twitch_events] detect_raid() → required tags missing (msg-param-viewerCount/displayName)")
    except Exception as e:
        print(f"[Events] Error parsing raid: {e}")
        print(f"[DEBUG twitch_events] detect_raid() exception, raw_message='{irc_message}'")
    
    print("[DEBUG twitch_events] detect_raid() → returning None")
    return None


def detect_subscription(irc_message: str) -> Optional[Dict]:
    """
    Detect subscription/resub from IRC message.
    
    IRC Format: @msg-id=sub/resub/subgift :tmi.twitch.tv USERNOTICE #channel
    
    Returns:
        Dict with sub info or None
    """
    print(f"[DEBUG twitch_events] detect_subscription() called with msg='{irc_message[:200]}'")

    if not ENABLE_SUB_DETECTION:
        print("[DEBUG twitch_events] detect_subscription() → feature disabled (ENABLE_SUB_DETECTION=false)")
        return None
    
    sub_types = ["msg-id=sub", "msg-id=resub", "msg-id=subgift", "msg-id=submysterygift"]
    if not any(st in irc_message for st in sub_types):
        print("[DEBUG twitch_events] detect_subscription() → no sub msg-id found")
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
        print(f"[DEBUG twitch_events] detect_subscription() parsed tags={tags}")
        
        msg_id = tags.get("msg-id", "")
        print(f"[DEBUG twitch_events] detect_subscription() msg-id={msg_id!r}")
        
        if msg_id in ["sub", "resub"]:
            info = {
                "type": "subscription",
                "sub_type": msg_id,
                "subscriber": tags.get("display-name", tags.get("login", "Unknown")),
                "months": int(tags.get("msg-param-cumulative-months", 1)),
                "tier": tags.get("msg-param-sub-plan", "1000"),
                "timestamp": datetime.now().isoformat()
            }
            print(f"[DEBUG twitch_events] detect_subscription() → subscription info={info}")
            return info
        
        elif msg_id == "subgift":
            info = {
                "type": "gift_subscription",
                "gifter": tags.get("display-name", "Anonymous"),
                "recipient": tags.get("msg-param-recipient-display-name", "Unknown"),
                "months": int(tags.get("msg-param-months", 1)),
                "tier": tags.get("msg-param-sub-plan", "1000"),
                "timestamp": datetime.now().isoformat()
            }
            print(f"[DEBUG twitch_events] detect_subscription() → gift_subscription info={info}")
            return info
        
        elif msg_id == "submysterygift":
            info = {
                "type": "mystery_gift",
                "gifter": tags.get("display-name", "Anonymous"),
                "count": int(tags.get("msg-param-sender-count", 1)),
                "tier": tags.get("msg-param-sub-plan", "1000"),
                "timestamp": datetime.now().isoformat()
            }
            print(f"[DEBUG twitch_events] detect_subscription() → mystery_gift info={info}")
            return info
    
    except Exception as e:
        print(f"[Events] Error parsing subscription: {e}")
        print(f"[DEBUG twitch_events] detect_subscription() exception, raw_message='{irc_message}'")
    
    print("[DEBUG twitch_events] detect_subscription() → returning None")
    return None


def detect_channel_point_redemption(irc_message: str) -> Optional[Dict]:
    """
    Detect channel point redemption from IRC message.
    
    IRC Format: @msg-id=reward-redeemed :tmi.twitch.tv USERNOTICE #channel
    
    Returns:
        Dict with redemption info or None
    """
    print(f"[DEBUG twitch_events] detect_channel_point_redemption() called with msg='{irc_message[:200]}'")

    if not ENABLE_CHANNEL_POINTS:
        print("[DEBUG twitch_events] detect_channel_point_redemption() → feature disabled (ENABLE_CHANNEL_POINTS=false)")
        return None
    
    if "msg-id=reward-redeemed" not in irc_message:
        print("[DEBUG twitch_events] detect_channel_point_redemption() → 'msg-id=reward-redeemed' not found")
        return None
    
    try:
        tags = {}
        if irc_message.startswith("@"):
            tag_str = irc_message.split(" ", 1)[0][1:]
            for tag in tag_str.split(";"):
                if "=" in tag:
                    key, value = tag.split("=", 1)
                    tags[key] = value
        print(f"[DEBUG twitch_events] detect_channel_point_redemption() parsed tags={tags}")
        
        info = {
            "type": "channel_points",
            "user": tags.get("display-name", "Unknown"),
            "reward_id": tags.get("custom-reward-id", ""),
            "reward_title": tags.get("msg-param-reward-title", ""),
            "reward_cost": int(tags.get("msg-param-reward-cost", 0)),
            "user_input": tags.get("msg-param-user-input", ""),
            "timestamp": datetime.now().isoformat()
        }
        print(f"[DEBUG twitch_events] detect_channel_point_redemption() → info={info}")
        return info
    
    except Exception as e:
        print(f"[Events] Error parsing channel points: {e}")
        print(f"[DEBUG twitch_events] detect_channel_point_redemption() exception, raw_message='{irc_message}'")
    
    print("[DEBUG twitch_events] detect_channel_point_redemption() → returning None")
    return None


def detect_bits(irc_message: str) -> Optional[Dict]:
    """
    Detect bits/cheering from IRC message.
    
    Returns:
        Dict with bits info or None
    """
    print(f"[DEBUG twitch_events] detect_bits() called with msg='{irc_message[:200]}'")

    if "bits=" not in irc_message.lower():
        print("[DEBUG twitch_events] detect_bits() → 'bits=' not found in message")
        return None
    
    try:
        tags = {}
        if irc_message.startswith("@"):
            tag_str = irc_message.split(" ", 1)[0][1:]
            for tag in tag_str.split(";"):
                if "=" in tag:
                    key, value = tag.split("=", 1)
                    tags[key] = value
        print(f"[DEBUG twitch_events] detect_bits() parsed tags={tags}")
        
        if "bits" in tags:
            info = {
                "type": "bits",
                "user": tags.get("display-name", "Unknown"),
                "amount": int(tags.get("bits", 0)),
                "timestamp": datetime.now().isoformat()
            }
            print(f"[DEBUG twitch_events] detect_bits() → info={info}")
            return info
        else:
            print("[DEBUG twitch_events] detect_bits() → 'bits' tag not found")
    
    except Exception as e:
        print(f"[Events] Error parsing bits: {e}")
        print(f"[DEBUG twitch_events] detect_bits() exception, raw_message='{irc_message}'")
    
    print("[DEBUG twitch_events] detect_bits() → returning None")
    return None


def get_raid_response(raid_info: Dict) -> str:
    """Generate response for raid"""
    print(f"[DEBUG twitch_events] get_raid_response() called with raid_info={raid_info}")
    raider = raid_info["raider"]
    viewers = raid_info["viewer_count"]
    
    responses = [
        f"🚨 RAID ALERT! 🚨 Welcome {raider} and {viewers} raiders! PogChamp",
        f"⚡ {raider} just raided with {viewers} viewers! LET'S GOOO! 🔥",
        f"🎉 HUGE raid from {raider}! Welcome {viewers} new friends! devilmeGODMODE",
        f"💥 {raider} brought {viewers} raiders! Thank you so much! 💖",
    ]
    
    chosen = random.choice(responses)
    print(f"[DEBUG twitch_events] get_raid_response() → chosen='{chosen}'")
    return chosen


def get_sub_response(sub_info: Dict) -> str:
    """Generate response for subscription"""
    print(f"[DEBUG twitch_events] get_sub_response() called with sub_info={sub_info}")
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
        
        chosen = random.choice(responses)
        print(f"[DEBUG twitch_events] get_sub_response() → subscription chosen='{chosen}'")
        return chosen
    
    elif sub_info["type"] == "gift_subscription":
        gifter = sub_info["gifter"]
        recipient = sub_info["recipient"]
        
        responses = [
            f"🎁 {gifter} just gifted a sub to {recipient}! So generous! 💖",
            f"⭐ Gift sub from {gifter} to {recipient}! Amazing! PogChamp",
            f"💝 {gifter} spreading the love with a gift sub for {recipient}! 🔥",
        ]
        
        chosen = random.choice(responses)
        print(f"[DEBUG twitch_events] get_sub_response() → gift_subscription chosen='{chosen}'")
        return chosen
    
    elif sub_info["type"] == "mystery_gift":
        gifter = sub_info["gifter"]
        count = sub_info["count"]
        
        responses = [
            f"🎁✨ {gifter} just gifted {count} subs! LEGENDARY! 👑",
            f"💖 MASSIVE gift sub bomb from {gifter}! {count} subs! devilmeGODMODE",
            f"🚀 {gifter} is going CRAZY with {count} gift subs! Thank you! 🔥",
        ]
        
        chosen = random.choice(responses)
        print(f"[DEBUG twitch_events] get_sub_response() → mystery_gift chosen='{chosen}'")
        return chosen
    
    fallback = f"Thanks for the sub! 💖"
    print(f"[DEBUG twitch_events] get_sub_response() → fallback='{fallback}'")
    return fallback


def get_channel_point_response(redemption_info: Dict) -> str:
    """Generate response for channel point redemption"""
    print(f"[DEBUG twitch_events] get_channel_point_response() called with redemption_info={redemption_info}")
    user = redemption_info["user"]
    reward = redemption_info["reward_title"]
    
    msg = f"⭐ {user} redeemed: {reward}! Thanks for using your points! 💖"
    print(f"[DEBUG twitch_events] get_channel_point_response() → '{msg}'")
    return msg


def get_bits_response(bits_info: Dict) -> str:
    """Generate response for bits/cheering"""
    print(f"[DEBUG twitch_events] get_bits_response() called with bits_info={bits_info}")
    user = bits_info["user"]
    amount = bits_info["amount"]
    
    if amount >= 1000:
        msg = f"💎 HUGE CHEER! {user} just dropped {amount} bits! You're amazing! 🔥"
    elif amount >= 100:
        msg = f"⭐ {user} cheered {amount} bits! Thank you so much! PogChamp"
    else:
        msg = f"💖 Thanks for the {amount} bits, {user}! Appreciate you!"
    
    print(f"[DEBUG twitch_events] get_bits_response() → '{msg}'")
    return msg


def load_global_emotes(token: str) -> List[str]:
    """Load global Twitch emotes"""
    print(f"[DEBUG twitch_events] load_global_emotes() called with token_present={bool(token)}")
    global _global_emotes
    
    if _global_emotes:
        print(f"[DEBUG twitch_events] load_global_emotes() → returning cached {_global_emotes and len(_global_emotes)} emotes")
        return _global_emotes
    
    try:
        headers = {
            "Client-ID": TWITCH_CLIENT_ID,
            "Authorization": f"Bearer {token}"
        }
        print(f"[DEBUG twitch_events] load_global_emotes() headers={headers}")
        
        response = requests.get(
            f"{TWITCH_API_BASE}/chat/emotes/global",
            headers=headers
        )
        print(f"[DEBUG twitch_events] load_global_emotes() status={response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            _global_emotes = [emote["name"] for emote in data["data"]]
            print(f"[Events] Loaded {len(_global_emotes)} global emotes")
            print(f"[DEBUG twitch_events] load_global_emotes() emotes_sample={_global_emotes[:10]}")
            return _global_emotes
        
        print(f"[DEBUG twitch_events] load_global_emotes() non-200 response: {response.status_code} body={response.text[:200]}")
        return []
    
    except Exception as e:
        print(f"[Events] Error loading global emotes: {e}")
        print(f"[DEBUG twitch_events] load_global_emotes() exception={e}")
        return []


def load_channel_emotes(token: str, broadcaster_id: str) -> List[str]:
    """Load channel-specific emotes"""
    print(f"[DEBUG twitch_events] load_channel_emotes() called with token_present={bool(token)} broadcaster_id={broadcaster_id!r}")
    global _channel_emotes
    
    if _channel_emotes:
        print(f"[DEBUG twitch_events] load_channel_emotes() → returning cached {_channel_emotes and len(_channel_emotes)} emotes")
        return _channel_emotes
    
    try:
        headers = {
            "Client-ID": TWITCH_CLIENT_ID,
            "Authorization": f"Bearer {token}"
        }
        print(f"[DEBUG twitch_events] load_channel_emotes() headers={headers}")
        
        response = requests.get(
            f"{TWITCH_API_BASE}/chat/emotes",
            headers=headers,
            params={"broadcaster_id": broadcaster_id}
        )
        print(f"[DEBUG twitch_events] load_channel_emotes() status={response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            _channel_emotes = [emote["name"] for emote in data["data"]]
            print(f"[Events] Loaded {len(_channel_emotes)} channel emotes")
            print(f"[DEBUG twitch_events] load_channel_emotes() emotes_sample={_channel_emotes[:10]}")
            return _channel_emotes
        
        print(f"[DEBUG twitch_events] load_channel_emotes() non-200 response: {response.status_code} body={response.text[:200]}")
        return []
    
    except Exception as e:
        print(f"[Events] Error loading channel emotes: {e}")
        print(f"[DEBUG twitch_events] load_channel_emotes() exception={e}")
        return []


def add_random_emote(message: str, emotes: List[str]) -> str:
    """Add a random Twitch emote to message"""
    print(f"[DEBUG twitch_events] add_random_emote() called with message='{message}' emote_count={len(emotes) if emotes else 0}")
    if not ENABLE_EMOTE_RESPONSES or not emotes:
        print("[DEBUG twitch_events] add_random_emote() → feature disabled or no emotes")
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
        print("[DEBUG twitch_events] add_random_emote() → no preferred emotes found, sampling from all")
        available_emotes = random.sample(emotes, min(10, len(emotes)))
    else:
        print(f"[DEBUG twitch_events] add_random_emote() → using preferred emotes={available_emotes}")
    
    emote = random.choice(available_emotes)
    result = f"{message} {emote}"
    print(f"[DEBUG twitch_events] add_random_emote() → '{result}'")
    return result


def extract_emotes_from_message(message: str, emotes: List[str]) -> List[str]:
    """Extract which emotes were used in a message"""
    print(f"[DEBUG twitch_events] extract_emotes_from_message() called with message='{message}' emote_count={len(emotes) if emotes else 0}")
    found_emotes = []
    for emote in emotes:
        if emote in message:
            print(f"[DEBUG twitch_events] extract_emotes_from_message() found emote='{emote}'")
            found_emotes.append(emote)
    print(f"[DEBUG twitch_events] extract_emotes_from_message() → found={found_emotes}")
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
    else:
        print("No raid detected")
    
    # Test sub detection
    print("\n--- Subscription Detection ---")
    sub_msg = "@msg-id=sub;display-name=TestSub;msg-param-cumulative-months=1;msg-param-sub-plan=1000 :tmi.twitch.tv USERNOTICE #channel"
    sub_info = detect_subscription(sub_msg)
    if sub_info:
        print(f"Detected: {sub_info}")
        print(f"Response: {get_sub_response(sub_info)}")
    else:
        print("No subscription detected")
    
    # Test gift sub
    print("\n--- Gift Sub Detection ---")
    gift_msg = "@msg-id=subgift;display-name=Gifter;msg-param-recipient-display-name=Lucky;msg-param-months=1 :tmi.twitch.tv USERNOTICE #channel"
    gift_info = detect_subscription(gift_msg)
    if gift_info:
        print(f"Detected: {gift_info}")
        print(f"Response: {get_sub_response(gift_info)}")
    else:
        print("No gift subscription detected")
    
    # Test channel points
    print("\n--- Channel Points Detection ---")
    points_msg = "@msg-id=reward-redeemed;display-name=Viewer;msg-param-reward-title=Hydrate;msg-param-reward-cost=100 :tmi.twitch.tv USERNOTICE #channel"
    points_info = detect_channel_point_redemption(points_msg)
    if points_info:
        print(f"Detected: {points_info}")
        print(f"Response: {get_channel_point_response(points_info)}")
    else:
        print("No channel points detected")
    
    # Test bits
    print("\n--- Bits Detection ---")
    bits_msg = "@bits=500;display-name=Cheerer :tmi.twitch.tv PRIVMSG #channel :Cheer500 Let's go!"
    bits_info = detect_bits(bits_msg)
    if bits_info:
        print(f"Detected: {bits_info}")
        print(f"Response: {get_bits_response(bits_info)}")
    else:
        print("No bits detected")

        print(f"Response: {get_bits_response(bits_info)}")