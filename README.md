# MedlarTV — Tactical AI Companion

Local AI with dynamic personality, Twitch integration, emotion-driven replies, and stream utilities.

## Overview
- Real-time Twitch chat listener that responds contextually and safely.
- Emotion/mood engine drives emotes and tone across replies.
- Command system with both code-defined handlers and a static command catalog site.
- Stream management helpers (title/category), moderation, timers, and event effects.

## Quick Start (Windows)
- Install Python 3.11+.
- Create a virtual environment and install dependencies:
  - `python -m venv .venv`
  - `.venv\Scripts\pip install -r requirements.txt`
- Set required environment variables (see “Twitch Setup”).
- Launch all services:
  - `python launcher.py`

## Twitch Setup
- Required environment variables:
  - `MEDLARTV_TWITCH_TOKEN`: Bot OAuth token (prefixed `oauth:` is ok).
  - `TWITCH_NICK`: Bot username (default `MedlarTV`).
  - `TWITCH_CHANNEL`: Target channel (e.g., `#devilmedlar`).
  - `APP_TWITCH_CLIENT_ID`: Twitch application client ID.
  - Optional: `DEVILMEDLAR_TWITCH_TOKEN` (App/Broadcaster token for channel APIs).
- The IRC listener connects and decorates replies with mood-aware emotes.
  - Source: `MedlarTV/tools/twitch_listener.py`

## Components
- Core API: `MedlarTV/core/main.py` (FastAPI; used by the brain and tools).
- Twitch Listener: `MedlarTV/tools/twitch_listener.py` (connects to IRC, processes chat).
- Avatar Bridge (optional): `MedlarTV/avatar/bridge/server.py` and `avatar_client/console_client.py`.
- Emotional System: `MedlarTV/core/emotional_system.py` (state, baselines, decay, influences).
- Sentiment Lexicon: `MedlarTV/core/sentiment_advanced.py` (keyword clusters, intensifiers).
- Emote Selector: `MedlarTV/core/emotion_emote_selector.py` (maps emotions to emotes).
- Mood Vector: `MedlarTV/core/mood_system.py` (valence, energy, warmth, snark).
- Moderation/Filter: `MedlarTV/core/content_filter.py` and `core/moderation.py`.
- Stream Management: `MedlarTV/core/stream_management.py`.
- Command Handlers: `MedlarTV/core/command_handlers.py`.
- Command Catalog Builder: `MedlarTV/tools/build_commands_site.py`.

## Commands — Add/Remove
- Code-defined commands live in `MedlarTV/core/command_handlers.py`.
  - Add a handler function and register it in `COMMAND_REGISTRY` with permissions and optional usage.
  - Example template is included in the file.
  - The listener routes `!<command>` via `execute_command(...)`.
- Static command catalog lives in `MedlarTV/config/commands.yaml`.
  - Used to generate a public catalog site (see “Command Catalog Site”).
  - Each entry: `name: { response, allowed_roles, description, usage }`.
- Remove a command by deleting its registry entry (code) and/or YAML section.
- Reply for `!commands` is served by the handler; the catalog URL can be configured via environment or YAML.

## Command Catalog Site
- Build a static site from `MedlarTV/config/commands.yaml`:
  - `python MedlarTV/tools/build_commands_site.py --out commands_site`
  - Publish `commands_site` folder (e.g., GitHub Pages).
- The Twitch auto-reply and `!commands` can point to this site.
  - Environment fallback: `MEDLAR_COMMANDS_URL`.
  - YAML fallback: the URL parsed from the `commands` entry in `config/commands.yaml`.

## Emotions & Moods — Add/Align
- Add a new emotion across four places to keep consistency:
  - Defaults and baselines: `MedlarTV/core/emotional_system.py` → `DEFAULT_EMOTIONS` and `EMOTION_INFLUENCES`.
  - Sentiment keywords: `MedlarTV/core/sentiment_advanced.py` → `EMOTION_WORDS`.
  - Emote mapping: `MedlarTV/core/emotion_emote_selector.py` → `EMOTION_EMOTE_MAP`.
  - Mood contributions: `MedlarTV/core/mood_system.py` → include in energy/warmth where appropriate.
