import os
DEBUG = os.getenv("MEDLARTV_DEBUG", "false").lower() == "true"
if DEBUG:
    print("[DEBUG memory] Loaded memory.py")
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

MEMORY_FILE = Path("memory.json")


# --------------------------------------------------------------
# LOAD MEMORY
# --------------------------------------------------------------

def load_memory() -> Dict[str, Any]:
    if DEBUG:
        print(f"[DEBUG memory] load_memory() called. FILE={MEMORY_FILE}")

    if not MEMORY_FILE.exists():
        if DEBUG:
            print("[DEBUG memory] memory.json does NOT exist. Returning empty memory.")
        return {"moods": [], "last_reset": datetime.utcnow().isoformat()}

    try:
        if DEBUG:
            print("[DEBUG memory] Opening memory.json for read...")
        with MEMORY_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if DEBUG:
            print(f"[DEBUG memory] load_memory() loaded data: {data}")
        return data
    except Exception as e:
        if DEBUG:
            print(f"[DEBUG memory] ERROR while reading memory.json: {e}")
        return {"moods": [], "last_reset": datetime.utcnow().isoformat()}


# --------------------------------------------------------------
# SAVE MEMORY
# --------------------------------------------------------------

def save_memory(data: Dict[str, Any]) -> None:
    if DEBUG:
        print(f"[DEBUG memory] save_memory() called with data={data}")

    try:
        if DEBUG:
            print("[DEBUG memory] Opening memory.json for WRITE...")
        with MEMORY_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        if DEBUG:
            print("[DEBUG memory] save_memory() write completed.")
    except Exception as e:
        if DEBUG:
            print(f"[DEBUG memory] ERROR saving memory.json: {e}")


# --------------------------------------------------------------
# RECORD MOOD ENTRY
# --------------------------------------------------------------

def record_mood(mood: str, source: str) -> None:
    if DEBUG:
        print(f"[DEBUG memory] record_mood() called mood={mood!r} source={source!r}")

    data = load_memory()
    if DEBUG:
        print(f"[DEBUG memory] record_mood() memory BEFORE append: {data}")

    entry = {
        "mood": mood,
        "source": source,
        "timestamp": datetime.utcnow().isoformat()
    }
    if DEBUG:
        print(f"[DEBUG memory] record_mood() new entry={entry}")

    try:
        data.setdefault("moods", []).append(entry)
        if DEBUG:
            print(f"[DEBUG memory] record_mood() memory AFTER append: {data}")
        save_memory(data)
    except Exception as e:
        if DEBUG:
            print(f"[DEBUG memory] ERROR updating mood memory: {e}")


# --------------------------------------------------------------
# GET DOMINANT MOOD (SIMPLE COUNT)
# --------------------------------------------------------------

def get_dominant_mood() -> Optional[str]:
    if DEBUG:
        print("[DEBUG memory] get_dominant_mood() called")

    data = load_memory()
    moods = data.get("moods", [])

    if DEBUG:
        print(f"[DEBUG memory] get_dominant_mood() moods list: {moods}")

    if not moods:
        if DEBUG:
            print("[DEBUG memory] dominant_mood → None (no moods)")
        return None

    counts: Dict[str, int] = {}
    for entry in moods:
        m = entry.get("mood")
        counts[m] = counts.get(m, 0) + 1

    if DEBUG:
        print(f"[DEBUG memory] get_dominant_mood() counts={counts}")

    dominant = max(counts, key=counts.get)
    if DEBUG:
        print(f"[DEBUG memory] get_dominant_mood() dominant={dominant}")

    return dominant


# --------------------------------------------------------------
# GET DOMINANT MOOD (WEIGHTED BY RECENCY)
# --------------------------------------------------------------

def get_dominant_weighted_mood() -> Optional[str]:
    if DEBUG:
        print("[DEBUG memory] get_dominant_weighted_mood() called")

    data = load_memory()
    moods = data.get("moods", [])

    if DEBUG:
        print(f"[DEBUG memory] get_dominant_weighted_mood() mood entries={len(moods)}")

    if not moods:
        if DEBUG:
            print("[DEBUG memory] weighted_mood → None (no moods)")
        return None

    weights: Dict[str, float] = {}
    now = datetime.utcnow()

    for entry in moods:
        mood = entry.get("mood")
        ts = entry.get("timestamp")

        try:
            dt = datetime.fromisoformat(ts.replace("Z", ""))
            age_seconds = max(1, (now - dt).total_seconds())
            weight = 1 / age_seconds
        except Exception as e:
            if DEBUG:
                print(f"[DEBUG memory] ERROR parsing timestamp {ts}: {e}")
            weight = 0.000001

        if DEBUG:
            print(f"[DEBUG memory] Mood={mood} ts={ts} weight={weight}")

        weights[mood] = weights.get(mood, 0) + weight

    if DEBUG:
        print(f"[DEBUG memory] get_dominant_weighted_mood() weights={weights}")

    dominant = max(weights, key=weights.get)
    if DEBUG:
        print(f"[DEBUG memory] get_dominant_weighted_mood() dominant={dominant}")

    return dominant


# --------------------------------------------------------------
# RESET MEMORY
# --------------------------------------------------------------

def reset_memory_on_shutdown() -> None:
    if DEBUG:
        print("[DEBUG memory] reset_memory_on_shutdown() called")

    data = {
        "moods": [],
        "last_reset": datetime.utcnow().isoformat()
    }

    if DEBUG:
        print(f"[DEBUG memory] reset_memory_on_shutdown() new memory={data}")

    try:
        save_memory(data)
        if DEBUG:
            print("[DEBUG memory] reset_memory_on_shutdown() save complete")
    except Exception as e:
        if DEBUG:
            print(f"[DEBUG memory] ERROR in reset_memory_on_shutdown(): {e}")
