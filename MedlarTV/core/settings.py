import os
import yaml
import threading
from pathlib import Path
from typing import Dict, Any

def _resolve_config_file() -> Path:
    try:
        root_env = os.getenv("MEDLARTV_ROOT", "").strip()
    except Exception:
        root_env = ""
    if root_env:
        try:
            base = Path(root_env)
            cfg = base / "MedlarTV" / "config" / "app_settings.yaml"
            cfg.parent.mkdir(parents=True, exist_ok=True)
            return cfg
        except Exception:
            pass
    candidates = []
    try:
        candidates.append(Path("C:/Users/znorr/medlartv"))
    except Exception:
        pass
    try:
        candidates.append(Path.home() / "medlartv")
    except Exception:
        pass
    try:
        candidates.append(Path.cwd())
    except Exception:
        pass

    for base in candidates:
        try:
            cfg_dir = base / "MedlarTV" / "config"
            if cfg_dir.exists():
                cfg_dir.mkdir(parents=True, exist_ok=True)
                return cfg_dir / "app_settings.yaml"
        except Exception:
            pass
    fallback = Path("C:/Users/znorr/medlartv/MedlarTV/config/app_settings.yaml")
    try:
        fallback.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return fallback

APP_SETTINGS_FILE = _resolve_config_file()

_DEFAULTS: Dict[str, Any] = {
    "llm_brain": True,
    "pcg_auto_catch": True,
    "ignore_viewer_pokecatch": True,
    "content_filter": True,
    "timers": True,
    "fuzzy_trigger": True,
}

_lock = threading.Lock()

def _ensure_file() -> None:
    if not APP_SETTINGS_FILE.exists():
        APP_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with APP_SETTINGS_FILE.open("w", encoding="utf-8") as f:
            yaml.safe_dump(_DEFAULTS, f)

def get_settings() -> Dict[str, Any]:
    with _lock:
        _ensure_file()
        try:
            with APP_SETTINGS_FILE.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            data = {}
        merged = {**_DEFAULTS, **data}
        return dict(merged)

def update_settings(updates: Dict[str, Any]) -> Dict[str, Any]:
    with _lock:
        cur = get_settings()
        cur.update({k: bool(v) for k, v in updates.items() if k in _DEFAULTS})
        with APP_SETTINGS_FILE.open("w", encoding="utf-8") as f:
            yaml.safe_dump(cur, f, default_flow_style=False)
        return dict(cur)

def is_enabled(key: str) -> bool:
    return bool(get_settings().get(key, False))

def settings_path() -> str:
    return str(APP_SETTINGS_FILE)
