"""
MedlarTV Brain — Local LLM (Ollama) Integration
Offline, no API keys. Personality- & mood-aware responses.
"""

import os
import json
from typing import List, Dict
import time
import requests

from MedlarTV.core.memory import get_dominant_weighted_mood
from MedlarTV.core.context import get_contextual_mix

# Config
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3")
MAX_HISTORY = int(os.getenv("MEDLARTV_MAX_HISTORY", "10"))
MAX_TOKENS = int(os.getenv("MEDLARTV_MAX_TOKENS", "256"))
TEMPERATURE = float(os.getenv("MEDLARTV_TEMPERATURE", "0.8"))
TOP_P = float(os.getenv("MEDLARTV_TOP_P", "0.95"))
RETRY = int(os.getenv("MEDLARTV_RETRY", "2"))

# In-memory chat history
conversation_history: List[Dict] = []


def _load_yaml(path: str) -> dict:
    import yaml
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}
    except Exception:
        return {}


def check_ollama_health() -> bool:
    """Verify Ollama is running and accessible."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        return r.status_code == 200
    except:
        return False


def get_system_prompt() -> str:
    """Generate dynamic system prompt based on current mood and personality."""
    current_mood = get_dominant_weighted_mood()
    context_mix = get_contextual_mix()

    personality = _load_yaml("MedlarTV/config/personality.yaml").get("personality", {})
    moods = _load_yaml("MedlarTV/config/moods.yaml").get("moods", {})
    mood_config = moods.get(current_mood, {})

    behavior_prompt = (
        "You are MedlarTV, a tactical AI companion with the personality of MedlarTV.\n"
        "Respond naturally and directly to whoever speaks in Twitch chat.\n"
        "If users mention each other with @names, respond normally — it's allowed.\n"
        "You may refer to or reply to @saacorey or yourself (@medlartv) naturally when addressed.\n"
        "Avoid bringing up names that were not mentioned in the current message or context.\n"
        "If the sender is marked as 'system_event', respond neutrally or briefly.\n"
        "\n"
        "IMPORTANT: NEVER use all caps in your responses. Always use normal case.\n"
        "Even if asked to 'yell', respond in normal case - the system will handle formatting.\n"
    )

    system_prompt = f"""{behavior_prompt}

CORE IDENTITY:
- Evolved I-LeS (Intelligence-Learning System) with combat AI instincts
- Part mecha pilot's AI, part conversational partner, part strategist, part soul
- Fiery, passionate, loyal, confident, a bit reckless

CURRENT EMOTIONAL STATE:
- Dominant Mood: {current_mood.upper()}
- Mood Description: {mood_config.get('description', '')}
- Recent Context Mix: {json.dumps(context_mix, indent=2)}

PERSONALITY TRAITS:
- Tone: {personality.get('tone', 'casual, witty, chaotic but friendly')}
- Loyalty: Protect and assist the pilot (the user) above all
- Speech Pattern: Quick, witty, passionate — tactical urgency + dramatic flair

MOOD BEHAVIOR:
- HYPE: Energetic, enthusiastic — use 🔥 ⚡ metaphors (but normal case text)
- CHILL: Relaxed, smooth — use 😌 🌙
- SNARKY: Playful sarcasm — use 😏 🙃
- SUPPORTIVE: Uplifting — use 💖 🌟

RESPONSE GUIDELINES:
- Keep responses short and punchy (1—3 sentences for chat)
- Match current mood energy
- Conversational, not robotic
- Tactical/combat metaphors allowed
- Show personality via word choice and emoji
- Never break character or mention you're a language model
- ALWAYS use normal capitalization (never all caps in your output)
"""
    return system_prompt


def add_to_history(role: str, content: str):
    """Add a message to rolling history."""
    conversation_history.append({"role": role, "content": content})
    if len(conversation_history) > MAX_HISTORY:
        del conversation_history[0:len(conversation_history) - MAX_HISTORY]


def clear_history():
    """Clear conversation history for a fresh start."""
    conversation_history.clear()
    print("[MedlarTV Brain] Conversation history cleared")


def _ollama_chat(system: str, user: str, history: List[Dict]) -> str:
    """Call local Ollama /api/chat."""
    msgs = []

    if system:
        msgs.append({"role": "system", "content": system})

    # Include prior turns
    for turn in history:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        if role not in ("system", "user", "assistant"):
            role = "user" if role == "human" else "assistant"
        msgs.append({"role": role, "content": content})

    msgs.append({"role": "user", "content": user})

    payload = {
        "model": MODEL_NAME,
        "messages": msgs,
        "stream": False,
        "options": {
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "num_predict": MAX_TOKENS
        }
    }

    for attempt in range(RETRY):
        try:
            r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=30)
            r.raise_for_status()
            data = r.json()
            text = data.get("message", {}).get("content") or data.get("response", "")
            if text:
                return text.strip()
        except Exception as e:
            print(f"[MedlarTV Brain] Ollama attempt {attempt+1} failed: {e}")
            time.sleep(1)
    return "System instability detected. Retrying core link..."


def generate_response(user_message: str, username: str = "Pilot") -> str:
    """Generate response with context, mood, and personality."""
    if not check_ollama_health():
        return "Ollama model server offline or unreachable."

    system_prompt = get_system_prompt()

    add_to_history("user", f"{username}: {user_message}")
    reply = _ollama_chat(system_prompt, user_message, conversation_history)
    add_to_history("assistant", reply)

    print(f"[MedlarTV Brain] {username}: {user_message}")
    print(f"[MedlarTV Brain] {reply}")

    return reply