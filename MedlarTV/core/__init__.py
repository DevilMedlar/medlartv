"""
MedlarTV Core Module
Contains the brain, memory, sentiment analysis, context tracking, and all new features
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

# Translation Module
from .translation import (
    detect_language,
    translate_phrase,
    translate_message,
    get_multilingual_greeting,
    get_multilingual_thanks,
    add_language_indicator
)

# Response Templates Module
from .response_templates import (
    get_template,
    get_greeting,
    get_agreement,
    get_hype,
    get_support,
    get_sarcastic,
    get_smart_response
)

# Interaction Logger Module
from .interaction_logger import (
    log_interaction,
    log_command,
    log_mood_change,
    log_error,
    get_interaction_stats
)

# Moderation Module
from .moderation import (
    check_message,
    execute_timeout,
    execute_ban,
    execute_delete,
    handle_mod_command,
    is_mod_command,
    load_link_whitelist,
    get_user_timeout_count
)

# Stream Management Module
from .stream_management import (
    get_stream_info,
    get_channel_info,
    update_stream_title,
    update_stream_category,
    search_game,
    get_top_games,
    format_stream_info
)

# Twitch Events Module
from .twitch_events import (
    detect_raid,
    detect_subscription,
    detect_channel_point_redemption,
    detect_bits,
    get_raid_response,
    get_sub_response,
    get_channel_point_response,
    get_bits_response,
    load_global_emotes,
    load_channel_emotes,
    add_random_emote,
    extract_emotes_from_message
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
    
    # Translation
    'detect_language',
    'translate_phrase',
    'translate_message',
    'get_multilingual_greeting',
    'get_multilingual_thanks',
    'add_language_indicator',
    
    # Response Templates
    'get_template',
    'get_greeting',
    'get_agreement',
    'get_hype',
    'get_support',
    'get_sarcastic',
    'get_smart_response',
    
    # Interaction Logging
    'log_interaction',
    'log_command',
    'log_mood_change',
    'log_error',
    'get_interaction_stats',
    
    # Moderation
    'check_message',
    'execute_timeout',
    'execute_ban',
    'execute_delete',
    'handle_mod_command',
    'is_mod_command',
    'load_link_whitelist',
    'get_user_timeout_count',
    
    # Stream Management
    'get_stream_info',
    'get_channel_info',
    'update_stream_title',
    'update_stream_category',
    'search_game',
    'get_top_games',
    'format_stream_info',
    
    # Twitch Events
    'detect_raid',
    'detect_subscription',
    'detect_channel_point_redemption',
    'detect_bits',
    'get_raid_response',
    'get_sub_response',
    'get_channel_point_response',
    'get_bits_response',
    'load_global_emotes',
    'load_channel_emotes',
    'add_random_emote',
    'extract_emotes_from_message',
]
