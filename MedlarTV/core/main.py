import os
if os.getenv("MEDLARTV_DEBUG", "false").lower() == "true":
    print("[DEBUG main] Loaded main.py")

"""
MedlarTV Main Entry Point (Refactored)
-------------------------------------
Clean initialization, clean shutdown, no duplicate systems, and perfect 
integration with the refactored Twitch listener, LLM brain, moderation, 
and event handlers.
...
"""

import logging
import os
from pathlib import Path
from dotenv import load_dotenv
import signal
import sys
import time
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
import yaml
from MedlarTV.core.settings import get_settings, update_settings

load_dotenv()

from MedlarTV.tools.twitch_listener import start_listener, stop_listener
from MedlarTV.core.emotional_system import get_emotional_system
from MedlarTV.core.memory import load_memory
from MedlarTV.core.stream_management import verify_twitch_tokens
from MedlarTV.core.llm_brain import generate_response
from MedlarTV.core.mood_system import compute_mood, get_mood_label
from MedlarTV.core.content_filter import filter_message, get_safety_response

log = logging.getLogger("main")
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


BOOT_BANNER = r"""
╔══════════════════════════════════════════════════════════╗
║                    MEDLAR  TACTICAL  AI                 ║
╚══════════════════════════════════════════════════════════╝
"""

APP = FastAPI(title="MedlarTV Commands", version="1.0.0")

def _load_commands_yaml() -> Dict[str, Any]:
    try:
        cfg = Path(__file__).resolve().parents[1] / "config" / "commands.yaml"
        with cfg.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data.get("commands", {})
    except Exception:
        return {}

@APP.get("/api/commands")
def api_commands() -> JSONResponse:
    data = _load_commands_yaml()
    items = []
    for name, info in data.items():
        items.append({
            "name": str(name),
            "response": str(info.get("response", "")),
            "allowed_roles": list(map(str, info.get("allowed_roles", []))),
            "description": str(info.get("description", "")),
            "usage": str(info.get("usage", "")),
        })
    return JSONResponse({"commands": items}, headers={"Cache-Control": "no-store"})

@APP.get("/api/settings")
def api_get_settings() -> JSONResponse:
    return JSONResponse(get_settings(), headers={"Cache-Control": "no-store"})

@APP.post("/api/settings")
def api_update_settings(payload: Dict[str, Any]) -> JSONResponse:
    updated = update_settings(dict(payload or {}))
    return JSONResponse(updated, headers={"Cache-Control": "no-store"})

