"""
MedlarTV Core API
FastAPI server for MedlarTV functionality
"""

from fastapi import FastAPI, Body
import yaml
from pathlib import Path
from MedlarTV.core.memory import reset_memory_on_shutdown
from MedlarTV.core.llm_brain import generate_response
import atexit

app = FastAPI(title="MedlarTV Core")

@app.get("/")
def root():
    return {"status": "MedlarTV Online", "message": "Processing data at light speed ⚡"}

def load_yaml(path: str, default: dict):
    p = Path(path)
    if not p.exists():
        return default
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or default

@app.get("/health")
def health():
    policy = load_yaml("MedlarTV/config/policy.yaml", {})
    devices = load_yaml("MedlarTV/config/devices.yaml", {})
    return {"ok": True, "policy_loaded": bool(policy), "devices_loaded": bool(devices)}

@app.get("/mood")
def current_mood():
    """Get MedlarTV's current dominant mood."""
    from MedlarTV.core.memory import get_dominant_weighted_mood
    mood = get_dominant_weighted_mood()
    return {"mood": mood, "status": "operational"}

@app.post("/mood")
def update_mood(data: dict = Body(...)):
    """Update MedlarTV's current mood via POST."""
    from MedlarTV.core.memory import record_mood
    new_mood = data.get("mood")
    if new_mood:
        record_mood(new_mood)
        return {"mood": new_mood, "status": "updated"}
    return {"error": "No mood provided", "status": "error"}

@app.get("/emotions")
def get_emotions():
    """Get current emotional state (new advanced system)."""
    try:
        from MedlarTV.core.emotional_system import get_emotional_system
        
        system = get_emotional_system()
        return {
            "dominant": system.get_dominant_emotion(),
            "top_3": system.get_top_emotions(3),
            "all_emotions": system.get_emotional_state(),
            "description": system.get_mood_description(),
            "status": "operational"
        }
    except ImportError:
        # Fallback if emotional system not installed yet
        from MedlarTV.core.memory import get_dominant_weighted_mood
        return {
            "dominant": get_dominant_weighted_mood(),
            "status": "legacy_mode"
        }

@app.get("/personality")
def personality():
    """Get MedlarTV's personality configuration."""
    personality_config = load_yaml("MedlarTV/config/personality.yaml", {})
    return personality_config.get("personality", {})

@app.post("/chat")
def chat(data: dict = Body(...)):
    prompt = data.get("prompt", "")
    sender = data.get("sender", "Pilot")  # default if none provided
    reply = generate_response(prompt, sender)

    # Fallback safeguard:
    # Automatically @tag users if missing — but skip Pilot and Co-Pilots
    if (
        "{user}" not in reply
        and "@" not in reply
        and sender.lower() not in ["pilot", "co-pilot"]
    ):
        reply = f"@{sender} {reply}"

    return {"input": prompt, "reply": reply}


# 🧹 Auto-reset memory when the core shuts down
atexit.register(reset_memory_on_shutdown)

if __name__ == "__main__":
    import uvicorn
    print("Launching MedlarTV Core on http://127.0.0.1:8000")
    uvicorn.run("MedlarTV.core.main:app", host="127.0.0.1", port=8000, reload=True)