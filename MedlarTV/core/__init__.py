"""
MedlarTV Core Module
Contains the brain, memory, sentiment analysis, and context tracking.
"""

from .memory import (
    load_memory,
    save_memory,
    record_mood,
    get_dominant_mood,
    get_dominant_weighted_mood,
    reset_memory_on_shutdown
)

from .llm_brain import (
    generate_response,
    check_ollama_health,
    clear_history
)

from .context import (
    record_session_mood,
    get_contextual_mix
)

from .expression import blended_phrase
from .sentiment import analyze_sentiment
from .fuzzy_trigger import (
    should_respond as fuzzy_should_respond,
    find_triggers_in_message,
    is_trigger_word
)

__all__ = [
    # Memory functions
    'load_memory',
    'save_memory',
    'record_mood',
    'get_dominant_mood',
    'get_dominant_weighted_mood',
    'reset_memory_on_shutdown',
    
    # LLM Brain functions
    'generate_response',
    'check_ollama_health',
    'clear_history',
    
    # Context functions
    'record_session_mood',
    'get_contextual_mix',
    
    # Expression & Sentiment
    'blended_phrase',
    'analyze_sentiment',
    
    # Fuzzy Trigger Detection
    'fuzzy_should_respond',
    'find_triggers_in_message',
    'is_trigger_word',
]
