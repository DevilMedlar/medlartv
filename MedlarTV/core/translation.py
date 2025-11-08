import re
import logging
from typing import Optional, Tuple
from langdetect import detect, DetectorFactory
import requests

log = logging.getLogger("translation")

# langdetect determinism
DetectorFactory.seed = 42

# Common aliases viewers actually use
LANGUAGE_ALIASES = {
    # Spanish
    "sp": "es", "es": "es", "spanish": "es",
    # Japanese
    "jp": "ja", "ja": "ja", "japanese": "ja",
    # Korean
    "kr": "ko", "ko": "ko", "korean": "ko",
    # Chinese
    "cn": "zh", "zh": "zh", "chinese": "zh",
    "zh-cn": "zh", "cn-simp": "zh", "zt": "zh",
    # French / German / etc.
    "fr": "fr", "french": "fr",
    "de": "de", "german": "de",
    "pt": "pt", "portuguese": "pt",
    "ru": "ru", "russian": "ru",
    "it": "it", "italian": "it",
    "en": "en", "english": "en",
}

SUPPORTED = {"es","ja","ko","zh","fr","de","pt","ru","it","en"}

def normalize_lang(code: str) -> Optional[str]:
    if not code:
        return None
    c = code.strip().lower()
    return LANGUAGE_ALIASES.get(c, c if c in SUPPORTED else None)

def detect_language(text: str) -> str:
    try:
        # langdetect hates super-short tokens; add a guard
        if not text or len(re.sub(r"\W+", "", text)) < 2:
            return "en"
        return detect(text)
    except Exception:
        return "en"

def get_multilingual_greeting(lang: str) -> str:
    lang = normalize_lang(lang) or "en"
    return {
        "es": "¡Hola!", "ja": "やあ！", "ko": "안녕!", "zh": "嗨！",
        "fr": "Salut !", "de": "Hallo!", "pt": "Olá!", "ru": "Привет!", "it": "Ciao!", "en": "Hey!"
    }.get(lang, "Hey!")

def add_language_indicator(msg: str, target_lang: str) -> str:
    flags = {
        "es":"🇪🇸","ja":"🇯🇵","ko":"🇰🇷","zh":"🇨🇳",
        "fr":"🇫🇷","de":"🇩🇪","pt":"🇵🇹","ru":"🇷🇺","it":"🇮🇹","en":"🇺🇸"
    }
    tl = normalize_lang(target_lang) or target_lang
    flag = flags.get(tl, "🌐")
    return f"{msg} {flag}"

# --- Translation engine (LibreTranslate first, fallback none for simplicity) ---

LIBRE_URL = "http://127.0.0.1:5000/translate"

def translate_text(text: str, target_lang: str) -> Tuple[bool, str]:
    """
    Returns (ok, translated_or_error).
    - Uses LibreTranslate running locally.
    - Auto-detects source.
    """
    tl = normalize_lang(target_lang)
    if not tl:
        return False, f"Unsupported language: {target_lang}"

    try:
        resp = requests.post(
            LIBRE_URL,
            json={"q": text, "source": "auto", "target": tl, "format": "text"},
            timeout=7,
        )
        if resp.status_code == 200:
            out = resp.json().get("translatedText", "").strip()
            if not out:
                return False, "Translation failed (empty result)."
            return True, out
        return False, f"Translation server error: {resp.status_code}"
    except requests.exceptions.RequestException as e:
        return False, f"Translator offline: {e}"

def supported_list_human() -> str:
    pretty = [
        "jp/ja (🇯🇵)", "kr/ko (🇰🇷)", "cn/zh (🇨🇳)", "sp/es (🇪🇸)",
        "fr (🇫🇷)", "de (🇩🇪)", "pt (🇵🇹)", "ru (🇷🇺)", "it (🇮🇹)"
    ]
    return "Supported: " + ", ".join(pretty)
