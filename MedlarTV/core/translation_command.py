"""
MedlarTV Translation Command
Translate text to different languages using !t command
Example: !t jp Hello, how are you?

Upgrade: Llama-3 refinement (local, free)
After a raw translation (MyMemory / LibreTranslate), optionally refine phrasing
with the local Llama-3 model for natural, idiomatic output.
"""

import os
import requests
from typing import Optional, Tuple
from MedlarTV.core.llm_brain import generate_response as llama_refine  # local Llama-3 refiner

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


# -------------------------------
# 🔧 Helper functions
# -------------------------------
def normalize_language_code(lang_input: str) -> Optional[str]:
    """Convert user input to standard language code."""
    lang_lower = lang_input.lower().strip()
    return LANGUAGE_CODES.get(lang_lower)


def _should_refine_with_llama3() -> bool:
    """Gate for refinement step (env override: LLAMA_REFINE=true/false)."""
    return os.getenv("LLAMA_REFINE", "true").lower() == "true"


def _lang_human_name(code: str) -> str:
    """Human-friendly language name for prompt clarity."""
    mapping = {
        "ja": "Japanese", "ko": "Korean", "zh": "Chinese", "es": "Spanish",
        "fr": "French", "de": "German", "pt": "Portuguese", "ru": "Russian",
        "it": "Italian", "ar": "Arabic", "en": "English"
    }
    return mapping.get(code, code)


def _refine_with_llama3(raw_translation: str, target_lang: str) -> str:
    """
    Post-process raw translation with local Llama-3 to improve naturalness.
    Falls back to raw text if Ollama is offline or returns a sentinel.
    """
    try:
        prompt = (
            f"Refine this translation so it sounds natural and idiomatic in "
            f"{_lang_human_name(target_lang)}. Keep the meaning identical. "
            f"Do not add explanations, quotes, or extra text. "
            f"Output only the rewritten sentence.\n\n"
            f"Translation:\n{raw_translation}"
        )
        refined = llama_refine(prompt, username="Translator")
        if not refined or "Ollama model server offline" in refined:
            return raw_translation
        return refined.strip().strip('"').strip("“”")
    except Exception:
        return raw_translation


# -------------------------------
# 🌐 Translation providers
# -------------------------------
def translate_with_mymemory(text: str, target_lang: str, source_lang: str = "en") -> Optional[str]:
    """Translate text using MyMemory free translation API."""
    try:
        url = "https://api.mymemory.translated.net/get"
        params = {"q": text, "langpair": f"{source_lang}|{target_lang}"}
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
    """Translate text using LibreTranslate (free, open source)."""
    try:
        url = os.getenv("LIBRETRANSLATE_URL", "https://libretranslate.com/translate")
        data = {"q": text, "source": source_lang, "target": target_lang, "format": "text"}
        response = requests.post(url, json=data, timeout=5)
        if response.status_code == 200:
            result = response.json()
            return result.get("translatedText")
        return None

    except Exception as e:
        print(f"[Translation] LibreTranslate error: {e}")
        return None


# -------------------------------
# 🧠 Unified translation flow
# -------------------------------
def translate_text(text: str, target_lang: str, source_lang: str = "auto") -> Tuple[Optional[str], str]:
    """Translate text using available services, refine optionally with Llama-3."""
    target_lang = normalize_language_code(target_lang)
    if not target_lang:
        return None, "invalid_lang"

    # Try MyMemory first
    translation = translate_with_mymemory(text, target_lang, source_lang)
    if translation:
        if _should_refine_with_llama3():
            translation = _refine_with_llama3(translation, target_lang)
            return translation, "llama3_refined(mymemory)"
        return translation, "mymemory"

    # Try LibreTranslate as fallback
    translation = translate_with_libretranslate(text, target_lang, source_lang)
    if translation:
        if _should_refine_with_llama3():
            translation = _refine_with_llama3(translation, target_lang)
            return translation, "llama3_refined(libretranslate)"
        return translation, "libretranslate"

    # All failed
    return None, "failed"


# -------------------------------
# 💬 Command handler
# -------------------------------
def handle_translate_command(args: str, username: str) -> str:
    """
    Handle the !t or !translate command.
    Format: !t <lang> <text to translate>
    """
    parts = args.strip().split(None, 1)
    if len(parts) < 2:
        return f"@{username} Usage: !t <lang> <text> | Example: !t jp Hello! | Supported: jp, kr, sp, fr, de, pt, cn"

    target_lang = parts[0]
    text_to_translate = parts[1]
    lang_code = normalize_language_code(target_lang)

    if not lang_code:
        return f"@{username} ❌ Unknown language '{target_lang}'. Try: jp, kr, sp, fr, de, pt, cn"

    if len(text_to_translate) > 500:
        return f"@{username} ❌ Text too long! Max 500 characters."

    translation, service = translate_text(text_to_translate, lang_code)

    if translation:
        flag = LANGUAGE_FLAGS.get(lang_code, "🌐")
        # Add a subtle tag if Llama-3 refinement was used
        refined_note = " ✨" if "llama3_refined" in service else ""
        return f"@{username} {flag} {translation}{refined_note}"
    else:
        if service == "invalid_lang":
            return f"@{username} ❌ Invalid language code. Try: jp, kr, sp, fr, de, pt"
        else:
            return f"@{username} ❌ Translation failed. Service temporarily unavailable."


# -------------------------------
# 📜 Supported languages helper
# -------------------------------
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
        "it (🇮🇹 Italian)",
    ]
    return ", ".join(langs)


# -------------------------------
# 🧪 CLI Test
# -------------------------------
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
    test_commands = [
        "jp Hello everyone!",
        "korean Thank you!",
        "es Good game!",
        "invalid test",
        "jp",
    ]
    for cmd in test_commands:
        print(f"\nCommand: !t {cmd}")
        response = handle_translate_command(cmd, "TestUser")
        print(f"Response: {response}")
