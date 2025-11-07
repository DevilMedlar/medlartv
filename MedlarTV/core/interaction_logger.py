"""
MedlarTV Interaction Logger
Logs all chat interactions for analytics and learning
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Check if logging is enabled
ENABLE_LOGGING = os.getenv("ENABLE_INTERACTION_LOGGING", "true").lower() == "true"
LOG_DIRECTORY = os.getenv("LOG_DIRECTORY", "logs")


def ensure_log_directory():
    """Create logs directory if it doesn't exist"""
    log_path = Path(LOG_DIRECTORY)
    log_path.mkdir(parents=True, exist_ok=True)
    return log_path


def log_interaction(
    username: str,
    message: str,
    response: str,
    mood: str = "unknown",
    language: str = "en",
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Log a chat interaction to JSONL file for analytics.
    
    Args:
        username: User who sent the message
        message: User's message
        response: Bot's response
        mood: Current bot mood
        language: Detected language
        metadata: Additional metadata (optional)
    """
    if not ENABLE_LOGGING:
        return
    
    try:
        log_path = ensure_log_directory()
        log_file = log_path / "interactions.jsonl"
        
        # Create log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user": username,
            "message": message,
            "response": response,
            "mood": mood,
            "language": language
        }
        
        # Add metadata if provided
        if metadata:
            log_entry["metadata"] = metadata
        
        # Append to JSONL file
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        
        # Success log (optional, can be removed for performance)
        # print(f"[Logger] Logged interaction: {username}")
        
    except Exception as e:
        print(f"[Logger] Error logging interaction: {e}")


def log_command(username: str, command: str, args: str = None, response: str = None, success: bool = True):
    """Log a command usage with optional arguments and response."""
    if not ENABLE_LOGGING:
        return
    
    try:
        log_path = ensure_log_directory()
        log_file = log_path / "commands.jsonl"
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user": username,
            "command": command,
            "success": success
        }
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
        
    except Exception as e:
        print(f"[Logger] Error logging command: {e}")


def log_mood_change(old_mood: str, new_mood: str, trigger: str = "auto"):
    """Log mood changes"""
    if not ENABLE_LOGGING:
        return
    
    try:
        log_path = ensure_log_directory()
        log_file = log_path / "moods.jsonl"
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "old_mood": old_mood,
            "new_mood": new_mood,
            "trigger": trigger
        }
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
        
    except Exception as e:
        print(f"[Logger] Error logging mood change: {e}")


def log_error(error_type: str, error_message: str, context: Optional[Dict] = None):
    """Log errors for debugging"""
    if not ENABLE_LOGGING:
        return
    
    try:
        log_path = ensure_log_directory()
        log_file = log_path / "errors.jsonl"
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": error_message
        }
        
        if context:
            log_entry["context"] = context
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        
    except Exception as e:
        print(f"[Logger] Error logging error (meta!): {e}")


def get_interaction_stats(days: int = 7) -> Dict[str, Any]:
    """
    Get statistics from interaction logs.
    
    Args:
        days: Number of days to analyze (default: 7)
    
    Returns:
        Dictionary with stats
    """
    try:
        log_path = ensure_log_directory()
        log_file = log_path / "interactions.jsonl"
        
        if not log_file.exists():
            return {"error": "No interaction logs found"}
        
        # Read logs
        interactions = []
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    interactions.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        
        # Calculate stats
        total_interactions = len(interactions)
        unique_users = len(set(i["user"] for i in interactions))
        
        # Mood distribution
        mood_counts = {}
        for interaction in interactions:
            mood = interaction.get("mood", "unknown")
            mood_counts[mood] = mood_counts.get(mood, 0) + 1
        
        # Language distribution
        language_counts = {}
        for interaction in interactions:
            lang = interaction.get("language", "en")
            language_counts[lang] = language_counts.get(lang, 0) + 1
        
        # Top users
        user_counts = {}
        for interaction in interactions:
            user = interaction["user"]
            user_counts[user] = user_counts.get(user, 0) + 1
        
        top_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "total_interactions": total_interactions,
            "unique_users": unique_users,
            "mood_distribution": mood_counts,
            "language_distribution": language_counts,
            "top_users": dict(top_users),
            "period_days": days
        }
        
    except Exception as e:
        return {"error": str(e)}


def clear_old_logs(days: int = 30):
    """
    Clear logs older than specified days (for storage management).
    
    Args:
        days: Keep logs from last N days
    """
    try:
        log_path = ensure_log_directory()
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        for log_file in log_path.glob("*.jsonl"):
            # Read and filter logs
            filtered_logs = []
            
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        timestamp = datetime.fromisoformat(entry["timestamp"]).timestamp()
                        
                        if timestamp >= cutoff:
                            filtered_logs.append(line)
                    except:
                        continue
            
            # Write back filtered logs
            with open(log_file, "w", encoding="utf-8") as f:
                f.writelines(filtered_logs)
        
        print(f"[Logger] Cleared logs older than {days} days")
        
    except Exception as e:
        print(f"[Logger] Error clearing old logs: {e}")


# Example usage and testing
if __name__ == "__main__":
    print("=" * 60)
    print("MedlarTV Interaction Logger - Testing")
    print("=" * 60)
    
    print("\n--- Logging Test Interactions ---")
    test_interactions = [
        ("User1", "Hey MedlarTV!", "Hey User1! 👋", "chill", "en"),
        ("User2", "Hola!", "Hola User2! 🇪🇸", "hype", "es"),
        ("User3", "Let's go!", "LET'S GOOOO! 🔥", "hype", "en"),
        ("User1", "Thanks!", "You're welcome! 💖", "supportive", "en"),
    ]
    
    for username, message, response, mood, language in test_interactions:
        log_interaction(username, message, response, mood, language)
        print(f"✓ Logged: {username}: {message}")
    
    print("\n--- Logging Commands ---")
    log_command("User1", "!ping", True)
    log_command("User2", "!mood", True)
    print("✓ Logged commands")
    
    print("\n--- Logging Mood Changes ---")
    log_mood_change("chill", "hype", "keyword")
    log_mood_change("hype", "supportive", "auto")
    print("✓ Logged mood changes")
    
    print("\n--- Getting Stats ---")
    stats = get_interaction_stats()
    print(json.dumps(stats, indent=2))
    
    print("\n--- Log Files Created ---")
    log_path = Path(LOG_DIRECTORY)
    for log_file in log_path.glob("*.jsonl"):
        print(f"  📄 {log_file.name}")