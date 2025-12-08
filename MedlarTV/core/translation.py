import re
import logging
from typing import Optional, Tuple
from langdetect import detect, DetectorFactory
import requests
import os
DEBUG = os.getenv("MEDLARTV_DEBUG", "false").lower() == "true"

log = logging.getLogger("translation")

# langdetect determinism
DetectorFactory.seed = 42

# Common aliases viewers actually use
LANGUAGE_ALIASES = {
    "sp": "es", "es": "es", "spanish": "es",
    "jp": "ja", "ja": "ja", "japanese": "ja",
    "kr": "ko", "ko": "ko", "korean": "ko",
    "cn": "zh", "zh": "zh", "chinese": "zh",
    "zh-cn": "zh", "cn-simp": "zh", "zt": "zh-hant",
    "fr": "fr", "french": "fr",
    "de": "de", "german": "de",
    "pt": "pt", "portuguese": "pt", "pt-br": "pt-br", "pb": "pt-br",
    "ru": "ru", "russian": "ru",
    "it": "it", "italian": "it",
    "en": "en", "english": "en",
    "tl": "tl", "tagalog": "tl", "filipino": "tl",
}

_SUPPORTED_CACHE = None


def _base_url() -> str:
    u = os.getenv("LIBRETRANSLATE_URL", "http://127.0.0.1:5000/translate")
    return u[:-10] if u.endswith("/translate") else u

def _lt_languages() -> set[str]:
    try:
        r = requests.get(f"{_base_url()}/languages", timeout=4)
        if r.status_code == 200:
            codes = set()
            for item in r.json():
                c = str(item.get("code", "")).strip().lower()
                if c:
                    codes.add(c)
            return codes
    except Exception:
        return set()
    return set()

def _argos_languages() -> set[str]:
    try:
        from argostranslate import translate as _t
        return set([str(l.code).strip().lower() for l in _t.get_installed_languages() if getattr(l, "code", None)])
    except Exception:
        return set()

def _get_supported() -> set[str]:
    global _SUPPORTED_CACHE
    if _SUPPORTED_CACHE is not None:
        return _SUPPORTED_CACHE
    lt = _lt_languages()
    ar = _argos_languages()
    s = set()
    s.update(lt)
    s.update(ar)
    if not s:
        s = {"en","es","fr","de","pt","it","ru","ja","ko","zh"}
    _SUPPORTED_CACHE = s
    return s

def normalize_lang(code: str) -> Optional[str]:
    if DEBUG:
        print(f"[DEBUG translation] normalize_lang() called with code={code!r}")
    if not code:
        if DEBUG:
            print("[DEBUG translation] normalize_lang(): code is None/empty → returning None")
        return None
    c = code.strip().lower()
    if DEBUG:
        print(f"[DEBUG translation] normalize_lang(): normalized={c!r}")
    s = _get_supported()
    alias = LANGUAGE_ALIASES.get(c, c)
    if alias == "zh":
        if "zh-hans" in s:
            alias = "zh-hans"
        elif "zh" in s:
            alias = "zh"
        elif "zh-hant" in s:
            alias = "zh-hant"
    if alias == "pt-br" and "pt-br" not in s and "pb" in s:
        alias = "pb"
    if alias == "pb" and "pb" not in s and "pt-br" in s:
        alias = "pt-br"
    result = alias if alias in s else None
    if DEBUG:
        print(f"[DEBUG translation] normalize_lang(): returning {result!r}")
    return result


def detect_language(text: str) -> str:
    if DEBUG:
        print(f"[DEBUG translation] detect_language() called with text={text!r}")
    try:
        stripped = re.sub(r"\W+", "", text or "")
        if DEBUG:
            print(f"[DEBUG translation] detect_language(): stripped_for_detection={stripped!r}")
        if not text or len(stripped) < 3:
            if DEBUG:
                print("[DEBUG translation] detect_language(): too short → returning 'en'")
            return "en"
        try:
            resp = requests.post(f"{_base_url()}/detect", json={"q": text}, timeout=5)
            if DEBUG:
                print(f"[DEBUG translation] detect_language(): LT detect status={resp.status_code}")
            if resp.status_code == 200:
                arr = resp.json()
                if isinstance(arr, list) and arr:
                    lang = str(arr[0].get("language", "")).strip().lower()
                    if DEBUG:
                        print(f"[DEBUG translation] detect_language(): LT detected={lang!r}")
                    if lang:
                        return lang
        except Exception as e:
            if DEBUG:
                print(f"[DEBUG translation] detect_language(): LT detect failed: {e}")
        detected = detect(text)
        if DEBUG:
            print(f"[DEBUG translation] detect_language(): fallback detected={detected!r}")
        return detected
    except Exception as e:
        if DEBUG:
            print(f"[DEBUG translation] detect_language() exception: {e}")
        return "en"


