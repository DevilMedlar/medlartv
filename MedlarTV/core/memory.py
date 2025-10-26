
import yaml
import os
import time
from datetime import datetime

# MedlarTV/core/memory.py
HERE = os.path.dirname(os.path.abspath(__file__))
MEMORY_PATH = os.path.normpath(os.path.join(HERE, "..", "data", "memory.yaml"))

def load_memory():
    if not os.path.exists(MEMORY_PATH):
        return {"personality_memory": {"mood_weights": {}, "last_update": None}}
    with open(MEMORY_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_memory(data):
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f)


def record_mood(mood):
    data = load_memory()
    moods = data["personality_memory"]["mood_weights"]
    moods[mood] = moods.get(mood, 0) + 1
    data["personality_memory"]["last_update"] = int(time.time())
    save_memory(data)


def get_dominant_mood():
    data = load_memory()
    moods = data["personality_memory"]["mood_weights"]
    if not moods:
        return "chill"
    return max(moods, key=moods.get)


def get_dominant_weighted_mood():
    data = load_memory()
    moods = data["personality_memory"]["mood_weights"]
    if not moods:
        return "chill"
    total = sum(moods.values())
    weighted = {m: v / total for m, v in moods.items()}
    return max(weighted, key=weighted.get)


def reset_memory_on_shutdown():
    """Reset MedlarTV's personality memory to neutral baseline on shutdown."""
    baseline = {
        "personality_memory": {
            "last_update": int(datetime.now().timestamp()),
            "mood_weights": {
                "chill": 1,
                "hype": 1,
                "snarky": 1,
                "supportive": 1
            }
        }
    }

    try:
        with open(MEMORY_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump(baseline, f)
        print("🧹 Memory reset to baseline.")
    except Exception as e:
        print(f"⚠️ Failed to reset memory: {e}")