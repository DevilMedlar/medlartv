"""
MedlarTV Content Filter
Prevents the bot from saying inappropriate things.
Super easy to configure via content_filter.yaml!
"""

import os
import yaml
import re
import time
from pathlib import Path

# State tracking for all caps mode
all_caps_state = {
    "active": False,
    "message_count": 0,
    "last_used": 0
}


def load_filter_config():
    """Load the content filter configuration."""
    config_path = Path("MedlarTV/config/content_filter.yaml")
    
    if not config_path.exists():
        # Return safe defaults if file doesn't exist
        return {
            "blocked_words": [],
            "blocked_topics": [],
            "response_modes": {
                "all_caps": {
                    "enabled": True,
                    "max_messages": 3,
                    "cooldown_seconds": 60
                },
                "emoji_limit": {
                    "enabled": True,
                    "max_per_message": 3
                }
            },
            "safety": {
                "max_message_length": 500,
                "cooldown_seconds": 8,
                "protected_users": []
            }
        }
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def normalize_text(text):
    """Normalize text for comparison (lowercase, remove special chars)."""
    return re.sub(r'[^a-z0-9\s]', '', text.lower())


def contains_blocked_word(text, blocked_words):
    """Check if text contains any blocked words."""
    normalized = normalize_text(text)
    
    for word in blocked_words:
        # Skip censored words (with asterisks) - they're examples
        if '*' in word:
            continue
            
        # Normalize the blocked word too
        normalized_word = normalize_text(word)
        
        # Skip if normalized word is too short (avoid false positives)
        if len(normalized_word) < 4:
            continue
        
        # Check for whole word matches
        pattern = r'\b' + re.escape(normalized_word) + r'\b'
        if re.search(pattern, normalized):
            return True, word
    
    return False, None


def contains_blocked_topic(text, blocked_topics):
    """Check if text discusses blocked topics."""
    normalized = normalize_text(text)
    
    for topic in blocked_topics:
        normalized_topic = normalize_text(topic)
        if normalized_topic in normalized:
            return True, topic
    
    return False, None


def should_enable_all_caps(message):
    """Check if message wants all caps mode, and if it's allowed."""
    config = load_filter_config()
    caps_config = config.get("response_modes", {}).get("all_caps", {})
    
    if not caps_config.get("enabled", True):
        return False
    
    global all_caps_state
    
    # If already active, don't re-activate
    if all_caps_state["active"]:
        return False
    
    # Check if user is requesting all caps
    message_lower = message.lower()
    yell_triggers = ["yell", "scream", "shout", "all caps", "caps lock", "loud"]
    
    wants_caps = any(trigger in message_lower for trigger in yell_triggers)
    
    if wants_caps:
        current_time = time.time()
        cooldown = caps_config.get("cooldown_seconds", 60)
        
        # Check cooldown
        if current_time - all_caps_state["last_used"] < cooldown:
            remaining = int(cooldown - (current_time - all_caps_state["last_used"]))
            print(f"[Filter] All caps on cooldown ({remaining}s remaining)")
            return False  # Still on cooldown
        
        # Enable all caps mode
        all_caps_state["active"] = True
        all_caps_state["message_count"] = 0
        all_caps_state["last_used"] = current_time
        print(f"[Filter] ✓ All caps mode ACTIVATED! Will yell for next 3 responses")
        return True
    
    return False


def apply_all_caps_mode(text):
    """Apply all caps mode with counter."""
    config = load_filter_config()
    caps_config = config.get("response_modes", {}).get("all_caps", {})
    max_messages = caps_config.get("max_messages", 3)
    
    global all_caps_state
    
    # Debug output
    print(f"[Filter DEBUG] active={all_caps_state['active']}, count={all_caps_state['message_count']}")
    
    if not all_caps_state["active"]:
        return text
    
    # Increment counter
    all_caps_state["message_count"] += 1
    
    print(f"[Filter] 📢 All caps message #{all_caps_state['message_count']}/{max_messages}")
    
    # Check if we should stop yelling
    if all_caps_state["message_count"] >= max_messages:
        all_caps_state["active"] = False
        all_caps_state["message_count"] = 0
        print(f"[Filter] ✓ All caps mode DEACTIVATED after {max_messages} messages")
        # Add a note that we're done yelling
        return text.upper() + " ...okay I'm done yelling now"
    
    return text.upper()