@APP.get("/settings")
def page_settings() -> HTMLResponse:
    html = """
    <!DOCTYPE html>
    <html lang=\"en\">
    <head>
      <meta charset=\"utf-8\" />
      <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
      <title>MedlarTV Settings</title>
      <style>
        :root { --bg:#0f1218; --card:#1a1f2b; --text:#e6e9ef; --muted:#9aa4b2; --accent:#6ae3ff; }
        body { margin:0; font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial; background:var(--bg); color:var(--text); }
        .container { max-width:720px; margin:24px auto; padding:0 16px; }
        .card { background:var(--card); border:1px solid #2b3242; border-radius:10px; padding:14px; }
        .row { display:flex; align-items:center; justify-content:space-between; padding:8px 0; }
        label { font-size:14px; }
      </style>
    </head>
    <body>
      <div class=\"container\">
        <h2>Settings</h2>
        <div class=\"card\">
          <div class=\"row\"><label>LLM Brain</label><input id=\"llm_brain\" type=\"checkbox\" /></div>
          <div class=\"row\"><label>Pokémon Auto-Catch</label><input id=\"pcg_auto_catch\" type=\"checkbox\" /></div>
          <div class=\"row\"><label>Ignore Viewer Poké Commands</label><input id=\"ignore_viewer_pokecatch\" type=\"checkbox\" /></div>
          <div class=\"row\"><label>Content Filter</label><input id=\"content_filter\" type=\"checkbox\" /></div>
          <div class=\"row\"><label>Timers</label><input id=\"timers\" type=\"checkbox\" /></div>
          <div class=\"row\"><label>Fuzzy Trigger</label><input id=\"fuzzy_trigger\" type=\"checkbox\" /></div>
        </div>
        <p style=\"margin-top:18px; font-size:12px; color:#8fa1b5\">Source: <a href=\"/api/settings\">/api/settings</a></p>
      </div>
      <script>
        async function load() {
          const r = await fetch('/api/settings', {cache:'no-store'});
          const s = await r.json();
          const keys = ['llm_brain','pcg_auto_catch','ignore_viewer_pokecatch','content_filter','timers','fuzzy_trigger'];
          for (const k of keys) {
            const el = document.getElementById(k);
            if (el) el.checked = !!s[k];
            if (el) el.onchange = async () => {
              const payload = {}; payload[k] = el.checked;
              await fetch('/api/settings', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
            };
          }
        }
        load();
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=200)

@APP.get("/commands")
def page_commands() -> HTMLResponse:
    html = """
    <!DOCTYPE html>
    <html lang=\"en\">
    <head>
      <meta charset=\"utf-8\" />
      <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
      <title>MedlarTV Commands</title>
      <style>
        :root { --bg:#0f1218; --card:#1a1f2b; --text:#e6e9ef; --muted:#9aa4b2; --accent:#6ae3ff; }
        body { margin:0; font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial; background:var(--bg); color:var(--text); }
        header { padding:20px 24px; border-bottom:1px solid #222633; display:flex; align-items:center; gap:12px; }
        header h1 { margin:0; font-size:18px; letter-spacing:.4px; }
        .container { max-width:960px; margin:24px auto; padding:0 16px; }
        .controls { display:flex; gap:12px; margin-bottom:16px; }
        input, select { background:var(--card); border:1px solid #2b3242; color:var(--text); padding:10px 12px; border-radius:8px; outline:none; }
        .grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(280px,1fr)); gap:14px; }
        .card { background:var(--card); border:1px solid #2b3242; border-radius:10px; padding:14px; }
        .name { font-weight:600; font-size:15px; }
        .roles { margin-top:6px; color:var(--muted); font-size:12px; }
        .desc { margin-top:8px; font-size:13px; color:var(--text); }
        .usage { margin-top:6px; font-size:12px; color:var(--muted); }
        .response { margin-top:10px; font-size:12px; color:#c8d2e0; border-top:1px dashed #2b3242; padding-top:8px; }
        .badge { display:inline-block; padding:3px 8px; border-radius:999px; background:#253047; color:#bfe8ff; margin-right:6px; font-size:11px; }
        .empty { color:var(--muted); text-align:center; padding:24px; }
        a { color:var(--accent); text-decoration:none; }
      </style>
    </head>
    <body>
      <header>
        <svg width=\"20\" height=\"20\" viewBox=\"0 0 24 24\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\"><path d=\"M12 2L2 7l10 5 10-5-10-5zm0 7l-10 5 10 5 10-5-10-5z\" fill=\"#6ae3ff\"/></svg>
        <h1>MedlarTV Command Catalog</h1>
      </header>
      <div class=\"container\">
        <div class=\"controls\">
          <input id=\"q\" type=\"text\" placeholder=\"Search commands…\" />
          <select id=\"role\">
            <option value=\"\">All roles</option>
            <option>everybody</option>
            <option>pilot</option>
            <option>copilot</option>
            <option>mod</option>
            <option>vip</option>
          </select>
        </div>
        <div id=\"grid\" class=\"grid\"></div>
        <div id=\"empty\" class=\"empty\" style=\"display:none\">No commands match your filters.</div>
        <p style=\"margin-top:18px; font-size:12px; color:#8fa1b5\">Source: <a href=\"/api/commands\">/api/commands</a></p>
      </div>
      <script>
        const state = { commands: [], q: '', role: '' };
        const grid = document.getElementById('grid');
        const empty = document.getElementById('empty');
        const q = document.getElementById('q');
        const role = document.getElementById('role');

        q.addEventListener('input', () => { state.q = q.value.toLowerCase(); render(); });
        role.addEventListener('change', () => { state.role = role.value; render(); });

        function matches(cmd) {
          const name = cmd.name.toLowerCase();
          const desc = (cmd.description||'').toLowerCase();
          const usage = (cmd.usage||'').toLowerCase();
          const text = name + ' ' + desc + ' ' + usage;
          const roleOk = !state.role || (cmd.allowed_roles||[]).includes(state.role);
          const queryOk = !state.q || text.includes(state.q);
          return roleOk && queryOk;
        }

        function render() {
          const list = state.commands.filter(matches);
          grid.innerHTML = '';
          if (!list.length) { empty.style.display = 'block'; return; } else { empty.style.display = 'none'; }
          for (const c of list) {
            const roles = (c.allowed_roles||[]).map(r => `<span class=\"badge\">${r}</span>`).join(' ');
            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = `
              <div class=\"name\">!${c.name}</div>
              <div class=\"roles\">${roles || '<span class=\"badge\">everybody</span>'}</div>
              ${c.description ? `<div class=\"desc\">${c.description}</div>` : ''}
              ${c.usage ? `<div class=\"usage\"><strong>Usage:</strong> ${c.usage}</div>` : ''}
              ${c.response ? `<div class=\"response\"><strong>Response:</strong> ${c.response}</div>` : ''}
            `;
            grid.appendChild(card);
          }
        }

        async function refetch() {
          try {
            const r = await fetch('/api/commands', {cache:'no-store'});
            const j = await r.json();
            const next = j.commands || [];
            // Compare by length and names; update if different
            const prev = state.commands;
            const changed = prev.length !== next.length ||
              prev.some((c, i) => !next[i] || next[i].name !== c.name || JSON.stringify(next[i]) !== JSON.stringify(c));
            if (changed) { state.commands = next; render(); }
          } catch (e) { /* ignore network errors */ }
        }

        refetch();
        setInterval(refetch, 5000);
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=200)


# api_chat removed


## filter endpoints removed


## personality endpoints removed


## startup/shutdown hooks removed


def configure_logging():
    log_dir = os.getenv("LOG_DIRECTORY", "logs")
    base = Path.cwd() / log_dir
    try:
        base.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    fmt = logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S")

    targets = {
        "twitch_listener": base / "twitch_listener_log.txt",
        "commands": base / "command_handler.txt",
        "fuzzy_trigger": base / "fuzzy_trigger.txt",
        "stream": base / "stream_management.txt",
        "emotions": base / "emotions.txt",
        "mood": base / "mood_system.txt",
        "llm_brain": base / "llm_brain.txt",
        "memory": base / "memory.txt",
        "main": base / "main.txt",
    }

    for name, path in targets.items():
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        exists = any(isinstance(h, logging.FileHandler) and getattr(h, "_medlar_path", None) == str(path) for h in logger.handlers)
        if exists:
            continue
        try:
            fh = logging.FileHandler(path, encoding="utf-8")
            setattr(fh, "_medlar_path", str(path))
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(fmt)
            logger.addHandler(fh)
        except Exception:
            pass

def initialize_systems():
    log.info("[SYSTEM] Initializing MedlarTV core…")
    if os.getenv("MEDLARTV_DEBUG", "false").lower() == "true":
        print("[DEBUG main] initialize_systems() called")

    try:
        if os.getenv("MEDLARTV_DEBUG", "false").lower() == "true":
            print("[DEBUG main] initializing emotional system…")
        from MedlarTV.core.emotional_system import get_emotional_system
        get_emotional_system()
        if os.getenv("MEDLARTV_DEBUG", "false").lower() == "true":
            print("[DEBUG main] emotional system initialized successfully")
        log.info("[OK] Emotional system initialized")
    except Exception as e:
        log.error(f"[FAIL] Emotional system failed: {e}")

    try:
        if os.getenv("MEDLARTV_DEBUG", "false").lower() == "true":
            print("[DEBUG main] loading memory…")
        load_memory()
        if os.getenv("MEDLARTV_DEBUG", "false").lower() == "true":
            print("[DEBUG main] memory loaded successfully")
        log.info("[OK] Memory loaded")
    except Exception as e:
        log.error(f"[FAIL] Memory load failed: {e}")

    try:
        if os.getenv("MEDLARTV_DEBUG", "false").lower() == "true":
            print("[DEBUG main] verifying twitch tokens…")
        verified = verify_twitch_tokens()
        if verified:
            if os.getenv("MEDLARTV_DEBUG", "false").lower() == "true":
                print("[DEBUG main] twitch tokens verified")
            log.info("[OK] Twitch tokens verified")
        else:
            if os.getenv("MEDLARTV_DEBUG", "false").lower() == "true":
                print("[DEBUG main] twitch tokens verification failed")
            log.error("[FAIL] Twitch token verification failed")
    except Exception as e:
        log.error(f"[FAIL] Twitch token verification failed: {e}")

def shutdown(*_):
    if os.getenv("MEDLARTV_DEBUG", "false").lower() == "true":
        print("[DEBUG main] shutdown() triggered")
    log.info("\n[SYSTEM] Shutting down MedlarTV…")
    try:
        if os.getenv("MEDLARTV_DEBUG", "false").lower() == "true":
            print("[DEBUG main] stopping twitch listener…")
        stop_listener()
        if os.getenv("MEDLARTV_DEBUG", "false").lower() == "true":
            print("[DEBUG main] twitch listener stopped")
    except Exception as e:
        log.error(f"[Shutdown] Listener stop failed: {e}")

    log.info("[SYSTEM] All systems offline.")
    sys.exit(0)

def main():
    if os.getenv("MEDLARTV_DEBUG", "false").lower() == "true":
        print("[DEBUG main] main() started")
        print(BOOT_BANNER)
        print("[DEBUG main] boot banner printed")
    configure_logging()

    if os.getenv("MEDLARTV_DEBUG", "false").lower() == "true":
        print("[DEBUG main] calling initialize_systems()")
    initialize_systems()
    if os.getenv("MEDLARTV_DEBUG", "false").lower() == "true":
        print("[DEBUG main] initialize_systems() completed")

    if os.getenv("MEDLARTV_DEBUG", "false").lower() == "true":
        print("[DEBUG main] calling start_listener()")
    start_listener()
    if os.getenv("MEDLARTV_DEBUG", "false").lower() == "true":
        print("[DEBUG main] start_listener() returned")

    log.info("[SYSTEM] MedlarTV is now operational.")
    log.info("Press Ctrl+C to shut down.")

    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            shutdown()

if __name__ == "__main__":
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    main()
