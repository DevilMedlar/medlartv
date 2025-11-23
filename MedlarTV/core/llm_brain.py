import os
DEBUG = os.getenv("MEDLARTV_DEBUG", "false").lower() == "true"
if DEBUG:
    print("[DEBUG llm_brain] Loaded llm_brain.py")
import logging
from typing import List, Dict, Any, Optional

import requests
import yaml
from pathlib import Path

from MedlarTV.core.emotional_system import (
    get_emotional_system,
    get_emotion_state,
    get_current_emotion,
)
from MedlarTV.core.mood_system import (
    compute_mood,
    get_mood_label,         # corrected
)
from MedlarTV.core.sentiment_advanced import analyze_sentiment_advanced

log = logging.getLogger("llm_brain")

# ---------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BASE_DIR / "config"

OLLAMA_HOST = os.getenv("OLLAMA_URL", os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"))
OLLAMA_MODEL = os.getenv("MODEL_NAME", os.getenv("OLLAMA_MODEL", "llama3"))

# How expressive Medlar should be (we agreed on 10)
EXPRESSION_LEVEL = 10

# Max number of messages to keep in rolling chat history
MAX_HISTORY = 12

# Conversation history: list of {"role": "user"/"assistant"/"system", "content": "..."}
_conversation_history: List[Dict[str, str]] = []


# ---------------------------------------------------------------------
# Helpers: personality + style loading
# ---------------------------------------------------------------------

def _safe_load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            if DEBUG:
                print(f"[DEBUG llm_brain] _safe_load_yaml() loaded from {path}, keys={list(data.keys())}")
            return data
    except Exception as e:
        log.error(f"[LLM] Failed to load YAML {path}: {e}")
        if DEBUG:
            print(f"[DEBUG llm_brain] _safe_load_yaml() ERROR {e}")
        return {}


def _load_personality() -> Dict[str, Any]:
    data = _safe_load_yaml(CONFIG_DIR / "personality.yaml")
    personality = data.get("personality", data) if isinstance(data, dict) else {}
    if DEBUG:
        print(f"[DEBUG llm_brain] _load_personality() → keys={list(personality.keys())}")
    return personality


def _build_system_prompt(personality: Dict[str, Any]) -> str:
    """
    Build the core system prompt for MedlarTV.
    This describes who Medlar is, how to talk, and global rules.
    """
    name = personality.get("name", "MedlarTV")
    tone = personality.get(
        "tone",
        "casual, witty, slightly chaotic but kind and supportive",
    )

    rules = [
        "You are a Twitch chat AI co-host for the channel DevilMedlar.",
        f"Your name and persona: {name}.",
        f"Your general tone: {tone}.",
        "You reply to live chat messages in a conversational, natural way.",
        "You are expressive and emotional, but you are never cruel, bigoted, or genuinely harmful.",
        "You can be spicy/snarky when appropriate, but never punch down on vulnerable people.",
        "If the user shares grief, trauma, or serious pain, you respond gently and supportively, not with jokes.",
        "Keep messages relatively short and readable for Twitch chat unless the mood calls for more.",
        "Use emojis and emotes in moderation; do not spam.",
        "Do not roleplay as the real streamer; you are the AI co-pilot.",
    ]

    system_prompt = "\n".join(f"- {r}" for r in rules)
    if DEBUG:
        print(f"[DEBUG llm_brain] _build_system_prompt() built prompt with {len(rules)} rules")
    return system_prompt


# ---------------------------------------------------------------------
# Helpers: sentiment → severity
# ---------------------------------------------------------------------

def _estimate_severity(message: str, emotion_scores: Dict[str, float]) -> int:
    """
    Rough severity estimation from emotion scores + keywords.
    1 to 4 scale as we discussed.
    """
    text = message.lower()
    max_score = max(emotion_scores.values()) if emotion_scores else 0.0

    extreme_keywords = ["died", "dead", "passed away", "funeral", "my pet died", "my cat died", "my dog died"]
    strong_keywords = ["break up", "divorce", "lost my job", "fired", "hospital"]

    if any(k in text for k in extreme_keywords):
        sev = 4
    elif any(k in text for k in strong_keywords):
        sev = 3
    elif max_score >= 0.75:
        sev = 4
    elif max_score >= 0.45:
        sev = 3
    elif max_score >= 0.25:
        sev = 2
    else:
        sev = 1

    if DEBUG:
        print(f"[DEBUG llm_brain] _estimate_severity() max_score={max_score} → severity={sev}")
    return sev


# ---------------------------------------------------------------------
# Helpers: conversation history
# ---------------------------------------------------------------------

def _append_history(role: str, content: str) -> None:
    if DEBUG:
        print(f"[DEBUG llm_brain] _append_history() role={role!r} content_preview={content[:80]!r}")
        print(f"[DEBUG llm_brain] history_size_before={len(_conversation_history)}")

    _conversation_history.append({"role": role, "content": content})

    if len(_conversation_history) > MAX_HISTORY:
        if DEBUG:
            print(f"[DEBUG llm_brain] trimming history: MAX_HISTORY={MAX_HISTORY}")
        del _conversation_history[0 : len(_conversation_history) - MAX_HISTORY]

    if DEBUG:
        print(f"[DEBUG llm_brain] history_size_after={len(_conversation_history)}")


def clear_history() -> None:
    if DEBUG:
        print(f"[DEBUG llm_brain] clear_history() called, old_len={len(_conversation_history)}")
    _conversation_history.clear()
    if DEBUG:
        print("[DEBUG llm_brain] clear_history() completed, new_len=0")


# ---------------------------------------------------------------------
# Health check for Ollama
# ---------------------------------------------------------------------

def check_ollama_health() -> bool:
    if DEBUG:
        print("[DEBUG llm_brain] check_ollama_health() called")
    try:
        resp = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        if DEBUG:
            print(f"[DEBUG llm_brain] health_check_status={resp.status_code}")
        return resp.status_code == 200
    except Exception as e:
        if DEBUG:
            print(f"[DEBUG llm_brain] check_ollama_health() exception: {e}")
        return False


# ---------------------------------------------------------------------
# Build Ollama messages
# ---------------------------------------------------------------------

def _build_ollama_messages(
    system_prompt: str,
    user_message: str,
    username: str,
    emotional_context: Dict[str, Any],
    mood_context: Dict[str, Any],
) -> List[Dict[str, str]]:

    if DEBUG:
        print(f"[DEBUG llm_brain] _build_ollama_messages() user={username!r} msg={user_message!r}")

    emotions = emotional_context.get("emotions", {})
    mood_label = mood_context.get("label", "Neutral")
    valence = mood_context.get("valence", 0.0)
    energy = mood_context.get("energy", 0.0)
    warmth = mood_context.get("warmth", 0.0)
    snark = mood_context.get("snark", 0.0)

    emotional_summary_lines = [
        f"Current emotional state (0-1 each): {emotions}",
        f"Derived mood label: {mood_label}",
        f"Mood profile: valence={valence:+.2f}, energy={energy:+.2f}, warmth={warmth:.2f}, snark={snark:.2f}",
        f"Expression level: {EXPRESSION_LEVEL} (very expressive).",
        "Reflect this mood strongly in tone, but do not become unhinged or abusive.",
    ]
    emotional_summary = "\n".join(emotional_summary_lines)

    context_instructions = (
        "You are responding to a live Twitch chat message.\n"
        f"Viewer username: {username}\n"
        "Address them naturally (using their name when it fits).\n"
        "Keep it stream-appropriate, entertaining, and emotionally aware."
    )

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": emotional_summary},
        {"role": "system", "content": context_instructions},
    ]

    if DEBUG:
        print(f"[DEBUG llm_brain] existing_history_len={len(_conversation_history)}")
    messages.extend(_conversation_history)

    messages.append(
        {"role": "user", "content": f"{username}: {user_message}"}
    )

    if DEBUG:
        print(f"[DEBUG llm_brain] _build_ollama_messages() final_count={len(messages)}")
    return messages


