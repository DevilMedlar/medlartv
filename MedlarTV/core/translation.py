"""
MedlarTV Translation Module
Multi-language support with automatic detection
"""

import os
import re
from typing import Optional, Dict
from pathlib import Path
import yaml

# Check if translation is enabled
ENABLE_TRANSLATION = os.getenv("ENABLE_TRANSLATION", "true").lower() == "true"
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")
SUPPORTED_LANGUAGES = os.getenv("SUPPORTED_LANGUAGES", "en,es,fr,de,ja,ko,pt").split(",")

def load_translations() -> Dict:
    """Load translations from personality.yaml"""
    config_path = Path("MedlarTV/config/personality.yaml")
    
    if not config_path.exists():
        return {}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
        
        personality = config.get("personality", {})
        return personality.get("translations", {})
    except Exception as e:
        print(f"[Translation] Error loading translations: {e}")
        return {}

def detect_language(text: str) -> str:
    """
    Simple language detection based on character sets.
    For production, consider using langdetect library.
    """
    if not ENABLE_TRANSLATION:
        return DEFAULT_LANGUAGE
    
    # Japanese characters
    if re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', text):
        return "ja"
    
    # Korean characters
    if re.search(r'[\uAC00-\uD7A3]', text):
        return "ko"
    
    # Chinese characters (simplified/traditional)
    if re.search(r'[\u4E00-\u9FFF]', text):
        return "zh"
    
    # Cyrillic (Russian, etc.)
    if re.search(r'[\u0400-\u04FF]', text):
        return "ru"
    
    # Spanish indicators
    spanish_words = ['hola', 'gracias', 'por favor', 'buenos', 'días', 'sí', 'no', 'qué']
    if any(word in text.lower() for word in spanish_words):
        return "es"
    
    # French indicators
    french_words = ['bonjour', 'merci', 'oui', 'non', 'ça', 'très', 'être']
    if any(word in text.lower() for word in french_words):
        return "fr"
    
    # German indicators
    german_words = ['hallo', 'danke', 'bitte', 'ja', 'nein', 'wie', 'ist', 'der', 'die', 'das']
    if any(word in text.lower() for word in german_words):
        return "de"
    
    # Portuguese indicators
    portuguese_words = ['olá', 'obrigado', 'por favor', 'sim', 'não', 'está']
    if any(word in text.lower() for word in portuguese_words):
        return "pt"
    
    # Default to English
    return DEFAULT_LANGUAGE

def translate_phrase(phrase_key: str, target_language: str = None) -> str:
    """
    Translate a common phrase to target language.
    
    Args:
        phrase_key: Key for the phrase (e.g., 'greeting', 'thanks', 'bye')
        target_language: Target language code (e.g., 'es', 'fr', 'ja')
    
    Returns:
        Translated phrase, or original if translation not available
    """
    if not ENABLE_TRANSLATION:
        return phrase_key
    
    if target_language is None:
        target_language = DEFAULT_LANGUAGE
    
    if target_language not in SUPPORTED_LANGUAGES:
        target_language = DEFAULT_LANGUAGE
    
    translations = load_translations()
    
    if phrase_key not in translations:
        return phrase_key
    
    phrase_translations = translations[phrase_key]
    
    if target_language not in phrase_translations:
        return phrase_translations.get(DEFAULT_LANGUAGE, phrase_key)
    
    return phrase_translations[target_language]

def translate_message(text: str, target_language: str = None) -> str:
    """
    Translate a full message to target language.
    Note: This is a placeholder. For real translation, integrate an API like:
    - Google Translate API
    - DeepL API
    - LibreTranslate (free/open source)
    """
    if not ENABLE_TRANSLATION:
        return text
    
    if target_language is None:
        target_language = DEFAULT_LANGUAGE
    
    # For now, just return original text
    # In production, call translation API here
    print(f"[Translation] Would translate '{text}' to {target_language}")
    return text

def add_language_indicator(text: str, language: str) -> str:
    """Add a small language flag emoji to responses"""
    if not ENABLE_TRANSLATION or language == DEFAULT_LANGUAGE:
        return text
    
    flags = {
        "es": "🇪🇸",
        "fr": "🇫🇷",
        "de": "🇩🇪",
        "ja": "🇯🇵",
        "ko": "🇰🇷",
        "pt": "🇵🇹",
        "ru": "🇷🇺",
        "zh": "🇨🇳"
    }
    
    flag = flags.get(language, "")
    if flag:
        return f"{flag} {text}"
    return text

def get_multilingual_greeting(username: str, language: str = None) -> str:
    """Get a greeting in the user's language"""
    if language is None:
        language = DEFAULT_LANGUAGE
    
    greeting = translate_phrase("greeting", language)
    return f"{greeting} {username}!"

def get_multilingual_thanks(language: str = None) -> str:
    """Get a thank you message in the user's language"""
    if language is None:
        language = DEFAULT_LANGUAGE
    
    return translate_phrase("thanks", language)

def llama_refine_static_translation(raw_text: str, target_lang: str) -> str:
    """
    Optionally refine a short static translation (like greetings or UI phrases)
    using local Llama-3 for natural tone and phrasing.
    100% free and offline.
    """
    try:
        from MedlarTV.core.llm_brain import generate_response as llama_refine
        from MedlarTV.core.translation_command import _lang_human_name

        prompt = (
            f"Make this short system message sound natural and idiomatic in "
            f"{_lang_human_name(target_lang)}. Keep the same meaning. "
            f"Do not add explanations or extra text.\n\nMessage:\n{raw_text}"
        )
        refined = llama_refine(prompt, username="System")
        if not refined or "Ollama model server offline" in refined:
            return raw_text
        return refined.strip().strip('"').strip("“”")
    except Exception as e:
        print(f"[Translation] Llama refine error: {e}")
        return raw_text

# Example usage and testing
if __name__ == "__main__":
    print("=" * 60)
    print("MedlarTV Translation Module - Testing")
    print("=" * 60)
    
    test_messages = [
        "Hello, how are you?",
        "Hola, ¿cómo estás?",
        "Bonjour, comment allez-vous?",
        "こんにちは、元気ですか？",
        "안녕하세요, 어떻게 지내세요?",
        "Olá, como vai?"
    ]
    
    print("\n--- Language Detection ---")
    for msg in test_messages:
        lang = detect_language(msg)
        print(f"{lang}: {msg}")
    
    print("\n--- Phrase Translation ---")
    for lang in SUPPORTED_LANGUAGES:
        greeting = translate_phrase("greeting", lang)
        thanks = translate_phrase("thanks", lang)
        print(f"{lang}: {greeting} / {thanks}")
    
    print("\n--- Multilingual Greetings ---")
    for lang in SUPPORTED_LANGUAGES:
        greeting = get_multilingual_greeting("User123", lang)
        print(f"{lang}: {greeting}")