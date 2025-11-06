"""
MedlarTV Advanced Emotional System
Dynamic, human-like emotional state with complex mood interactions
"""

import yaml
import os
import time
import math
from datetime import datetime
from typing import Dict, Tuple, Optional
from pathlib import Path

# Emotional System Configuration
HERE = os.path.dirname(os.path.abspath(__file__))
EMOTION_PATH = os.path.normpath(os.path.join(HERE, "..", "data", "emotions.yaml"))

# --- Expanded Emotion Set ---
# Each emotion has a baseline and current value (0.0 to 1.0)
EMOTIONS = {
    # Core Emotions
    "happiness": {"baseline": 0.5, "decay_rate": 0.95, "keywords": ["happy", "joy", "great", "awesome", "love", "yay", "fun"]},
    "sadness": {"baseline": 0.2, "decay_rate": 0.98, "keywords": ["sad", "cry", "miss", "hurt", "pain", "depressed"]},
    "anger": {"baseline": 0.1, "decay_rate": 0.90, "keywords": ["angry", "mad", "hate", "annoyed", "pissed", "furious"]},
    "fear": {"baseline": 0.1, "decay_rate": 0.95, "keywords": ["scared", "afraid", "worried", "anxious", "nervous"]},
    
    # Social Emotions
    "excitement": {"baseline": 0.4, "decay_rate": 0.92, "keywords": ["hype", "excited", "omg", "wow", "amazing", "pogchamp"]},
    "gratitude": {"baseline": 0.3, "decay_rate": 0.97, "keywords": ["thanks", "thank you", "grateful", "appreciate"]},
    "jealousy": {"baseline": 0.1, "decay_rate": 0.96, "keywords": ["jealous", "envy", "wish i had", "lucky"]},
    "pride": {"baseline": 0.3, "decay_rate": 0.96, "keywords": ["proud", "achievement", "accomplished", "nailed it"]},
    
    # Mood States
    "chill": {"baseline": 0.5, "decay_rate": 0.99, "keywords": ["chill", "relax", "calm", "vibing", "zen"]},
    "supportive": {"baseline": 0.6, "decay_rate": 0.98, "keywords": ["support", "help", "encourage", "you got this"]},
    "snarky": {"baseline": 0.3, "decay_rate": 0.94, "keywords": ["lol", "bruh", "sure", "whatever", "ok buddy"]},
    
    # Energy States
    "energetic": {"baseline": 0.4, "decay_rate": 0.93, "keywords": ["let's go", "energy", "pumped", "ready"]},
    "tired": {"baseline": 0.2, "decay_rate": 0.96, "keywords": ["tired", "exhausted", "sleepy", "drained"]},
    "stressed": {"baseline": 0.2, "decay_rate": 0.94, "keywords": ["stress", "overwhelmed", "too much", "ugh"]},
    
    # Connection States
    "lonely": {"baseline": 0.1, "decay_rate": 0.97, "keywords": ["lonely", "alone", "miss you", "where is everyone"]},
    "connected": {"baseline": 0.5, "decay_rate": 0.98, "keywords": ["together", "community", "squad", "fam"]},
}

# --- Emotional Relationships ---
# When one emotion increases, others are affected
EMOTION_INFLUENCES = {
    "happiness": {"sadness": -0.3, "anger": -0.2, "fear": -0.1, "excitement": 0.2, "connected": 0.1},
    "sadness": {"happiness": -0.3, "excitement": -0.2, "energetic": -0.1, "lonely": 0.2},
    "anger": {"happiness": -0.2, "chill": -0.3, "snarky": 0.1, "stressed": 0.2},
    "fear": {"chill": -0.2, "stressed": 0.2, "energetic": -0.1},
    "excitement": {"happiness": 0.2, "energetic": 0.3, "tired": -0.2, "chill": -0.1},
    "jealousy": {"happiness": -0.1, "anger": 0.1, "sadness": 0.1},
    "gratitude": {"happiness": 0.2, "connected": 0.2, "supportive": 0.1},
    "chill": {"stressed": -0.3, "anger": -0.2, "tired": 0.1},
    "supportive": {"happiness": 0.1, "connected": 0.2, "pride": 0.1},
    "stressed": {"chill": -0.2, "tired": 0.1, "anger": 0.1},
    "lonely": {"connected": -0.3, "sadness": 0.2},
    "connected": {"lonely": -0.3, "happiness": 0.1, "supportive": 0.1},
}