def limit_emojis(text):
    """Limit the number of emojis in a message."""
    config = load_filter_config()
    emoji_config = config.get("response_modes", {}).get("emoji_limit", {})
    
    if not emoji_config.get("enabled", True):
        return text
    
    max_emojis = emoji_config.get("max_per_message", 3)
    
    # Simple emoji detection (matches Unicode emoji ranges)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE
    )
    
    emojis = emoji_pattern.findall(text)
    
    if len(emojis) <= max_emojis:
        return text
    
    # Remove excess emojis
    for emoji in emojis[max_emojis:]:
        text = text.replace(emoji, '', 1)
    
    return text


def filter_message(text, username=None):
    """
    Main filter function. Returns (is_safe, filtered_text, reason).
    
    Returns:
        tuple: (is_safe: bool, filtered_text: str, reason: str or None)
    """
    config = load_filter_config()
    
    # Check for blocked words
    has_blocked, word = contains_blocked_word(
        text, 
        config.get("blocked_words", [])
    )
    if has_blocked:
        return False, None, f"Contains blocked word: {word}"
    
    # Check for blocked topics
    has_topic, topic = contains_blocked_topic(
        text,
        config.get("blocked_topics", [])
    )
    if has_topic:
        return False, None, f"Discusses blocked topic: {topic}"
    
    # Check protected users (don't @mention them)
    protected = config.get("safety", {}).get("protected_users", [])
    if username and username.lower() in [u.lower() for u in protected]:
        # Remove @mentions of this user
        text = re.sub(rf'@{username}\b', username, text, flags=re.IGNORECASE)
    
    # Apply emoji limit
    text = limit_emojis(text)
    
    # Apply all caps mode if active (THIS IS THE KEY PART)
    text = apply_all_caps_mode(text)
    
    # Enforce max length
    max_length = config.get("safety", {}).get("max_message_length", 500)
    if len(text) > max_length:
        text = text[:max_length-3] + "..."
    
    return True, text, None


def reset_all_caps_mode():
    """Manually reset all caps mode."""
    global all_caps_state
    all_caps_state["active"] = False
    all_caps_state["message_count"] = 0
    print("[Filter] All caps mode manually reset")


def get_safety_response():
    """Get a safe response when content is blocked."""
    responses = [
        "I can't respond to that. Let's keep things positive!",
        "That's not something I can discuss. How about we talk about something else?",
        "I'm programmed to keep things friendly and safe. Let's change topics!",
        "Nope, can't go there. Ask me something else!",
        "That crosses a line. Let's keep the vibes good!"
    ]
    import random
    return random.choice(responses)


# Example usage and testing
if __name__ == "__main__":
    print("MedlarTV Content Filter - Testing\n")
    
    test_cases = [
        "This is a normal message",
        "Can you YELL for me?",  # Should activate
        "Another message",       # Should be in caps (1/3)
        "And another",           # Should be in caps (2/3)
        "Last caps one",         # Should be in caps (3/3) + deactivate
        "Back to normal",        # Should be normal
    ]
    
    for i, message in enumerate(test_cases):
        print(f"\n{'='*60}")
        print(f"Test {i+1}: {message}")
        print(f"{'='*60}")
        
        # Check if this message wants to enable caps
        if should_enable_all_caps(message):
            print("  → User requested all caps mode!")
        
        # Filter the response
        response_text = f"Response to: {message}"
        is_safe, filtered, reason = filter_message(response_text, None)
        
        if is_safe:
            print(f"  Output: {filtered}")
        else:
            print(f"  BLOCKED: {reason}")
            print(f"  Safe response: {get_safety_response()}")