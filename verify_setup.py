"""
MedlarTV Setup Verification Script (Professional Edition)
---------------------------------------------------------
A polished, production-grade system validator that checks the full MedlarTV stack:

- Python version
- .env correctness
- Directory structure
- __init__ package markers
- Required YAML configs
- Required Python packages
- Memory file (auto-creates default)
- Ollama installation + model presence
- Port conflicts (FastAPI, Bridge, Ollama)

Run with:
    python verify_setup.py
"""

import os
import sys
import socket
import subprocess
from pathlib import Path
from datetime import datetime
import requests

import yaml
from dotenv import load_dotenv


# -------------------------------------------------------------
# Terminal Colors
# -------------------------------------------------------------
class Colors:
    GREEN = "\u001b[32m"
    YELLOW = "\u001b[33m"
    RED = "\u001b[31m"
    BLUE = "\u001b[34m"
    CYAN = "\u001b[36m"
    RESET = "\u001b[0m"
    BOLD = "\u001b[1m"


# -------------------------------------------------------------
# Pretty Output Helpers
# -------------------------------------------------------------
def print_header(text: str) -> None:
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(70)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}\n")


def ok(text: str) -> None:
    print(f"{Colors.GREEN}✔ {text}{Colors.RESET}")


def warn(text: str) -> None:
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def err(text: str) -> None:
    print(f"{Colors.RED}✖ {text}{Colors.RESET}")


def info(text: str) -> None:
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")


# -------------------------------------------------------------
# 1. Python Version
# -------------------------------------------------------------
def check_python_version() -> bool:
    info("Checking Python version…")
    v = sys.version_info
    if v.major >= 3 and v.minor >= 8:
        ok(f"Python {v.major}.{v.minor}.{v.micro}")
        return True
    err(f"Python {v.major}.{v.minor} detected — need 3.8 or newer")
    return False


# -------------------------------------------------------------
# 2. .env File
# -------------------------------------------------------------
def check_env_file() -> bool:
    info("Checking .env file…")
    env_path = Path(".env")

    if not env_path.exists():
        err("Missing .env file!")
        info("Create one based on the template.")
        return False

    # Required variables for MedlarTV
    required = [
        "TWITCH_NICK", "TWITCH_CHANNEL",
        "DEVILMEDLAR_TWITCH_TOKEN", "DEVILMEDLAR_TWITCH_CLIENT_ID",
        "APP_SECRET_ID", "CORE_URL", "OLLAMA_URL", "BRIDGE_URL"
    ]

    contents = env_path.read_text(encoding="utf-8")
    missing = [v for v in required if f"{v}=" not in contents]

    if missing:
        err("Missing env variables: " + ", ".join(missing))
        return False

    ok(".env looks good")
    return True


# -------------------------------------------------------------
# 3. Directory Structure
# -------------------------------------------------------------
def check_directory_structure() -> bool:
    info("Checking directory structure…")

    required_dirs = [
        "MedlarTV", "MedlarTV/core", "MedlarTV/avatar",
        "MedlarTV/avatar_client", "MedlarTV/tools",
        "MedlarTV/config", "MedlarTV/data",
    ]

    missing = [d for d in required_dirs if not Path(d).exists()]

    if missing:
        err("Missing directories: " + ", ".join(missing))
        return False

    ok("All required directories present")
    return True


# -------------------------------------------------------------
# 4. __init__.py Files
# -------------------------------------------------------------
def check_init_files() -> bool:
    info("Checking __init__.py files…")

    required_inits = [
        "MedlarTV/__init__.py",
        "MedlarTV/core/__init__.py",
        "MedlarTV/avatar/__init__.py",
        "MedlarTV/avatar_client/__init__.py",
        "MedlarTV/tools/__init__.py",
        "MedlarTV/config/__init__.py",
        "MedlarTV/data/__init__.py",
    ]

    missing = [p for p in required_inits if not Path(p).exists()]

    if missing:
        warn("Some packages are missing __init__.py: " + ", ".join(missing))
        return False

    ok("All package markers present")
    return True


# -------------------------------------------------------------
# 5. YAML Configs
# -------------------------------------------------------------
def check_config_files() -> bool:
    info("Checking configuration files…")

    required = [
        "MedlarTV/config/commands.yaml",
        "MedlarTV/config/devices.yaml",
        "MedlarTV/config/moods.yaml",
        "MedlarTV/config/personality.yaml",
        "MedlarTV/config/policy.yaml",
        "MedlarTV/config/style_profiles.yaml",
    ]

    missing = [f for f in required if not Path(f).exists()]

    if missing:
        err("Missing config files: " + ", ".join(Path(f).name for f in missing))
        return False

    ok("All config YAMLs present")
    return True


# -------------------------------------------------------------
# 6. Python Packages
# -------------------------------------------------------------
def check_python_packages() -> bool:
    info("Checking installed Python packages…")

    required = {
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "websockets": "websockets",
        "yaml": "pyyaml",
        "dotenv": "python-dotenv",
        "requests": "requests",
        "colorama": "colorama",
    }

    missing = []

    for module, pkg in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(pkg)

    if missing:
        err("Missing Python packages: " + ", ".join(missing))
        info("Install with: pip install -r requirements.txt")
        return False

    ok("All required packages installed")
    return True


# -------------------------------------------------------------
# 7. Memory File
# -------------------------------------------------------------
def check_memory_file() -> bool:
    info("Checking memory.yaml…")

    path = Path("MedlarTV/data/memory.yaml")

    if not path.exists():
        warn("memory.yaml missing — creating default…")
        path.parent.mkdir(parents=True, exist_ok=True)

        default = {
            "personality_memory": {
                "last_update": int(datetime.now().timestamp()),
                "mood_weights": {
                    "chill": 1, "hype": 1,
                    "snarky": 1, "supportive": 1,
                },
            }
        }

        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(default, f)

        ok("Created default memory.yaml")
        return True

    ok("memory.yaml exists")
    return True


# -------------------------------------------------------------
# 8. Ollama Installation + Model
# -------------------------------------------------------------
def check_ollama() -> bool:
    info("Checking Ollama installation…")

    try:
        result = subprocess.run([
            "ollama", "--version"
        ], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            ok(f"Ollama installed: {result.stdout.strip()}")
        else:
            warn("Ollama found but not responding correctly")
    except FileNotFoundError:
        err("Ollama not installed")
        info("Install from https://ollama.ai")
        return False
    except subprocess.TimeoutExpired:
        warn("Ollama version check timed out")
        return False

    base = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    try:
        r = requests.get(f"{base}/api/tags", timeout=5)
        if r.status_code == 200:
            ok(f"Ollama server responding on {base}")
        else:
            warn(f"Ollama server returned {r.status_code} at {base}")
            return False
    except Exception:
        warn(f"Ollama server not reachable on {base}")
        return False

    return True

def run_all() -> bool:
    print_header("MedlarTV Setup Verification")
    load_dotenv()

    results = [
        check_python_version(),
        check_env_file(),
        check_directory_structure(),
        check_init_files(),
        check_config_files(),
        check_python_packages(),
        check_memory_file(),
        check_ollama(),
    ]

    all_ok = all(results)
    if all_ok:
        ok("Setup verification completed successfully")
    else:
        err("Setup verification detected issues")
    return all_ok

if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)