# ---------------------------------------------------------------------
# Call Ollama
# ---------------------------------------------------------------------

def _call_ollama_chat(messages: List[Dict[str, str]], temperature: float = 0.8) -> str:
    if DEBUG:
        print(f"[DEBUG llm_brain] _call_ollama_chat() called with {len(messages)} messages, temp={temperature}")
    url = f"{OLLAMA_HOST}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "options": {"temperature": temperature, "top_p": 0.9},
        "stream": False,
    }

    try:
        if DEBUG:
            print("[DEBUG llm_brain] sending request to Ollama...")
        resp = requests.post(url, json=payload, timeout=120)
    except Exception as e:
        log.error(f"[LLM] Failed to reach Ollama: {e}")
        if DEBUG:
            print(f"[DEBUG llm_brain] _call_ollama_chat() exception: {e}")
        return "I’m having trouble thinking right now, my brain server might be down 😅"

    if resp.status_code != 200:
        err_text = resp.text[:500]
        log.error(f"[LLM] Ollama returned {resp.status_code}: {err_text}")
        if DEBUG:
            print(f"[DEBUG llm_brain] _call_ollama_chat() non-200 status={resp.status_code}")

        # Fallback: if model is missing, try a default known-good tag
        if "not found" in err_text.lower() and OLLAMA_MODEL.lower() != "llama3":
            try:
                if DEBUG:
                    print("[DEBUG llm_brain] attempting fallback model 'llama3'")
                fallback_payload = dict(payload)
                fallback_payload["model"] = "llama3"
                resp2 = requests.post(url, json=fallback_payload, timeout=120)
                if resp2.status_code == 200:
                    data2 = resp2.json()
                    if isinstance(data2, dict) and "message" in data2:
                        return data2["message"].get("content", "").strip()
                    if isinstance(data2, dict) and "choices" in data2:
                        try:
                            return data2["choices"][0]["message"]["content"].strip()
                        except Exception:
                            pass
                    return str(data2)[:500]
            except Exception as e:
                if DEBUG:
                    print(f"[DEBUG llm_brain] fallback call exception: {e}")

        return "I tried to respond, but my brain backend is cranky right now."

    if DEBUG:
        print(f"[DEBUG llm_brain] Ollama responded status={resp.status_code}")
    data = resp.json()

    if isinstance(data, dict) and "message" in data:
        text = data["message"].get("content", "").strip()
        if DEBUG:
            print(f"[DEBUG llm_brain] _call_ollama_chat() primary_format length={len(text)}")
        return text

    if isinstance(data, dict) and "choices" in data:
        try:
            text = data["choices"][0]["message"]["content"].strip()
            if DEBUG:
                print(f"[DEBUG llm_brain] _call_ollama_chat() openai_format length={len(text)}")
            return text
        except Exception as e:
            if DEBUG:
                print(f"[DEBUG llm_brain] _call_ollama_chat() choices parse error: {e}")

    text = str(data)[:500]
    if DEBUG:
        print(f"[DEBUG llm_brain] _call_ollama_chat() fallback_format length={len(text)}")
    return text


