"""
MedlarTV Enhanced Sentiment Analysis
Works with the advanced emotional system
"""

import re
from typing import Dict, Tuple

# --- Expanded Sentiment Lexicon ---
POSITIVE_WORDS = [
    "good", "great", "awesome", "amazing", "love", "wonderful", "fantastic",
    "excellent", "perfect", "best", "brilliant", "outstanding", "superb",
    "happy", "joy", "excited", "yay", "nice", "cool", "sweet", "fun",
    "pogchamp", "pog", "lit", "fire", "hype", "epic", "legendary"
]

NEGATIVE_WORDS = [
    "bad", "terrible", "awful", "horrible", "worst", "hate", "suck",
    "sad", "depressed", "cry", "hurt", "pain", "miss", "lonely",
    "angry", "mad", "annoyed", "frustrating", "ugh", "annoying",
    "tired", "exhausted", "stressed", "overwhelmed", "anxious", "worried",
    "scared", "afraid", "fear", "nervous", "disappointed", "lame"
]

INTENSIFIERS = [
    "very", "so", "super", "really", "extremely", "incredibly", "absolutely",
    "totally", "completely", "utterly", "exceptionally", "particularly"
]

NEGATIONS = ["not", "no", "never", "neither", "nobody", "nothing", "don't", "won't", "can't"]

# Emotion-specific word clusters
EMOTION_WORDS = {
    "happiness": ["happy", "joy", "cheerful", "glad", "pleased", "delighted", "smile", "laugh"],
    "sadness": ["sad", "unhappy", "depressed", "miserable", "gloomy", "down", "cry"],
    "anger": ["angry", "mad", "furious", "annoyed", "irritated", "pissed", "rage"],
    "fear": ["scared", "afraid", "fearful", "anxious", "worried", "nervous", "terrified"],
    "excitement": ["excited", "thrilled", "hyped", "pumped", "stoked", "omg", "wow"],
    "gratitude": ["thanks", "thank you", "grateful", "appreciate", "thankful"],
    "jealousy": ["jealous", "envy", "envious", "wish i had"],
    "pride": ["proud", "accomplished", "achievement", "nailed it", "crushed it"],
}

# Emoji sentiment mapping
EMOJI_SENTIMENT = {
    "😊": 0.5, "😀": 0.6, "😁": 0.7, "🤣": 0.8, "❤️": 0.7, "💖": 0.7,
    "😢": -0.5, "😭": -0.7, "😞": -0.4, "😔": -0.4,
    "😠": -0.6, "😡": -0.8, "🤬": -0.9,
    "😱": -0.6, "😨": -0.5, "😰": -0.5,
    "🔥": 0.6, "⚡": 0.5, "✨": 0.4, "💯": 0.6,
    "🙄": -0.3, "😒": -0.4, "😤": -0.5,
}


def analyze_sentiment_advanced(message: str) -> Tuple[float, Dict[str, float]]:
    """
    Advanced sentiment analysis with emotion detection
    
    Args:
        message: Chat message to analyze
    
    Returns:
        Tuple of (overall_sentiment, emotion_scores)
        - overall_sentiment: -1.0 (very negative) to 1.0 (very positive)
        - emotion_scores: Dict of detected emotions and their strengths
    """
    text = message.lower()
    words = re.findall(r'\b\w+\b', text)
    
    # --- Overall Sentiment Score ---
    score = 0.0
    word_count = 0
    
    # Check for negations
    negated = False
    for i, word in enumerate(words):
        # Check if word is negated
        if i > 0 and words[i-1] in NEGATIONS:
            negated = True
        else:
            negated = False
        
        # Positive words
        if word in POSITIVE_WORDS:
            word_count += 1
            score += -1 if negated else 1
        
        # Negative words
        elif word in NEGATIVE_WORDS:
            word_count += 1
            score += 1 if negated else -1  # Negated negative = positive
        
        # Intensifiers multiply nearby sentiment
        elif word in INTENSIFIERS and i < len(words) - 1:
            next_word = words[i + 1]
            if next_word in POSITIVE_WORDS:
                score += 0.5
            elif next_word in NEGATIVE_WORDS:
                score -= 0.5
    
    # Check for emojis
    emoji_score = 0.0
    emoji_count = 0
    for emoji, value in EMOJI_SENTIMENT.items():
        if emoji in message:
            emoji_score += value
            emoji_count += 1
    
    # Combine word and emoji sentiment
    total_count = word_count + emoji_count
    if total_count > 0:
        combined_score = (score + emoji_score) / total_count
    else:
        combined_score = 0.0
    
    # Clamp between -1 and 1
    overall_sentiment = max(-1.0, min(1.0, combined_score))
    
    # --- Emotion Detection ---
    emotion_scores = {}
    
    for emotion, emotion_keywords in EMOTION_WORDS.items():
        matches = sum(1 for keyword in emotion_keywords if keyword in text)
        if matches > 0:
            # Emotion strength based on keyword frequency and overall sentiment
            strength = min(matches * 0.15, 0.5)
            
            # Adjust by overall sentiment
            if emotion in ["happiness", "excitement", "gratitude", "pride"]:
                if overall_sentiment > 0:
                    strength *= (1 + overall_sentiment * 0.5)
            elif emotion in ["sadness", "anger", "fear"]:
                if overall_sentiment < 0:
                    strength *= (1 + abs(overall_sentiment) * 0.5)
            
            emotion_scores[emotion] = min(strength, 1.0)
    
    return overall_sentiment, emotion_scores


def analyze_sentiment_simple(message: str) -> float:
    """
    Simple sentiment analysis (backward compatible)
    
    Returns:
        Sentiment score from -1.0 to 1.0
    """
    sentiment, _ = analyze_sentiment_advanced(message)
    return sentiment


def detect_emotional_keywords(message: str) -> Dict[str, int]:
    """
    Detect which emotions are mentioned in a message
    
    Returns:
        Dict of emotions and how many keywords matched
    """
    text = message.lower()
    detected = {}
    
    for emotion, keywords in EMOTION_WORDS.items():
        matches = sum(1 for keyword in keywords if keyword in text)
        if matches > 0:
            detected[emotion] = matches
    
    return detected


def get_sentiment_description(sentiment: float) -> str:
    """Get a text description of sentiment score"""
    if sentiment >= 0.7:
        return "very positive"
    elif sentiment >= 0.3:
        return "positive"
    elif sentiment >= -0.3:
        return "neutral"
    elif sentiment >= -0.7:
        return "negative"
    else:
        return "very negative"


# --- Example usage ---
if __name__ == "__main__":
    print("=" * 60)
    print("Enhanced Sentiment Analysis - Demo")
    print("=" * 60)
    
    test_messages = [
        "OMG this is absolutely amazing! I love it! 🔥",
        "I'm so sad and lonely right now 😢",
        "This is frustrating and annoying ugh",
        "Thanks so much! You're the best! ❤️",
        "Not bad, actually pretty good!",
        "I'm excited but also nervous 😰",
        "This sucks, I hate it",
        "Just chilling, nothing special",
    ]
    
    for msg in test_messages:
        sentiment, emotions = analyze_sentiment_advanced(msg)
        print(f"\nMessage: '{msg}'")
        print(f"Sentiment: {sentiment:.2f} ({get_sentiment_description(sentiment)})")
        if emotions:
            print(f"Emotions: {emotions}")
        else:
            print("Emotions: None detected")