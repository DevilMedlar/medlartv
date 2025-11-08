# MedlarTV / translation.py
from __future__ import annotations
import threading
from typing import Optional, Tuple, Dict, Set, List

try:
    import argostranslate.package as argo_pkg
    import argostranslate.translate as argo_tx
except Exception as e:
    argo_pkg = None
    argo_tx = None
    _import_error = e
else:
    _import_error = None

# Optional auto-detect (nice-to-have). If not installed, we’ll fallback to 'en'.
try:
    from langdetect import detect as _detect_lang  # provided by your libretranslate deps, but works standalone too
except Exception:
    _detect_lang = None

# Normalize user aliases -> Argos codes
# Argos typically uses ISO like: en, es, fr, de, it, pt, ru, ja, ko, zh
LANG_ALIASES: Dict[str, str] = {
    # English and friends
    "en": "en",

    # Japanese
    "jp": "ja", "ja": "ja",

    # Korean
    "kr": "ko", "ko": "ko",

    # Chinese (treat cn/zh/zh-hans as zh for Argos)
    "cn": "zh", "zh": "zh", "zh-hans": "zh", "zh_hans": "zh",

    # Spanish
    "sp": "es", "es": "es",

    # French, German, Portuguese, Russian, Italian
    "fr": "fr",
    "de": "de",
    "pt": "pt",
    "ru": "ru",
    "it": "it",
}

# Emoji flags for a nicer response
LANG_FLAGS: Dict[str, str] = {
    "en": "🇺🇸",
    "es": "🇪🇸",
    "fr": "🇫🇷",
    "de": "🇩🇪",
    "pt": "🇵🇹",
    "ru": "🇷🇺",
    "it": "🇮🇹",
    "ja": "🇯🇵",
    "ko": "🇰🇷",
    "zh": "🇨🇳",
}

# Lock to serialize first-time installs
_install_lock = threading.Lock()


class TranslationError(Exception):
    pass


def _require_argos():
    if _import_error:
        raise TranslationError(
            "Argos Translate is not available in this environment "
            f"(import error: {_import_error}). Make sure `argostranslate==1.9.6` is installed."
        )
    if argo_pkg is None or argo_tx is None:
        raise TranslationError("Argos Translate modules not loaded.")


def normalize_lang(code_or_alias: str) -> Optional[str]:
    if not code_or_alias:
        return None
    c = code_or_alias.strip().lower()
    return LANG_ALIASES.get(c, c)  # allow direct ISO if already correct


def _list_installed_pairs() -> Set[Tuple[str, str]]:
    """Return a set of (from, to) codes that are currently installed."""
    pairs = set()
    for from_lang in argo_tx.get_installed_languages():
        for to_lang in from_lang.translations_to:
            pairs.add((from_lang.code, to_lang.code))
    return pairs


def _get_language_obj(code: str):
    """Return Argos Language object for code, or None."""
    for lang in argo_tx.get_installed_languages():
        if lang.code == code:
            return lang
    return None


def _ensure_pair_installed(src: str, tgt: str) -> None:
    """Install translation package for (src -> tgt) if missing."""
    installed = _list_installed_pairs()
    if (src, tgt) in installed:
        return

    with _install_lock:
        # Double-check inside lock
        installed = _list_installed_pairs()
        if (src, tgt) in installed:
            return

        # Find package
        packages = argo_pkg.get_available_packages()
        match = next((p for p in packages if p.from_code == src and p.to_code == tgt), None)
        if not match:
            raise TranslationError(f"No Argos translation package found for {src} → {tgt}.")

        # Download+Install
        try:
            path = match.download()
            argo_pkg.install_from_path(path)
        except Exception as e:
            raise TranslationError(f"Failed to install {src}→{tgt} package: {e}")


def _detect(text: str, default: str = "en") -> str:
    if not _detect_lang:
        return default
    try:
        code = _detect_lang(text)
        # Map langdetect outputs through our aliases if needed
        return normalize_lang(code) or default
    except Exception:
        return default


def translate_text(
    text: str,
    target: str,
    source: Optional[str] = None,
    autodetect_source: bool = True
) -> Tuple[str, str, str]:
    """
    Translate text with Argos.
    Returns: (translated_text, src_code, tgt_code)
    Raises: TranslationError
    """
    _require_argos()

    if not text or not text.strip():
        raise TranslationError("Nothing to translate.")

    tgt = normalize_lang(target)
    if not tgt:
        raise TranslationError(f"Unknown target language: {target}")

    src = normalize_lang(source) if source else None
    if not src and autodetect_source:
        src = _detect(text, default="en")
    if not src:
        src = "en"

    # Ensure we have a package; download on first use if missing
    _ensure_pair_installed(src, tgt)

    # Resolve language objects
    from_lang = _get_language_obj(src)
    to_lang = _get_language_obj(tgt)
    if not from_lang or not to_lang:
        raise TranslationError("Language models not available after install attempt.")

    try:
        translator = from_lang.get_translation(to_lang)
        out = translator.translate(text)
        return out, src, tgt
    except Exception as e:
        raise TranslationError(f"Translation failed: {e}")


def supported_aliases_message() -> str:
    return (
        "Supported: jp/ja (🇯🇵), kr/ko (🇰🇷), cn/zh (🇨🇳), "
        "sp/es (🇪🇸), fr (🇫🇷), de (🇩🇪), pt (🇵🇹), ru (🇷🇺), it (🇮🇹)"
    )


def flag_for(code: str) -> str:
    return LANG_FLAGS.get(code, "")