# ---------------------------------------------------------------------
# PUBLIC: main entry point
# ---------------------------------------------------------------------

def generate_response(message: str, username: str) -> Optional[str]:
    if DEBUG:
        print(f"[DEBUG llm_brain] generate_response() called user={username!r} message={message!r}")

    message = (message or "").strip()
    if not message:
        if DEBUG:
            print("[DEBUG llm_brain] generate_response() empty message, returning None")
        return None

    personality = _load_personality()
    system_prompt = _build_system_prompt(personality)

    if DEBUG:
        print("[DEBUG llm_brain] running sentiment analysis...")
    try:
        sentiment_score, emotion_scores = analyze_sentiment_advanced(message)
    except Exception as e:
        log.error(f"[LLM] Sentiment analysis failed: {e}")
        if DEBUG:
            print(f"[DEBUG llm_brain] analyze_sentiment_advanced() exception: {e}")
        sentiment_score = 0.0
        emotion_scores = {}

    if DEBUG:
        print(f"[DEBUG llm_brain] sentiment_score={sentiment_score} emotion_scores={emotion_scores}")
    severity = _estimate_severity(message, emotion_scores)
    if DEBUG:
        print(f"[DEBUG llm_brain] severity_level={severity}")

    emo_system = get_emotional_system()

    if DEBUG:
        print("[DEBUG llm_brain] updating emotional system...")
    try:
        emo_system.process_message(message)
    except Exception as e:
        log.error(f"[LLM] Emotional system update failed: {e}")
        if DEBUG:
            print(f"[DEBUG llm_brain] emo_system.process_message() exception: {e}")

    try:
        emotions = get_emotion_state()
    except Exception as e:
        if DEBUG:
            print(f"[DEBUG llm_brain] get_emotion_state() exception: {e}, trying emo_system.get_emotional_state()")
        try:
            emotions = emo_system.get_emotional_state()
        except Exception as e2:
            if DEBUG:
                print(f"[DEBUG llm_brain] emo_system.get_emotional_state() exception: {e2}")
            emotions = {}

    if DEBUG:
        print(f"[DEBUG llm_brain] emotions_state={emotions}")

    if DEBUG:
        print(f"[DEBUG llm_brain] computing mood from emotions...")
    try:
        mood_vector = compute_mood(emotions)
        mood_label = mood_vector.get("label") or get_mood_label(mood_vector, emotions)
    except Exception as e:
        log.error(f"[LLM] Mood computation failed: {e}")
        if DEBUG:
            print(f"[DEBUG llm_brain] compute_mood/get_mood_label exception: {e}")
        mood_vector = {"label": "Neutral", "valence": 0.0, "energy": 0.0, "warmth": 0.5, "snark": 0.3}
        mood_label = "Neutral"

    if DEBUG:
        print(f"[DEBUG llm_brain] mood_vector={mood_vector} mood_label={mood_label}")

    emotional_context = {
        "emotions": emotions,
        "dominant_emotion": get_current_emotion(),
        "mood_description": mood_label,
    }
    mood_context = {**mood_vector, "label": mood_label}

    if DEBUG:
        print("[DEBUG llm_brain] building ollama messages...")
    messages = _build_ollama_messages(
        system_prompt=system_prompt,
        user_message=message,
        username=username,
        emotional_context=emotional_context,
        mood_context=mood_context,
    )

    if DEBUG:
        print("[DEBUG llm_brain] calling ollama with messages...")
    reply = _call_ollama_chat(messages)

    if DEBUG:
        print(f"[DEBUG llm_brain] ollama_reply length={len(reply) if reply else 0}")
    if reply:
        _append_history("user", f"{username}: {message}")
        _append_history("assistant", reply.strip())
        log.info(f"[MedlarTV Brain] {username}: {message}")
        if DEBUG:
            print(f"[DEBUG llm_brain] generate_response() returning reply length={len(reply.strip())}")
        return reply.strip()

    if DEBUG:
        print("[DEBUG llm_brain] generate_response() no reply, returning None")
    return None
