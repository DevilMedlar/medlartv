"""
MedlarTV Moderation Module
Auto-moderation with link filtering, caps detection, spam prevention, and mod commands
"""

import os
import re
import time
from typing import Optional, Dict, List, Tuple
from collections import defaultdict
from pathlib import Path
import yaml

# Feature flags
ENABLE_AUTO_MOD = os.getenv("ENABLE_AUTO_MOD", "true").lower() == "true"
MOD_LINK_FILTER = os.getenv("MOD_LINK_FILTER", "true").lower() == "true"
MOD_CAPS_FILTER = os.getenv("MOD_CAPS_FILTER", "true").lower() == "true"
MOD_SPAM_FILTER = os.getenv("MOD_SPAM_FILTER", "true").lower() == "true"

# Moderation settings
CAPS_THRESHOLD = 0.7  # 70% caps triggers filter
MIN_MESSAGE_LENGTH = 10  # Minimum length to check caps
SPAM_MESSAGE_LIMIT = 5  # Messages per window
SPAM_TIME_WINDOW = 30  # Seconds
LINK_WHITELIST_FILE = Path("MedlarTV/config/link_whitelist.yaml")

# Tracking
user_message_history = defaultdict(list)  # {username: [(message, timestamp), ...]}
warned_users = set()  # Users who have been warned
timeout_history = defaultdict(list)  # {username: [timestamp, ...]}


def load_link_whitelist() -> List[str]:
    """Load whitelisted domains that are allowed"""
    if not LINK_WHITELIST_FILE.exists():
        # Create default whitelist
        default_whitelist = {
            "whitelist": [
                "twitch.tv",
                "clips.twitch.tv",
                "twitter.com",
                "x.com",
                "youtube.com",
                "youtu.be",
                "discord.gg",
                "imgur.com",
                "reddit.com",
                "github.com"
            ]
        }
        LINK_WHITELIST_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LINK_WHITELIST_FILE, 'w') as f:
            yaml.safe_dump(default_whitelist, f)
        return default_whitelist["whitelist"]
    
    try:
        with open(LINK_WHITELIST_FILE, 'r') as f:
            data = yaml.safe_load(f) or {}
        return data.get("whitelist", [])
    except:
        return []


def contains_link(message: str) -> Tuple[bool, Optional[str]]:
    """
    Check if message contains a link.
    
    Returns:
        (has_link, link_or_none)
    """
    # URL patterns
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    domain_pattern = r'\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b'
    
    # Check for explicit URLs
    urls = re.findall(url_pattern, message)
    if urls:
        return True, urls[0]
    
    # Check for domain-like patterns
    domains = re.findall(domain_pattern, message)
    if domains:
        # Filter out common false positives
        false_positives = ["twitch.tv", "youtube.com", "lol.com", "bruh.moment"]
        for domain in domains:
            if domain.lower() not in false_positives:
                return True, domain
    
    return False, None


def is_link_allowed(link: str) -> bool:
    """Check if a link is whitelisted"""
    whitelist = load_link_whitelist()
    
    for allowed_domain in whitelist:
        if allowed_domain.lower() in link.lower():
            return True
    
    return False


def check_caps(message: str) -> bool:
    """
    Check if message is excessively capitalized.
    
    Returns:
        True if message violates caps policy
    """
    if len(message) < MIN_MESSAGE_LENGTH:
        return False
    
    # Count caps vs total letters
    letters = [c for c in message if c.isalpha()]
    if not letters:
        return False
    
    caps_count = sum(1 for c in letters if c.isupper())
    caps_ratio = caps_count / len(letters)
    
    return caps_ratio > CAPS_THRESHOLD


