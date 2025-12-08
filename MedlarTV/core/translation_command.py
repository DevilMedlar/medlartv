import logging
import re
from typing import Tuple, Optional
from MedlarTV.core.translation import (
    normalize_lang, translate_text, supported_list_human, detect_language
)

log = logging.getLogger("translation_cmd")

HELP = "!t <target> <text> | Optional source override: !t <target> <source>: <text> | Example: !t en tl: mahal kita"


def _parse_args(raw: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parse '<target> [<source>:] <text...>' from the caller-provided raw string.
    Returns (target, source_override, text)
    """
    print(f"[DEBUG translation_cmd] _parse_args() called with raw={raw!r}")

    if not raw:
        print("[DEBUG translation_cmd] _parse_args(): raw empty → returning (None,None,None)")
        return None, None, None

    raw = raw.strip()
    print(f"[DEBUG translation_cmd] _parse_args(): stripped={raw!r}")

    parts = raw.split(maxsplit=1)
    print(f"[DEBUG translation_cmd] _parse_args(): parts={parts!r}")

    if len(parts) < 2:
        print("[DEBUG translation_cmd] _parse_args(): fewer than 2 parts → returning (None,None,None)")
        return None, None, None

    target, text = parts[0].strip().lower(), parts[1].strip()
    source = None
    m = re.match(r"^([a-zA-Z]{2,5}(?:-[a-zA-Z]{2,5})?):\s*(.+)$", text)
    if m:
        source = m.group(1).strip().lower()
        text = m.group(2)
    print(f"[DEBUG translation_cmd] _parse_args(): target={target!r} source={source!r} text={text!r}")

    return target, source, text


def handle_t_command(raw_after_cmd: str, username: str) -> str:
    """
    raw_after_cmd: the substring after '!t' (or '!translate'/'!trans')
    """
    print(f"[DEBUG translation_cmd] handle_t_command() raw_after_cmd={raw_after_cmd!r} username={username!r}")

    target, src_override, text = _parse_args(raw_after_cmd)
    print(f"[DEBUG translation_cmd] handle_t_command(): parsed target={target!r} src_override={src_override!r} text={text!r}")

    if not target or not text:
        print("[DEBUG translation_cmd] handle_t_command(): missing target/text → returning HELP")
        return HELP

    norm_tgt = normalize_lang(target)
    print(f"[DEBUG translation_cmd] handle_t_command(): normalized target={norm_tgt!r}")

    if not norm_tgt:
        msg = f"@{username} Unsupported language '{target}'. {HELP}"
        print(f"[DEBUG translation_cmd] handle_t_command(): unsupported → {msg!r}")
        return msg

    src = normalize_lang(src_override) if src_override else detect_language(text)
    ok, result = translate_text(text, norm_tgt, src)
    print(f"[DEBUG translation_cmd] handle_t_command(): translate returned ok={ok} result={result!r}")

    if not ok:
        msg = f"@{username} {result}"
        print(f"[DEBUG translation_cmd] handle_t_command(): translation failed → {msg!r}")
        return msg

    src_norm = normalize_lang(src) or src
    final = f"@{username} → [{norm_tgt}] {result} (from [{src_norm}] to [{norm_tgt}])"
    print(f"[DEBUG translation_cmd] handle_t_command(): returning {final!r}")
    return final


def handle_tlang_command() -> str:
    print("[DEBUG translation_cmd] handle_tlang_command() called")
    result = supported_list_human()
    print(f"[DEBUG translation_cmd] handle_tlang_command(): returning {result!r}")
    return result
