"""
MedlarTV Fuzzy Trigger Detection
Detects mentions of MedlarTV even with typos, case variations, and misspellings.
"""

import re
from difflib import SequenceMatcher


# --- Core Trigger Words ---
PRIMARY_TRIGGERS = [
    "medlartv",
    "medlar",
    "medlr",
    "medlr tv",
    "medlar tv"
]

# Common variations/nicknames
SECONDARY_TRIGGERS = [
    "med",
    "meddy",
    "mtv",
    "medlarbot",
    "medbot"
]


def calculate_similarity(a: str, b: str) -> float:
    """Calculate similarity ratio between two strings (0.0 to 1.0)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def normalize_text(text: str) -> str:
    """Normalize text by removing special characters and extra spaces."""
    # Remove special characters except spaces
    text = re.sub(r'[^a-z0-9\s]', '', text.lower())
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def check_keyboard_distance(word: str, target: str, max_distance: int = 1) -> bool:
    """
    Check if word is close to target considering keyboard layout.
    Helps detect accidental key presses (e.g., nedlar instead of medlar).
    """
    # Keyboard adjacency map (QWERTY layout)
    keyboard = {
        'q': ['w', 'a'], 'w': ['q', 'e', 's'], 'e': ['w', 'r', 'd'],
        'r': ['e', 't', 'f'], 't': ['r', 'y', 'g'], 'y': ['t', 'u', 'h'],
        'u': ['y', 'i', 'j'], 'i': ['u', 'o', 'k'], 'o': ['i', 'p', 'l'],
        'p': ['o', 'l'],
        'a': ['q', 's', 'z'], 's': ['a', 'w', 'd', 'x'], 'd': ['s', 'e', 'f', 'c'],
        'f': ['d', 'r', 'g', 'v'], 'g': ['f', 't', 'h', 'b'], 'h': ['g', 'y', 'j', 'n'],
        'j': ['h', 'u', 'k', 'm'], 'k': ['j', 'i', 'l'], 'l': ['k', 'o', 'p'],
        'z': ['a', 'x'], 'x': ['z', 's', 'c'], 'c': ['x', 'd', 'v'],
        'v': ['c', 'f', 'b'], 'b': ['v', 'g', 'n'], 'n': ['b', 'h', 'm'],
        'm': ['n', 'j']
    }
    
    if len(word) != len(target):
        return False
    
    differences = 0
    for i, (w_char, t_char) in enumerate(zip(word.lower(), target.lower())):
        if w_char != t_char:
            # Check if they're adjacent on keyboard
            if w_char not in keyboard or t_char not in keyboard.get(w_char, []):
                differences += 1
            if differences > max_distance:
                return False
    
    return differences <= max_distance


def check_missing_letters(word: str, target: str, max_missing: int = 2) -> bool:
    """
    Check if word is target with missing letters.
    Example: medltv -> medlartv (missing 'ar')
    """
    if len(word) >= len(target):
        return False
    
    word_lower = word.lower()
    target_lower = target.lower()
    
    # Try to match word as subsequence of target
    target_idx = 0
    for char in word_lower:
        while target_idx < len(target_lower) and target_lower[target_idx] != char:
            target_idx += 1
        if target_idx >= len(target_lower):
            return False
        target_idx += 1
    
    missing = len(target) - len(word)
    return missing <= max_missing


def check_extra_letters(word: str, target: str, max_extra: int = 2) -> bool:
    """
    Check if word is target with extra letters.
    Example: meedlartv -> medlartv (extra 'e')
    """
    if len(word) <= len(target):
        return False
    
    return check_missing_letters(target, word, max_extra)


def check_swapped_letters(word: str, target: str) -> bool:
    """
    Check if word has adjacent letters swapped.
    Example: mdelartv -> medlartv (swapped 'ed')
    """
    if len(word) != len(target):
        return False
    
    word_lower = word.lower()
    target_lower = target.lower()
    
    swaps = 0
    i = 0
    while i < len(word_lower):
        if word_lower[i] != target_lower[i]:
            # Check if next chars are swapped
            if (i + 1 < len(word_lower) and 
                word_lower[i] == target_lower[i + 1] and 
                word_lower[i + 1] == target_lower[i]):
                swaps += 1
                i += 2  # Skip both swapped chars
                continue
            else:
                return False
        i += 1
    
    return swaps <= 2


def is_trigger_word(word: str, strict: bool = False) -> bool:
    """
    Main function to check if a word is a trigger.
    
    Args:
        word: The word to check
        strict: If True, only check exact matches and close variations
    
    Returns:
        True if word should trigger MedlarTV
    """
    normalized = normalize_text(word)
    
    # Empty or too short
    if not normalized or len(normalized) < 3:
        return False
    
    # --- EXACT MATCHES ---
    # Check primary triggers (exact match, case-insensitive)
    for trigger in PRIMARY_TRIGGERS:
        if normalized == normalize_text(trigger):
            return True
    
    # Check secondary triggers
    if not strict:
        for trigger in SECONDARY_TRIGGERS:
            if normalized == normalize_text(trigger):
                return True
    
    # --- FUZZY MATCHES ---
    if strict:
        return False
    
    # Check each primary trigger for fuzzy matches
    for trigger in PRIMARY_TRIGGERS:
        trigger_norm = normalize_text(trigger)
        
        # High similarity (>= 85%)
        if calculate_similarity(normalized, trigger_norm) >= 0.85:
            return True
        
        # Keyboard typos (1 key away)
        if check_keyboard_distance(normalized, trigger_norm, max_distance=1):
            return True
        
        # Missing letters (up to 2)
        if check_missing_letters(normalized, trigger_norm, max_missing=2):
            return True
        
        # Extra letters (up to 2)
        if check_extra_letters(normalized, trigger_norm, max_extra=2):
            return True
        
        # Swapped adjacent letters
        if check_swapped_letters(normalized, trigger_norm):
            return True
    
    return False


def find_triggers_in_message(message: str, strict: bool = False) -> list:
    """
    Find all trigger words in a message.
    
    Args:
        message: The chat message to check
        strict: If True, only find exact/close matches
    
    Returns:
        List of detected trigger words
    """
    # Split message into words
    words = re.findall(r'\b\w+\b', message)
    
    # Also check multi-word combinations (e.g., "medlar tv")
    message_normalized = normalize_text(message)
    
    triggers_found = []
    
    # Check individual words
    for word in words:
        if is_trigger_word(word, strict):
            triggers_found.append(word)
    
    # Check multi-word triggers
    for trigger in PRIMARY_TRIGGERS:
        if ' ' in trigger:  # Multi-word trigger
            trigger_norm = normalize_text(trigger)
            if trigger_norm in message_normalized:
                triggers_found.append(trigger)
    
    return triggers_found


def should_respond(message: str, strict: bool = False) -> bool:
    """
    Determine if MedlarTV should respond to this message.
    
    Args:
        message: The chat message
        strict: If True, only respond to exact/close mentions
    
    Returns:
        True if message contains trigger words
    """
    return len(find_triggers_in_message(message, strict)) > 0


# --- TESTING / DEMO ---
def test_fuzzy_trigger():
    """Test cases for fuzzy trigger detection."""
    test_cases = [
        # (input, should_trigger, description)
        ("medlartv", True, "Exact match"),
        ("MEDLARTV", True, "All uppercase"),
        ("MeDlArTv", True, "Mixed case"),
        ("medlar", True, "Short form"),
        ("@medlartv", True, "With @ symbol"),
        ("medlartv!", True, "With punctuation"),
        ("medlrtv", True, "Missing 'a'"),
        ("medltv", True, "Missing 'ar'"),
        ("meedlartv", True, "Extra 'e'"),
        ("medlarttvv", True, "Extra letters at end"),
        ("mdelartv", True, "Swapped 'de'"),
        ("nedlartv", True, "Keyboard typo (n instead of m)"),
        ("medkartv", True, "Keyboard typo (k instead of l)"),
        ("medlarvt", True, "Swapped 'tv'"),
        ("medlar tv", True, "With space"),
        ("med", True, "Nickname"),
        ("mtv", True, "Abbreviation"),
        ("hey medlartv!", True, "In sentence"),
        ("medlartv is awesome", True, "Start of sentence"),
        ("call medlartv", True, "Middle of sentence"),
        ("random text", False, "No trigger"),
        ("medical", False, "Similar but wrong word"),
        ("me", False, "Too short"),
    ]
    
    print("=" * 60)
    print("MedlarTV Fuzzy Trigger Detection - Test Results")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for text, expected, description in test_cases:
        result = should_respond(text)
        status = "0" if result == expected else "1"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} {description:30s} | '{text:20s}' → {result}")
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed ({passed}/{len(test_cases)})")
    print("=" * 60)


if __name__ == "__main__":
    test_fuzzy_trigger()