def check_spam(username: str, message: str) -> bool:
    """
    Check if user is spamming messages.
    
    Returns:
        True if user is spamming
    """
    current_time = time.time()
    
    # Clean old messages outside time window
    user_message_history[username] = [
        (msg, ts) for msg, ts in user_message_history[username]
        if current_time - ts < SPAM_TIME_WINDOW
    ]
    
    # Add current message
    user_message_history[username].append((message, current_time))
    
    # Check if too many messages
    if len(user_message_history[username]) > SPAM_MESSAGE_LIMIT:
        return True
    
    # Check for repeated messages
    recent_messages = [msg for msg, _ in user_message_history[username]]
    if len(recent_messages) >= 3:
        if recent_messages[-1] == recent_messages[-2] == recent_messages[-3]:
            return True
    
    return False


def check_message(username: str, message: str, user_role: str = "user") -> Dict[str, any]:
    """
    Main moderation check for a message.
    
    Args:
        username: User who sent the message
        message: Message content
        user_role: User's role (pilot, copilot, mod, vip, user)
    
    Returns:
        Dict with:
        - is_allowed: bool
        - violation: str or None
        - action: str (delete, timeout, warn, allow)
        - reason: str
    """
    if not ENABLE_AUTO_MOD:
        return {"is_allowed": True, "violation": None, "action": "allow", "reason": None}
    
    # Moderators, pilots, and co-pilots bypass auto-mod
    if user_role in ["pilot", "copilot", "mod", "vip"]:
        return {"is_allowed": True, "violation": None, "action": "allow", "reason": "Trusted user"}
    
    # Check for links
    if MOD_LINK_FILTER:
        has_link, link = contains_link(message)
        if has_link and not is_link_allowed(link):
            return {
                "is_allowed": False,
                "violation": "unauthorized_link",
                "action": "timeout" if username not in warned_users else "timeout",
                "reason": f"Unauthorized link: {link}",
                "duration": 60  # 60 second timeout
            }
    
    # Check for excessive caps
    if MOD_CAPS_FILTER:
        if check_caps(message):
            if username not in warned_users:
                warned_users.add(username)
                return {
                    "is_allowed": False,
                    "violation": "excessive_caps",
                    "action": "warn",
                    "reason": "Too many capital letters"
                }
            else:
                return {
                    "is_allowed": False,
                    "violation": "excessive_caps",
                    "action": "timeout",
                    "reason": "Repeated caps spam",
                    "duration": 30
                }
    
    # Check for spam
    if MOD_SPAM_FILTER:
        if check_spam(username, message):
            return {
                "is_allowed": False,
                "violation": "spam",
                "action": "timeout",
                "reason": "Message spam detected",
                "duration": 120  # 2 minute timeout
            }
    
    return {"is_allowed": True, "violation": None, "action": "allow", "reason": None}


def execute_timeout(sock, channel: str, username: str, duration: int, reason: str):
    """
    Execute a timeout command via IRC.
    
    Args:
        sock: IRC socket
        channel: Channel name (e.g., "#devilmedlar")
        username: User to timeout
        duration: Duration in seconds
        reason: Reason for timeout
    """
    timeout_cmd = f"/timeout {username} {duration} {reason}"
    sock.send(f"PRIVMSG {channel} :{timeout_cmd}\r\n".encode("utf-8"))
    
    # Track timeout
    timeout_history[username].append(time.time())
    
    print(f"[Mod] Timed out {username} for {duration}s: {reason}")


def execute_ban(sock, channel: str, username: str, reason: str):
    """Execute a ban command via IRC"""
    ban_cmd = f"/ban {username} {reason}"
    sock.send(f"PRIVMSG {channel} :{ban_cmd}\r\n".encode("utf-8"))
    print(f"[Mod] Banned {username}: {reason}")


def execute_delete(sock, channel: str, msg_id: str):
    """Delete a specific message via IRC"""
    delete_cmd = f"/delete {msg_id}"
    sock.send(f"PRIVMSG {channel} :{delete_cmd}\r\n".encode("utf-8"))
    print(f"[Mod] Deleted message: {msg_id}")