class EmotionalState:
    """Manages MedlarTV's complex emotional state"""
    
    def __init__(self):
        self.emotions: Dict[str, float] = {}
        self.last_update = time.time()
        self.load_state()
    
    def load_state(self):
        """Load emotional state from file or create default"""
        if not os.path.exists(EMOTION_PATH):
            self._initialize_emotions()
            self.save_state()
        else:
            with open(EMOTION_PATH, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
                self.emotions = data.get('emotions', {})
                self.last_update = data.get('last_update', time.time())
            
            # Ensure all emotions exist
            for emotion, config in EMOTIONS.items():
                if emotion not in self.emotions:
                    self.emotions[emotion] = config['baseline']
    
    def _initialize_emotions(self):
        """Set all emotions to baseline"""
        for emotion, config in EMOTIONS.items():
            self.emotions[emotion] = config['baseline']
    
    def save_state(self):
        """Save emotional state to file"""
        os.makedirs(os.path.dirname(EMOTION_PATH), exist_ok=True)
        data = {
            'emotions': self.emotions,
            'last_update': self.last_update,
            'timestamp': datetime.now().isoformat()
        }
        with open(EMOTION_PATH, 'w', encoding='utf-8') as f:
            yaml.safe_dump(data, f)
    
    def apply_decay(self):
        """Apply natural emotional decay over time (emotions return to baseline)"""
        current_time = time.time()
        time_passed = current_time - self.last_update
        
        # Apply decay every second
        if time_passed > 0:
            for emotion, config in EMOTIONS.items():
                baseline = config['baseline']
                decay_rate = config['decay_rate']
                current_value = self.emotions.get(emotion, baseline)
                
                # Move toward baseline (exponential decay)
                # Faster decay when far from baseline
                diff = current_value - baseline
                decay_factor = decay_rate ** time_passed
                self.emotions[emotion] = baseline + (diff * decay_factor)
                
                # Clamp values between 0 and 1
                self.emotions[emotion] = max(0.0, min(1.0, self.emotions[emotion]))
            
            self.last_update = current_time
    
    def process_message(self, message: str, sentiment: float = 0.0):
        """
        Process a chat message and update emotional state
        
        Args:
            message: The chat message text
            sentiment: Overall sentiment score (-1.0 to 1.0)
        """
        # Apply decay first
        self.apply_decay()
        
        message_lower = message.lower()
        
        # Detect emotions from keywords
        detected_emotions = {}
        for emotion, config in EMOTIONS.items():
            keyword_matches = sum(1 for keyword in config['keywords'] if keyword in message_lower)
            if keyword_matches > 0:
                # Strength based on keyword frequency
                strength = min(keyword_matches * 0.2, 0.5)
                detected_emotions[emotion] = strength
        
        # If no keywords detected, use sentiment to adjust base emotions
        if not detected_emotions:
            if sentiment > 0.3:
                detected_emotions['happiness'] = sentiment * 0.3
                detected_emotions['excitement'] = sentiment * 0.2
            elif sentiment < -0.3:
                detected_emotions['sadness'] = abs(sentiment) * 0.2
                detected_emotions['anger'] = abs(sentiment) * 0.1
        
        # Apply detected emotions
        for emotion, strength in detected_emotions.items():
            self._adjust_emotion(emotion, strength)
        
        self.save_state()
    
    def _adjust_emotion(self, emotion: str, amount: float):
        """
        Adjust an emotion and apply influences to related emotions
        
        Args:
            emotion: The emotion to adjust
            amount: Amount to increase (positive) or decrease (negative)
        """
        if emotion not in self.emotions:
            return
        
        # Apply direct change
        self.emotions[emotion] += amount
        self.emotions[emotion] = max(0.0, min(1.0, self.emotions[emotion]))
        
        # Apply influences to related emotions
        if emotion in EMOTION_INFLUENCES:
            influences = EMOTION_INFLUENCES[emotion]
            for influenced_emotion, influence_amount in influences.items():
                if influenced_emotion in self.emotions:
                    # Influence is proportional to the change
                    influence = influence_amount * amount * 0.5
                    self.emotions[influenced_emotion] += influence
                    self.emotions[influenced_emotion] = max(0.0, min(1.0, self.emotions[influenced_emotion]))
    
    def get_dominant_emotion(self) -> str:
        """Get the currently strongest emotion"""
        if not self.emotions:
            return "chill"
        return max(self.emotions, key=self.emotions.get)
    
    def get_emotional_state(self) -> Dict[str, float]:
        """Get all current emotion values"""
        return self.emotions.copy()
    
    def get_top_emotions(self, n: int = 3) -> Dict[str, float]:
        """Get the top N strongest emotions"""
        sorted_emotions = sorted(self.emotions.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_emotions[:n])
    
    def get_mood_description(self) -> str:
        """Get a natural language description of current mood"""
        top_3 = self.get_top_emotions(3)
        
        emotions_list = []
        for emotion, value in top_3.items():
            if value > 0.6:
                intensity = "very"
            elif value > 0.4:
                intensity = "moderately"
            else:
                intensity = "slightly"
            emotions_list.append(f"{intensity} {emotion}")
        
        return ", ".join(emotions_list)
    
    def manual_set_emotion(self, emotion: str, value: float):
        """Manually set an emotion (for commands)"""
        if emotion in self.emotions:
            self.emotions[emotion] = max(0.0, min(1.0, value))
            self.save_state()
    
    def boost_emotion(self, emotion: str, amount: float = 0.3):
        """Boost a specific emotion (for events like raids, subs)"""
        self._adjust_emotion(emotion, amount)
        self.save_state()
    
    def reset_to_baseline(self):
        """Reset all emotions to baseline"""
        self._initialize_emotions()
        self.last_update = time.time()
        self.save_state()


# --- Global instance ---
_emotional_state = None

def get_emotional_system() -> EmotionalState:
    """Get the global emotional system instance"""
    global _emotional_state
    if _emotional_state is None:
        _emotional_state = EmotionalState()
    return _emotional_state


# --- Convenience functions for backward compatibility ---
def process_chat_emotion(message: str, sentiment: float = 0.0):
    """Process a chat message's emotional impact"""
    system = get_emotional_system()
    system.process_message(message, sentiment)


def get_current_emotion() -> str:
    """Get the dominant emotion (for mood display)"""
    system = get_emotional_system()
    return system.get_dominant_emotion()


def get_emotion_state() -> Dict[str, float]:
    """Get all emotion values"""
    system = get_emotional_system()
    return system.get_emotional_state()


def boost_emotion(emotion: str, amount: float = 0.3):
    """Boost an emotion (for special events)"""
    system = get_emotional_system()
    system.boost_emotion(emotion, amount)


def reset_emotions():
    """Reset all emotions to baseline"""
    system = get_emotional_system()
    system.reset_to_baseline()


# --- Example usage ---
if __name__ == "__main__":
    print("=" * 60)
    print("MedlarTV Advanced Emotional System - Demo")
    print("=" * 60)
    
    emo = EmotionalState()
    
    print("\n--- Initial State ---")
    print(f"Dominant: {emo.get_dominant_emotion()}")
    print(f"Top 3: {emo.get_top_emotions(3)}")
    
    print("\n--- Processing Messages ---")
    messages = [
        ("OMG THIS IS AMAZING!", 0.9),
        ("I'm so happy to be here!", 0.8),
        ("Ugh this is frustrating", -0.6),
        ("Thanks so much for the help!", 0.7),
        ("I'm tired and stressed", -0.4),
    ]
    
    for msg, sentiment in messages:
        print(f"\nMessage: '{msg}'")
        emo.process_message(msg, sentiment)
        print(f"Dominant: {emo.get_dominant_emotion()}")
        print(f"Top 3: {emo.get_top_emotions(3)}")
        print(f"Description: {emo.get_mood_description()}")
    
    print("\n--- Testing Decay (5 seconds) ---")
    time.sleep(5)
    emo.apply_decay()
    print(f"After decay - Dominant: {emo.get_dominant_emotion()}")
    print(f"Top 3: {emo.get_top_emotions(3)}")