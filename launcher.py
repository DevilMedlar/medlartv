#!/usr/bin/env python3
"""
MedlarTV Unified Launcher (Mixed venv + system processes)
Runs Ollama and LibreTranslate from system, Medlar from .venv
"""

import os
import sys
import time
import platform
import subprocess
import signal
from pathlib import Path

# ──────────────────────────────────────────────────────────────
# Colors for pretty output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'

    @classmethod
    def init(cls):
        if platform.system() == 'Windows':
            try:
                import colorama
                colorama.just_fix_windows_console()
            except ImportError:
                cls.RED = cls.GREEN = cls.YELLOW = cls.CYAN = cls.NC = ''
Colors.init()
# ──────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent.resolve()
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
LOGS_DIR = ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

processes = []

def banner():
    print(f"""{Colors.CYAN}
╔══════════════════════════════════════════════════════════╗
║                    MEDLAR  TACTICAL  AI                 ║
╚══════════════════════════════════════════════════════════╝
{Colors.NC}""")

def start_process(name, command, wait=2, cwd=None, use_venv=False):
    print(f"{Colors.CYAN}[START] {name}...{Colors.NC}")
    try:
        env = os.environ.copy()
        if use_venv:
            env["PYTHONPATH"] = str(ROOT)
        proc = subprocess.Popen(
            command,
            cwd=cwd or ROOT,
            env=env,
            shell=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if platform.system() == "Windows" else 0
        )
        time.sleep(wait)
        if proc.poll() is None:
            print(f"{Colors.GREEN}[OK] {name} running (PID {proc.pid}){Colors.NC}")
            processes.append(proc)
        else:
            print(f"{Colors.RED}[FAIL] {name} failed to start{Colors.NC}")
    except Exception as e:
        print(f"{Colors.RED}[ERROR] {name}: {e}{Colors.NC}")

def stop_all():
    print(f"\n{Colors.YELLOW}Shutting down Medlar systems...{Colors.NC}")
    for p in processes:
        try:
            if platform.system() == "Windows":
                p.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                p.terminate()
        except Exception as e:
            print(f"{Colors.YELLOW}Warning stopping process: {e}{Colors.NC}")
    for p in processes:
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()
    print(f"{Colors.GREEN}All systems offline.{Colors.NC}")

def main():
    banner()
    print(f"{Colors.GREEN}Initializing Medlar Tactical AI systems...{Colors.NC}\n")

    # Check .venv exists
    if not VENV_PYTHON.exists():
        print(f"{Colors.RED}[ERROR] Python venv not found at {VENV_PYTHON}{Colors.NC}")
        sys.exit(1)

    # ───────────────────────────────────────────────
    # 1️⃣ Ollama (system)
    start_process("Ollama Server", "ollama serve", wait=3)

    # ───────────────────────────────────────────────
    # 2️⃣ LibreTranslate (system)
    lt_script = Path("C:/LibreTranslate")
    if lt_script.exists():
        start_process(
            "LibreTranslate Server",
            "python -m libretranslate.main",
            cwd=lt_script,
            wait=5
        )
    else:
        print(f"{Colors.YELLOW}[WARN] LibreTranslate path not found at {lt_script}{Colors.NC}")

    # ───────────────────────────────────────────────
    # 3️⃣ Medlar Core (inside venv)
    start_process("Medlar Core (FastAPI)", f'"{VENV_PYTHON}" MedlarTV/core/main.py', use_venv=True, wait=4)

    # ───────────────────────────────────────────────
    # 4️⃣ Twitch Listener (inside venv)
    start_process("Twitch Listener", f'"{VENV_PYTHON}" MedlarTV/tools/twitch_listener.py', use_venv=True, wait=2)

    print(f"\n{Colors.GREEN}✅ MedlarTV Systems Operational{Colors.NC}")
    print(f"{Colors.YELLOW}Press Ctrl+C to shutdown gracefully...{Colors.NC}\n")

    try:
        while True:
            time.sleep(1)
            for p in processes:
                if p.poll() is not None:
                    print(f"{Colors.RED}[ALERT] {p.args} exited unexpectedly!{Colors.NC}")
                    stop_all()
                    sys.exit(1)
    except KeyboardInterrupt:
        stop_all()


if __name__ == "__main__":
    main()