def handle_mod_command(sock, channel: str, username: str, command: str, user_role: str) -> Optional[str]:
    """
    Handle moderation commands (!timeout, !ban, !warn, etc.)
    
    Args:
        sock: IRC socket
        channel: Channel name
        username: User who issued command
        command: Full command string
        user_role: Role of user issuing command
    
    Returns:
        Response message or None
    """
    # Only pilots, co-pilots, and mods can use mod commands
    if user_role not in ["pilot", "copilot", "mod"]:
        return f"@{username} You don't have permission to use mod commands."
    
    parts = command.split()
    cmd = parts[0][1:].lower()  # Remove !
    
    if cmd == "timeout" and len(parts) >= 3:
        target_user = parts[1].lstrip("@")
        try:
            duration = int(parts[2])
            reason = " ".join(parts[3:]) if len(parts) > 3 else "Moderator timeout"
            execute_timeout(sock, channel, target_user, duration, reason)
            return f"@{username} Timed out {target_user} for {duration} seconds."
        except ValueError:
            return f"@{username} Usage: !timeout username seconds [reason]"
    
    elif cmd == "ban" and len(parts) >= 2:
        target_user = parts[1].lstrip("@")
        reason = " ".join(parts[2:]) if len(parts) > 2 else "Moderator ban"
        execute_ban(sock, channel, target_user, reason)
        return f"@{username} Banned {target_user}."
    
    elif cmd == "warn" and len(parts) >= 2:
        target_user = parts[1].lstrip("@")
        warned_users.add(target_user)
        return f"@{target_user} Warning from moderators. Please follow chat rules."
    
    elif cmd == "unwarn" and len(parts) >= 2:
        target_user = parts[1].lstrip("@")
        if target_user in warned_users:
            warned_users.remove(target_user)
            return f"@{username} Removed warning for {target_user}."
        return f"@{username} {target_user} has no warnings."
    
    elif cmd == "whitelist" and len(parts) >= 2:
        domain = parts[1]
        whitelist = load_link_whitelist()
        if domain not in whitelist:
            whitelist.append(domain)
            with open(LINK_WHITELIST_FILE, 'w') as f:
                yaml.safe_dump({"whitelist": whitelist}, f)
            return f"@{username} Added {domain} to whitelist."
        return f"@{username} {domain} is already whitelisted."
    
    elif cmd == "modstats":
        total_warnings = len(warned_users)
        total_timeouts = sum(len(v) for v in timeout_history.values())
        return f"@{username} Mod Stats: {total_warnings} warnings, {total_timeouts} timeouts"
    
    return None


def is_mod_command(message: str) -> bool:
    """Check if message is a moderation command"""
    mod_commands = ["!timeout", "!ban", "!warn", "!unwarn", "!whitelist", "!modstats"]
    return any(message.lower().startswith(cmd) for cmd in mod_commands)


def get_user_timeout_count(username: str, hours: int = 24) -> int:
    """Get number of times user has been timed out in last N hours"""
    cutoff = time.time() - (hours * 3600)
    return sum(1 for ts in timeout_history[username] if ts > cutoff)


# Example usage and testing
if __name__ == "__main__":
    print("=" * 60)
    print("MedlarTV Moderation Module - Testing")
    print("=" * 60)
    
    test_cases = [
        ("user1", "Check out my site at sketchy-site.com", "user"),
        ("user2", "HELLO EVERYONE THIS IS ALL CAPS!!!", "user"),
        ("user3", "spam spam spam spam spam", "user"),
        ("pilot", "https://sketchy-site.com", "pilot"),
        ("user4", "Normal message", "user"),
        ("user5", "Check out this clip: https://clips.twitch.tv/abc123", "user"),
    ]
    
    print("\n--- Moderation Checks ---")
    for username, message, role in test_cases:
        result = check_message(username, message, role)
        print(f"\nUser: {username} ({role})")
        print(f"Message: {message}")
        print(f"Result: {result['action']} - {result['reason'] or 'Allowed'}")
    
    print("\n--- Spam Detection Test ---")
    for i in range(6):
        result = check_message("spammer", f"spam message {i}", "user")
        print(f"Message {i+1}: {result['action']}")