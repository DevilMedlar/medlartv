import time
from collections import deque

# store the last 20 mood events with timestamps
recent_moods = deque(maxlen=20)

def record_session_mood(mood):
    """Add a mood event with timestamp."""
    recent_moods.append((mood, time.time()))

def get_contextual_mix():
    """Return a soft ratio blend based on recent moods."""
    if not recent_moods:
        return {"hype": 0.25, "chill": 0.25, "snarky": 0.25, "supportive": 0.25}
    counts = {}
    for mood, _ in recent_moods:
        counts[mood] = counts.get(mood, 0) + 1
    total = sum(counts.values())
    return {m: counts.get(m, 0) / total for m in ["hype", "chill", "snarky", "supportive"]}