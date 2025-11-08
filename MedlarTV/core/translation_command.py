# MedlarTV / translation_command.py
from __future__ import annotations
from typing import Dict, Any

from . import translation as tx

# If you have a shared “send/emit” function, import it here.
# from .twitch_events import send_chat_message  # example

HELP_LINE = "!t <lang> <text> | Example: !t jp Hello!  use !tlang to see supported languages"

def _parse_args(raw: str):
    """
    Parse "!t <lang> <text...>"
    Returns (lang_code_or_alias, text) or (None, None) if invalid.
    """
    if not raw:
        return None, None
    parts = raw.strip().split(None, 1)
    if len(parts) < 2:
        return None, None
    lang, text = parts[0].strip(), parts[1].strip()
    return lang, text


def handle_t_command(user: str, raw_args: str) -> str:
    """
    Core handler for !t / !translate / !trans.
    Returns a formatted string for chat.
    """
    lang, text = _parse_args(raw_args)
    if not lang or not text:
        return f"{HELP_LINE}"

    try:
        out, src, tgt = tx.translate_text(text, target=lang, source=None, autodetect_source=True)
        flag = tx.flag_for(tgt)
        # Shorten if your chat needs truncation; otherwise return full.
        return f"{flag} [{src}→{tgt}] {out}"
    except Exception as e:
        return f"⚠️ Translation error: {e}"


def handle_tlang_command() -> str:
    return f"{tx.supported_aliases_message()}"


# ---- Registration hooks (adapt to your command framework) ----
def register_commands(router) -> None:
    """
    You likely have some router/dispatcher where commands are registered.
    This function shows how to wire the aliases so they all call our handler.
    """
    # Main translate commands
    router.register("t", handle_t_command)
    router.register("translate", handle_t_command)
    router.register("trans", handle_t_command)

    # Language help aliases
    router.register("tlang", lambda *_: handle_tlang_command())
    router.register("translatelangs", lambda *_: handle_tlang_command())
    router.register("languages", lambda *_: handle_tlang_command())
    router.register("thelp", lambda *_: HELP_LINE)
