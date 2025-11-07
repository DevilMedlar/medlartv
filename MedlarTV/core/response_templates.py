"""
MedlarTV Response Templates
Reduces repetitive responses with template variations
"""

import os
import random
import yaml
from pathlib import Path
from typing import List, Dict, Optional

# Check if templates are enabled
ENABLE_TEMPLATES = os.getenv("ENABLE_RESPONSE_TEMPLATES", "true").lower() == "true"
MIN_VARIATION = int(os.getenv("MIN_TEMPLATE_VARIATION", "3"))

# Track recently used templates to avoid repetition
recent_templates = {
    "greeting": [],
    "agreement": [],
    "hype": [],
    "support": [],
    "sarcastic": []
}


def load_templates() -> Dict[str, List[str]]:
    """Load response templates from personality.yaml"""
    config_path = Path("MedlarTV/config/personality.yaml")
    
    if not config_path.exists():
        return {}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
        
        personality = config.get("personality", {})
        return personality.get("response_templates", {})
    except Exception as e:
        print(f"[Templates] Error loading templates: {e}")
        return {}


def get_template(template_type: str, username: str = None, emoji: str = None, avoid_recent: bool = True) -> Optional[str]:
    """
    Get a response template with variation.
    
    Args:
        template_type: Type of template (greeting, agreement, hype, etc.)
        username: Username to insert into template
        emoji: Emoji to insert into template
        avoid_recent: If True, avoid recently used templates
    
    Returns:
        Formatted template string, or None if not found
    """
    if not ENABLE_TEMPLATES:
        return None
    
    templates = load_templates()
    
    if template_type not in templates:
        return None
    
    available_templates = templates[template_type]
    
    if not available_templates:
        return None
    
    # Filter out recently used templates
    if avoid_recent and template_type in recent_templates:
        recent = recent_templates[template_type]
        if len(recent) < len(available_templates):
            available = [t for t in available_templates if t not in recent]
            if available:
                available_templates = available
    
    # Select random template
    template = random.choice(available_templates)
    
    # Track usage
    if template_type in recent_templates:
        recent_templates[template_type].append(template)
        # Keep only last MIN_VARIATION templates
        if len(recent_templates[template_type]) > MIN_VARIATION:
            recent_templates[template_type].pop(0)
    
    # Format template
    if username:
        template = template.replace("{user}", username)
    
    if emoji:
        template = template.replace("{emoji}", emoji)
    
    return template


def get_greeting(username: str, emoji: str = "👋") -> str:
    """Get a varied greeting"""
    template = get_template("greeting", username, emoji)
    return template if template else f"Hey {username}! {emoji}"


def get_agreement(username: str = None, emoji: str = "💯") -> str:
    """Get a varied agreement response"""
    template = get_template("agreement", username, emoji)
    return template if template else f"Absolutely! {emoji}"


def get_hype(username: str = None, emoji: str = "🔥") -> str:
    """Get a varied hype response"""
    template = get_template("hype", username, emoji)
    return template if template else f"LET'S GOOOO! {emoji}"


def get_support(username: str, emoji: str = "💖") -> str:
    """Get a varied supportive response"""
    template = get_template("support", username, emoji)
    return template if template else f"You got this, {username}! {emoji}"


def get_sarcastic(username: str = None, emoji: str = "😏") -> str:
    """Get a varied sarcastic response"""
    template = get_template("sarcastic", username, emoji)
    return template if template else f"Oh really? {emoji}"


def detect_template_type(message: str, mood: str = "chill") -> Optional[str]:
    """
    Automatically detect which template type to use based on message content and mood.
    
    Args:
        message: User's message
        mood: Current bot mood
    
    Returns:
        Template type to use, or None
    """
    message_lower = message.lower()
    
    # Greeting detection
    greetings = ["hi", "hello", "hey", "yo", "sup", "what's up", "whats up", "howdy"]
    if any(g in message_lower.split() for g in greetings):
        return "greeting"
    
    # Agreement detection
    agreements = ["agree", "true", "facts", "exactly", "right", "yes", "yep", "yeah"]
    if any(a in message_lower for a in agreements):
        return "agreement"
    
    # Hype detection (or if mood is hype)
    hype_words = ["hype", "let's go", "lets go", "pog", "amazing", "awesome", "incredible"]
    if mood == "hype" or any(h in message_lower for h in hype_words):
        return "hype"
    
    # Support detection
    support_words = ["help", "sad", "tired", "struggling", "hard", "difficult", "need"]
    if any(s in message_lower for s in support_words):
        return "support"
    
    # Sarcastic detection (or if mood is snarky)
    sarcastic_words = ["sure", "whatever", "ok", "really", "lol", "lmao"]
    if mood == "snarky" or any(s in message_lower for s in sarcastic_words):
        return "sarcastic"
    
    return None


def get_smart_response(message: str, username: str, mood: str = "chill", emoji: str = None) -> Optional[str]:
    """
    Intelligently select and return a template-based response.
    
    Args:
        message: User's message
        username: User's username
        mood: Current bot mood
        emoji: Optional emoji to use
    
    Returns:
        Template response, or None if no suitable template
    """
    template_type = detect_template_type(message, mood)
    
    if not template_type:
        return None
    
    if emoji is None:
        # Select emoji based on mood
        mood_emojis = {
            "hype": "🔥",
            "chill": "😌",
            "snarky": "😏",
            "supportive": "💖"
        }
        emoji = mood_emojis.get(mood, "💬")
    
    return get_template(template_type, username, emoji)


# Example usage and testing
if __name__ == "__main__":
    print("=" * 60)
    print("MedlarTV Response Templates - Testing")
    print("=" * 60)
    
    test_cases = [
        ("hey", "User1", "chill"),
        ("I totally agree", "User2", "chill"),
        ("let's gooo!", "User3", "hype"),
        ("I'm feeling sad", "User4", "supportive"),
        ("sure buddy", "User5", "snarky")
    ]
    
    print("\n--- Smart Response Detection ---")
    for message, username, mood in test_cases:
        response = get_smart_response(message, username, mood)
        print(f"\nUser: {message}")
        print(f"Mood: {mood}")
        print(f"Bot: {response}")
    
    print("\n--- Template Variation Test (5 greetings) ---")
    for i in range(5):
        greeting = get_greeting(f"User{i+1}")
        print(f"{i+1}. {greeting}")
    
    print("\n--- Template Types ---")
    print("Greeting:", get_greeting("TestUser"))
    print("Agreement:", get_agreement("TestUser"))
    print("Hype:", get_hype("TestUser"))
    print("Support:", get_support("TestUser"))
    print("Sarcastic:", get_sarcastic("TestUser"))

# 🌍 Optional Llama-3 Refinement for Template Output
def refine_template_with_llama3(text: str, target_lang: str = "en") -> str:
    """
    Optionally refine a template output in another language using local Llama-3.
    Keeps tone natural and idiomatic for multilingual chats.
    """
    try:
        from MedlarTV.core.llm_brain import generate_response as llama_refine
        from MedlarTV.core.translation_command import _lang_human_name

        prompt = (
            f"Rewrite this short message so it sounds natural and idiomatic in "
            f"{_lang_human_name(target_lang)}. "
            f"Keep the same tone and emoji usage. Do not translate literally. "
            f"Message:\n{text}"
        )
        refined = llama_refine(prompt, username="Translator")
        if not refined or "Ollama model server offline" in refined:
            return text
        return refined.strip().strip('"').strip("“”")
    except Exception as e:
        print(f"[Templates] Llama refine error: {e}")
        return text
