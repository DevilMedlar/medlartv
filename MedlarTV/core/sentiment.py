import re

# very simple lexical sentiment scale
POSITIVE = ["good", "great", "awesome", "love", "hype", "yay", "nice", "cool", "sweet", "fun"]
NEGATIVE = ["bad", "sad", "angry", "hate", "tired", "bored", "ugh", "annoyed", "lame"]
INTENSIFIERS = ["very", "so", "super", "really", "extremely"]

def analyze_sentiment(message: str) -> float:
    """Return sentiment from -1.0 (negative) to +1.0 (positive)."""
    text = message.lower()
    score = 0
    for w in POSITIVE:
        if re.search(rf"\b{w}\b", text):
            score += 1
    for w in NEGATIVE:
        if re.search(rf"\b{w}\b", text):
            score -= 1
    for i in INTENSIFIERS:
        if re.search(rf"\b{i}\b", text):
            score *= 1.5
    # clamp between -1 and 1
    return max(-1.0, min(1.0, score / 5))