"""
MedlarTV Translation Command
Translate text to different languages using !t command
Example: !t jp Hello, how are you?
"""

import os
import requests
from typing import Optional, Tuple

# Language code mappings
LANGUAGE_CODES = {
    # Short codes
    "jp": "ja",     # Japanese
    "kr": "ko",     # Korean
    "cn": "zh",     # Chinese
    "sp": "es",     # Spanish
    "fr": "fr",     # French
    "de": "de",     # German
    "pt": "pt",     # Portuguese
    "ru": "ru",     # Russian
    "it": "it",     # Italian
    "ar": "ar",     # Arabic
    
    # Full names (lowercase)
    "japanese": "ja",
    "korean": "ko",
    "chinese": "zh",
    "spanish": "es",
    "french": "fr",
    "german": "de",
    "portuguese": "pt",
    "russian": "ru",
    "italian": "it",
    "arabic": "ar",
    "english": "en",
    
    # Already correct codes
    "ja": "ja",
    "ko": "ko",
    "zh": "zh",
    "es": "es",
    "en": "en",
}

# Language flags
LANGUAGE_FLAGS = {
    "ja": "🇯🇵",
    "ko": "🇰🇷",
    "zh": "🇨🇳",
    "es": "🇪🇸",
    "fr": "🇫🇷",
    "de": "🇩🇪",
    "pt": "🇵🇹",
    "ru": "🇷🇺",
    "it": "🇮🇹",
    "ar": "🇸🇦",
    "en": "🇺🇸",
}


def normalize_language_code(lang_input: str) -> Optional[str]:
    """
    Convert user input to standard language code.
    
    Args:
        lang_input: User's language input (e.g., "jp", "japanese", "ja")
    
    Returns:
        Standard language code (e.g., "ja") or None if invalid
    """
    lang_lower = lang_input.lower().strip()
    return LANGUAGE_CODES.get(lang_lower)


def translate_with_mymemory(text: str, target_lang: str, source_lang: str = "en") -> Optional[str]:
    """
    Translate text using MyMemory free translation API.
    No API key required, but has rate limits.
    
    Args:
        text: Text to translate
        target_lang: Target language code
        source_lang: Source language code (default: auto-detect)
    
    Returns:
        Translated text or None if failed
    """
    try:
        # MyMemory API endpoint
        url = "https://api.mymemory.translated.net/get"
        
        params = {
            "q": text,
            "langpair": f"{source_lang}|{target_lang}",
        }
        
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("responseStatus") == 200:
                translation = data.get("responseData", {}).get("translatedText", "")
                return translation if translation else None
        
        return None
    
    except Exception as e:
        print(f"[Translation] MyMemory API error: {e}")
        return None


def translate_with_libretranslate(text: str, target_lang: str, source_lang: str = "en") -> Optional[str]:
    """
    Translate text using LibreTranslate (free, open source).
    Requires LibreTranslate server running or use public instance.
    
    Args:
        text: Text to translate
        target_lang: Target language code
        source_lang: Source language code (default: auto)
    
    Returns:
        Translated text or None if failed
    """
    try:
        # Public LibreTranslate instance (or set your own)
        url = os.getenv("LIBRETRANSLATE_URL", "https://libretranslate.com/translate")
        
        data = {
            "q": text,
            "source": source_lang,
            "target": target_lang,
            "format": "text"
        }
        
        response = requests.post(url, json=data, timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            return result.get("translatedText")
        
        return None
    
    except Exception as e:
        print(f"[Translation] LibreTranslate error: {e}")
        return None


def translate_text(text: str, target_lang: str, source_lang: str = "auto") -> Tuple[Optional[str], str]:
    """
    Translate text using available translation services.
    
    Args:
        text: Text to translate
        target_lang: Target language code
        source_lang: Source language code (default: auto-detect)
    
    Returns:
        Tuple of (translated_text, service_used)
    """
    # Normalize language code
    target_lang = normalize_language_code(target_lang)
    if not target_lang:
        return None, "invalid_lang"
    
    # Try MyMemory first (free, no API key)
    translation = translate_with_mymemory(text, target_lang, source_lang)
    if translation:
        return translation, "mymemory"
    
    # Try LibreTranslate as fallback
    translation = translate_with_libretranslate(text, target_lang, source_lang)
    if translation:
        return translation, "libretranslate"
    
    # All failed
    return None, "failed"


def handle_translate_command(args: str, username: str) -> str:
    """
    Handle the !t or !translate command.
    
    Format: !t <lang> <text to translate>
    Example: !t jp Hello, how are you?
    
    Args:
        args: Command arguments (lang + text)
        username: User who sent command
    
    Returns:
        Bot response with translation
    """
    # Parse arguments
    parts = args.strip().split(None, 1)
    
    if len(parts) < 2:
        return f"@{username} Usage: !t <lang> <text> | Example: !t jp Hello! | Supported: jp, kr, sp, fr, de, pt, cn"
    
    target_lang = parts[0]
    text_to_translate = parts[1]
    
    # Normalize language code
    lang_code = normalize_language_code(target_lang)
    
    if not lang_code:
        return f"@{username} ❌ Unknown language '{target_lang}'. Try: jp, kr, sp, fr, de, pt, cn"
    
    # Check text length (API limits)
    if len(text_to_translate) > 500:
        return f"@{username} ❌ Text too long! Max 500 characters."
    
    # Translate
    translation, service = translate_text(text_to_translate, lang_code)
    
    if translation:
        # Get language flag
        flag = LANGUAGE_FLAGS.get(lang_code, "🌐")
        
        # Format response
        return f"@{username} {flag} {translation}"
    else:
        if service == "invalid_lang":
            return f"@{username} ❌ Invalid language code. Try: jp, kr, sp, fr, de, pt"
        else:
            return f"@{username} ❌ Translation failed. Service temporarily unavailable."


def get_supported_languages_list() -> str:
    """Get a formatted list of supported languages for help text."""
    langs = [
        "jp/ja (🇯🇵 Japanese)",
        "kr/ko (🇰🇷 Korean)",
        "cn/zh (🇨🇳 Chinese)",
        "sp/es (🇪🇸 Spanish)",
        "fr (🇫🇷 French)",
        "de (🇩🇪 German)",
        "pt (🇵🇹 Portuguese)",
        "ru (🇷🇺 Russian)",
        "it (🇮🇹 Italian)"
    ]
    return ", ".join(langs)


# Test function
if __name__ == "__main__":
    print("=" * 60)
    print("MedlarTV Translation Command - Testing")
    print("=" * 60)
    
    test_cases = [
        ("jp", "Hello, how are you?"),
        ("kr", "Good morning!"),
        ("sp", "Thank you very much!"),
        ("fr", "I love this game!"),
        ("de", "See you later!"),
    ]
    
    for lang, text in test_cases:
        print(f"\n--- Translating to {lang.upper()} ---")
        print(f"Original: {text}")
        
        translation, service = translate_text(text, lang)
        
        if translation:
            flag = LANGUAGE_FLAGS.get(normalize_language_code(lang), "")
            print(f"Translated ({service}): {flag} {translation}")
        else:
            print(f"Translation failed ({service})")
    
    print("\n" + "=" * 60)
    print("Testing command handler")
    print("=" * 60)
    
    # Simulate command usage
    test_commands = [
        "jp Hello everyone!",
        "korean Thank you!",
        "es Good game!",
        "invalid test",  # Should fail
        "jp",  # Missing text
    ]
    
    for cmd in test_commands:
        print(f"\nCommand: !t {cmd}")
        response = handle_translate_command(cmd, "TestUser")
        print(f"Response: {response}")