- After edits, run `python -m compileall -q MedlarTV` to validate syntax.

## Adjusting Weights & Behavior
- Baselines/Decay (per emotion):
  - Create `MedlarTV/config/emotions.yaml` to override code defaults.
  - Structure:
    ```yaml
    emotions:
      happiness: { baseline: 0.4, decay: 0.92 }
      arousal:   { baseline: 0.05, decay: 0.90 }
    ```
- Influence Graph (how one emotion affects others):
  - Edit `EMOTION_INFLUENCES` in `MedlarTV/core/emotional_system.py`.
  - Keep weights gentle; changes ripple through expression.
- Personality Trait Multipliers:
  - `MedlarTV/config/personality.yaml` → under `traits`, set per-emotion scaling (e.g., `supportive: 1.2`).
- Mood Labels and Vector:
  - Adjust logic in `MedlarTV/core/mood_system.py` for how emotions map to valence/energy/warmth/snark.
- Memory/Mood Weights (optional):
  - `MedlarTV/data/memory.yaml` can store mood weight preferences for some systems.

## Moderation & Safety
- Configure `MedlarTV/config/content_filter.yaml`:
  - `blocked_words`, `blocked_topics`, `response_modes`, `safety` (cooldowns, emoji limits).
- Link whitelist: `MedlarTV/config/link_whitelist.yaml`.
- Auto-moderation flow in `MedlarTV/core/moderation.py`.

## Timers & Events
- Timers: `MedlarTV/config/timers.yaml` → periodic chat messages by time or chat count.
- Event rules: `MedlarTV/config/events.yaml` → Firebot-like effects (chat, shoutout, play sound) triggered on joins or custom events.
- Co-Pilots: `MedlarTV/config/copilots.yaml` and chat commands `!addcopilot`, `!removecopilot`, `!listcopilots`.

## Mood-Aware Replies
- All outgoing messages pass through decoration to append an emote based on current emotion.
  - Source: `MedlarTV/tools/twitch_listener.py`.
  - Emote mapping: `MedlarTV/core/emotion_emote_selector.py`.

## Logging & Diagnostics
- Interaction logs in `logs/` directory (JSONL files).
- Toggle logging via `ENABLE_INTERACTION_LOGGING` env var.
- Health checks: `!status` summarizes subsystem readiness.

## Environment Reference (Common)
- `MEDLARTV_TWITCH_TOKEN`, `TWITCH_NICK`, `TWITCH_CHANNEL`, `APP_TWITCH_CLIENT_ID`.
- `MEDLARTV_DEBUG=true` to enable verbose diagnostics.
- `ENABLE_EMOTE_RESPONSES`, `ENABLE_RAID_DETECTION`, `ENABLE_SUB_DETECTION`, `ENABLE_CHANNEL_POINTS` (feature flags).
- `MEDLAR_COMMANDS_URL` to set the command catalog link.

## Launch Details
- `launcher.py` starts Ollama, optional LibreTranslate, Avatar Bridge, Core API.
- Twitch Listener can be run via the Core or independently; launcher starts main systems and monitors them.

## Development Tips
- Keep emotion names consistent across emotional system, sentiment, emotes, and mood logic.
- Prefer configuration files in `MedlarTV/config/` for safe runtime tweaks.
- Follow existing code style and use small, incremental changes; validate with `compileall` before launching.

## Safety Notes
- Never hardcode secrets in code or YAML; use environment variables.
- Respect Twitch rate limits and message length (≤500 chars).

## Troubleshooting
- Verify tokens and client ID env vars.
- Check `logs/*.log` produced by `launcher.py` for startup issues.
- Use `MEDLARTV_DEBUG=true` to surface detailed diagnostics during development.
