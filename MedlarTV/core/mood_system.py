"""
MedlarTV Mood System
Consolidated mood tracking, context, and expression generation
Merged from context.py and expression.py
"""

import time
import random
from collections import deque
from typing import Dict
from MedlarTV.core.memory import load_memory

# ===== Context Tracking =====
recent_moods = deque(maxlen=20)

def record_session_mood(mood: str) -> None:
    """Add a mood event with timestamp."""
    recent_moods.append((mood, time.time()))

def get_contextual_mix() -> Dict[str, float]:
    """Return a soft ratio blend based on recent moods."""
    if not recent_moods:
        return {"hype": 0.25, "chill": 0.25, "snarky": 0.25, "supportive": 0.25}
    
    counts = {}
    for mood, _ in recent_moods:
        counts[mood] = counts.get(mood, 0) + 1
    
    total = sum(counts.values())
    return {m: counts.get(m, 0) / total for m in ["hype", "chill", "snarky", "supportive"]}

# ===== Expression Generation =====
VOCAB = {
    "hype": ["LET'S GOOO!!!", "We're SO back!", "🔥🔥🔥", "WOO!!"],
    "chill": ["just vibin'", "easy breezy", "coolin'", "smooth vibes"],
    "snarky": ["lol", "sure thing", "bruh", "🤨"],
    "supportive": ["you got this", "keep shining", "nice work", "💖"]
}

def blended_phrase() -> str:
    """Return a tone phrase mixed by memory and recent context."""
    data = load_memory()
    moods = data["personality_memory"]["mood_weights"]
    total = sum(moods.values()) or 1
    ratios = {m: moods.get(m, 0) / total for m in ["hype", "chill", "snarky", "supportive"]}

    context = get_contextual_mix()
    for m in ratios:
        ratios[m] = (ratios[m] + context[m]) / 2

    pool = []
    for m, w in ratios.items():
        count = int(w * 10) or 1
        pool.extend([m] * count)

    if not pool:
        pool = ["chill"]

    chosen = random.choice(pool)
    return random.choice(VOCAB[chosen])