def get_multilingual_greeting(lang: str) -> str:
    if DEBUG:
        print(f"[DEBUG translation] get_multilingual_greeting() called with lang={lang!r}")
    lang_norm = normalize_lang(lang) or "en"
    if DEBUG:
        print(f"[DEBUG translation] get_multilingual_greeting(): normalized={lang_norm!r}")
    greeting = {
        "es": "¡Hola!", "ja": "やあ！", "ko": "안녕!", "zh": "嗨！",
        "fr": "Salut !", "de": "Hallo!", "pt": "Olá!", "ru": "Привет!", "it": "Ciao!", "en": "Hey!"
    }.get(lang_norm, "Hey!")
    if DEBUG:
        print(f"[DEBUG translation] get_multilingual_greeting(): returning {greeting!r}")
    return greeting


def add_language_indicator(msg: str, target_lang: str) -> str:
    if DEBUG:
        print(f"[DEBUG translation] add_language_indicator() called msg={msg!r} target_lang={target_lang!r}")
    flags = {
        "es":"🇪🇸","ja":"🇯🇵","ko":"🇰🇷","zh":"🇨🇳",
        "zh-hans":"🇨🇳","zh-hant":"🇹🇼",
        "fr":"🇫🇷","de":"🇩🇪","pt":"🇵🇹","pt-br":"🇧🇷","pb":"🇧🇷",
        "ru":"🇷🇺","it":"🇮🇹","en":"🇺🇸","tl":"🇵🇭"
    }
    tl = normalize_lang(target_lang) or target_lang
    if DEBUG:
        print(f"[DEBUG translation] add_language_indicator(): normalized target={tl!r}")
    flag = flags.get(tl, "🌐")
    if DEBUG:
        print(f"[DEBUG translation] add_language_indicator(): flag={flag!r}")
    result = f"{msg} {flag}"
    if DEBUG:
        print(f"[DEBUG translation] add_language_indicator(): returning {result!r}")
    return result


# --- Translation engine (LibreTranslate first, fallback none for simplicity) ---

LIBRE_URL = os.getenv("LIBRETRANSLATE_URL", "http://127.0.0.1:5000/translate")


def translate_text(text: str, target_lang: str, source_lang: Optional[str] = None) -> Tuple[bool, str]:
    """
    Returns (ok, translated_or_error).
    - Uses LibreTranslate running locally.
    - Auto-detects source.
    """
    if DEBUG:
        print(f"[DEBUG translation] translate_text() called text={text!r} target_lang={target_lang!r} source_lang={source_lang!r}")

    tl = normalize_lang(target_lang)
    if DEBUG:
        print(f"[DEBUG translation] translate_text(): normalized target={tl!r}")

    if not tl:
        msg = f"Unsupported language: {target_lang}"
        if DEBUG:
            print(f"[DEBUG translation] translate_text(): {msg}")
        return False, msg

    sl = normalize_lang(source_lang) if source_lang else None
    try:
        payload = {"q": text, "source": sl or "auto", "target": tl, "format": "text"}
        if DEBUG:
            print(f"[DEBUG translation] translate_text(): POST {LIBRE_URL} with payload={payload}")

        resp = requests.post(
            LIBRE_URL,
            json=payload,
            timeout=7,
        )

        if DEBUG:
            print(f"[DEBUG translation] translate_text(): resp.status_code={resp.status_code}")

        if resp.status_code == 200:
            out = resp.json().get("translatedText", "").strip()
            if DEBUG:
                print(f"[DEBUG translation] translate_text(): translated={out!r}")
            if not out:
                return False, "Translation failed (empty result)."
            return True, out

        msg = f"Translation server error: {resp.status_code}"
        if DEBUG:
            print(f"[DEBUG translation] translate_text(): {msg}")
        return False, msg

    except requests.exceptions.RequestException as e:
        msg = f"Translator offline: {e}"
        if DEBUG:
            print(f"[DEBUG translation] translate_text(): exception={msg}")
        return False, msg


def supported_list_human() -> str:
    if DEBUG:
        print("[DEBUG translation] supported_list_human() called")
    s = sorted(list(_get_supported()))
    result = "Supported: " + ", ".join(s)
    if DEBUG:
        print(f"[DEBUG translation] supported_list_human(): returning {result!r}")
    return result
 
