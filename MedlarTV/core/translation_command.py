import logging
from typing import Tuple, Optional
from MedlarTV.core.translation import (
    normalize_lang, translate_text, supported_list_human
)

log = logging.getLogger("translation_cmd")

HELP = "!t <lang> <text> | Example: !t jp Hello!  use !tlang to see supported languages"

def _parse_args(raw: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse '<lang> <text...>' from the caller-provided raw string.
    We expect 'raw' to be everything AFTER the command token.
    """
    if not raw:
        return None, None
    raw = raw.strip()
    parts = raw.split(maxsplit=1)
    if len(parts) < 2:
        return None, None
    lang, text = parts[0].strip().lower(), parts[1].strip()
    return lang, text

def handle_t_command(raw_after_cmd: str, username: str) -> str:
    """
    raw_after_cmd: the substring after '!t' (or '!translate'/'!trans')
    """
    lang, text = _parse_args(raw_after_cmd)
    if not lang or not text:
        return HELP

    norm = normalize_lang(lang)
    if not norm:
        return f"@{username} Unsupported language '{lang}'. {HELP}"

    ok, result = translate_text(text, norm)
    if not ok:
        return f"@{username} {result}"

    # Keep it short and useful for Twitch
    return f"@{username} → [{norm}] {result}"

def handle_tlang_command() -> str:
    return supported_list_human()
