import logging
from typing import Tuple, Optional
from MedlarTV.core.translation import (
    normalize_lang, translate_text, supported_list_human, detect_language
)

log = logging.getLogger("translation_cmd")

HELP = "!t <lang> <text> | Example: !t jp Hello!  use !tlang to see supported languages"


def _parse_args(raw: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse '<lang> <text...>' from the caller-provided raw string.
    We expect 'raw' to be everything AFTER the command token.
    """
    print(f"[DEBUG translation_cmd] _parse_args() called with raw={raw!r}")

    if not raw:
        print("[DEBUG translation_cmd] _parse_args(): raw empty → returning (None,None)")
        return None, None

    raw = raw.strip()
    print(f"[DEBUG translation_cmd] _parse_args(): stripped={raw!r}")

    parts = raw.split(maxsplit=1)
    print(f"[DEBUG translation_cmd] _parse_args(): parts={parts!r}")

    if len(parts) < 2:
        print("[DEBUG translation_cmd] _parse_args(): fewer than 2 parts → returning (None,None)")
        return None, None

    lang, text = parts[0].strip().lower(), parts[1].strip()

    print(f"[DEBUG translation_cmd] _parse_args(): lang={lang!r} text={text!r}")

    return lang, text


def handle_t_command(raw_after_cmd: str, username: str) -> str:
    """
    raw_after_cmd: the substring after '!t' (or '!translate'/'!trans')
    """
    print(f"[DEBUG translation_cmd] handle_t_command() raw_after_cmd={raw_after_cmd!r} username={username!r}")

    lang, text = _parse_args(raw_after_cmd)
    print(f"[DEBUG translation_cmd] handle_t_command(): parsed lang={lang!r} text={text!r}")

    if not lang or not text:
        print("[DEBUG translation_cmd] handle_t_command(): missing lang/text → returning HELP")
        return HELP

    norm = normalize_lang(lang)
    print(f"[DEBUG translation_cmd] handle_t_command(): normalized lang={norm!r}")

    if not norm:
        msg = f"@{username} Unsupported language '{lang}'. {HELP}"
        print(f"[DEBUG translation_cmd] handle_t_command(): unsupported → {msg!r}")
        return msg

    src = detect_language(text)
    ok, result = translate_text(text, norm)
    print(f"[DEBUG translation_cmd] handle_t_command(): translate returned ok={ok} result={result!r}")

    if not ok:
        msg = f"@{username} {result}"
        print(f"[DEBUG translation_cmd] handle_t_command(): translation failed → {msg!r}")
        return msg

    src_norm = normalize_lang(src) or src
    final = f"@{username} → [{norm}] {result} (from [{src_norm}] to [{norm}])"
    print(f"[DEBUG translation_cmd] handle_t_command(): returning {final!r}")
    return final


def handle_tlang_command() -> str:
    print("[DEBUG translation_cmd] handle_tlang_command() called")
    result = supported_list_human()
    print(f"[DEBUG translation_cmd] handle_tlang_command(): returning {result!r}")
    return result
