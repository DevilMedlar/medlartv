import re
import logging
from typing import Optional, Tuple
from langdetect import detect, DetectorFactory
import requests
import os

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
    print(f"[DEBUG translation] normalize_lang() called with code={code!r}")
    if not code:
        print("[DEBUG translation] normalize_lang(): code is None/empty → returning None")
        return None
    c = code.strip().lower()
    print(f"[DEBUG translation] normalize_lang(): normalized={c!r}")
    result = LANGUAGE_ALIASES.get(c, c if c in SUPPORTED else None)
    print(f"[DEBUG translation] normalize_lang(): returning {result!r}")
    return result


def detect_language(text: str) -> str:
    print(f"[DEBUG translation] detect_language() called with text={text!r}")
    try:
        stripped = re.sub(r"\W+", "", text or "")
        print(f"[DEBUG translation] detect_language(): stripped_for_detection={stripped!r}")

        if not text or len(stripped) < 2:
            print("[DEBUG translation] detect_language(): too short → returning 'en'")
            return "en"

        detected = detect(text)
        print(f"[DEBUG translation] detect_language(): detected={detected!r}")
        return detected

    except Exception as e:
        print(f"[DEBUG translation] detect_language() exception: {e}")
        return "en"


def get_multilingual_greeting(lang: str) -> str:
    print(f"[DEBUG translation] get_multilingual_greeting() called with lang={lang!r}")
    lang_norm = normalize_lang(lang) or "en"
    print(f"[DEBUG translation] get_multilingual_greeting(): normalized={lang_norm!r}")
    greeting = {
        "es": "¡Hola!", "ja": "やあ！", "ko": "안녕!", "zh": "嗨！",
        "fr": "Salut !", "de": "Hallo!", "pt": "Olá!", "ru": "Привет!", "it": "Ciao!", "en": "Hey!"
    }.get(lang_norm, "Hey!")
    print(f"[DEBUG translation] get_multilingual_greeting(): returning {greeting!r}")
    return greeting


def add_language_indicator(msg: str, target_lang: str) -> str:
    print(f"[DEBUG translation] add_language_indicator() called msg={msg!r} target_lang={target_lang!r}")
    flags = {
        "es":"🇪🇸","ja":"🇯🇵","ko":"🇰🇷","zh":"🇨🇳",
        "fr":"🇫🇷","de":"🇩🇪","pt":"🇵🇹","ru":"🇷🇺","it":"🇮🇹","en":"🇺🇸"
    }
    tl = normalize_lang(target_lang) or target_lang
    print(f"[DEBUG translation] add_language_indicator(): normalized target={tl!r}")
    flag = flags.get(tl, "🌐")
    print(f"[DEBUG translation] add_language_indicator(): flag={flag!r}")
    result = f"{msg} {flag}"
    print(f"[DEBUG translation] add_language_indicator(): returning {result!r}")
    return result


# --- Translation engine (LibreTranslate first, fallback none for simplicity) ---

LIBRE_URL = os.getenv("LIBRETRANSLATE_URL", "http://127.0.0.1:5000/translate")


def translate_text(text: str, target_lang: str) -> Tuple[bool, str]:
    """
    Returns (ok, translated_or_error).
    - Uses LibreTranslate running locally.
    - Auto-detects source.
    """
    print(f"[DEBUG translation] translate_text() called text={text!r} target_lang={target_lang!r}")

    tl = normalize_lang(target_lang)
    print(f"[DEBUG translation] translate_text(): normalized target={tl!r}")

    if not tl:
        msg = f"Unsupported language: {target_lang}"
        print(f"[DEBUG translation] translate_text(): {msg}")
        return False, msg

    try:
        payload = {"q": text, "source": "auto", "target": tl, "format": "text"}
        print(f"[DEBUG translation] translate_text(): POST {LIBRE_URL} with payload={payload}")

        resp = requests.post(
            LIBRE_URL,
            json=payload,
            timeout=7,
        )

        print(f"[DEBUG translation] translate_text(): resp.status_code={resp.status_code}")

        if resp.status_code == 200:
            out = resp.json().get("translatedText", "").strip()
            print(f"[DEBUG translation] translate_text(): translated={out!r}")
            if not out:
                return False, "Translation failed (empty result)."
            return True, out

        msg = f"Translation server error: {resp.status_code}"
        print(f"[DEBUG translation] translate_text(): {msg}")
        return False, msg

    except requests.exceptions.RequestException as e:
        msg = f"Translator offline: {e}"
        print(f"[DEBUG translation] translate_text(): exception={msg}")
        return False, msg


def supported_list_human() -> str:
    print("[DEBUG translation] supported_list_human() called")
    pretty = [
        "jp/ja (🇯🇵)", "kr/ko (🇰🇷)", "cn/zh (🇨🇳)", "sp/es (🇪🇸)",
        "fr (🇫🇷)", "de (🇩🇪)", "pt (🇵🇹)", "ru (🇷🇺)", "it (🇮🇹)"
    ]
    result = "Supported: " + ", ".join(pretty)
    print(f"[DEBUG translation] supported_list_human(): returning {result!r}")
    return result
