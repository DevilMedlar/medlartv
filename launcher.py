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
import socket
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
        env["PYTHONIOENCODING"] = "utf-8"

        # DEBUG LINES (correctly indented)
        print(f"[DEBUG] Launching process '{name}' with command: {command}")
        print(f"[DEBUG] Working directory: {cwd or ROOT}")
        print(f"[DEBUG] Using venv: {use_venv}")

        log_file_name = name.lower().replace(" ", "_").replace("(", "").replace(")", "") + ".log"
        log_path = LOGS_DIR / log_file_name
        log_handle = open(log_path, "a", encoding="utf-8")

        proc = subprocess.Popen(
            command,
            cwd=cwd or ROOT,
            env=env,
            shell=True,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if platform.system() == "Windows" else 0
        )

        print(f"[DEBUG] Process object created. PID pending...")

        time.sleep(wait)
        if proc.poll() is None:
            print(f"{Colors.GREEN}[OK] {name} running (PID {proc.pid}){Colors.NC}")
            processes.append({"proc": proc, "name": name, "log": log_handle})
        else:
            print(f"{Colors.RED}[FAIL] {name} failed to start{Colors.NC}")
            try:
                log_handle.close()
            except Exception:
                pass

    except Exception as e:
        print(f"{Colors.RED}[ERROR] {name}: {e}{Colors.NC}")

def stop_all():
    print(f"\n{Colors.YELLOW}Shutting down Medlar systems...{Colors.NC}")
    for p in processes:
        try:
            if platform.system() == "Windows":
                p["proc"].send_signal(signal.CTRL_BREAK_EVENT)
            else:
                p["proc"].terminate()
        except Exception as e:
            print(f"{Colors.YELLOW}Warning stopping process: {e}{Colors.NC}")
    for p in processes:
        try:
            p["proc"].wait(timeout=5)
        except subprocess.TimeoutExpired:
            p["proc"].kill()
        try:
            p["log"].close()
        except Exception:
            pass
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

    bridge_host = "0.0.0.0"
    preferred_port = 8765
    def is_port_free(port, host="0.0.0.0"):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
            s.close()
            return True
        except OSError:
            s.close()
            return False
    def find_free_port(start_port: int, end_port: int) -> int:
        for p in range(start_port, end_port + 1):
            if is_port_free(p):
                return p
        return start_port
    bridge_port = find_free_port(preferred_port, preferred_port + 10)
    os.environ["BRIDGE_HOST"] = bridge_host
    os.environ["BRIDGE_PORT"] = str(bridge_port)
    os.environ["BRIDGE_URL"] = f"ws://127.0.0.1:{bridge_port}"
    print(f"[DEBUG] Avatar Bridge selected port: {bridge_port}")
    start_process("Avatar Bridge Server", f'"{VENV_PYTHON}" MedlarTV/avatar/bridge/server.py', use_venv=True, wait=2)

    # ───────────────────────────────────────────────
    # 3️⃣ Medlar Core (inside venv)
    start_process("Medlar Core (FastAPI)", f'"{VENV_PYTHON}" MedlarTV/core/main.py', use_venv=True, wait=4)

    # ───────────────────────────────────────────────
    # Avatar Console Client (inside venv, optional)
    if os.getenv("ENABLE_AVATAR_CONSOLE", "0") == "1":
        start_process("Avatar Console Client", f'"{VENV_PYTHON}" MedlarTV/avatar_client/console_client.py', use_venv=True, wait=2)

    # ───────────────────────────────────────────────
    print(f"\n{Colors.GREEN}✅ MedlarTV Systems Operational{Colors.NC}")
    print(f"{Colors.YELLOW}Press Ctrl+C to shutdown gracefully...{Colors.NC}\n")

    try:
        heartbeat = 0
        while True:
            time.sleep(1)
            heartbeat += 1
            if heartbeat % 10 == 0:
                print("[DEBUG] Launcher heartbeat: processes running okay...")
            for p in processes:
                if p["proc"].poll() is not None:
                    print(f"{Colors.RED}[ALERT] Process crashed: {p['proc'].args}{Colors.NC}")
                    print(f"[DEBUG] Return code: {p['proc'].returncode}")
                    print(f"{Colors.RED}[ALERT] {p['proc'].args} exited unexpectedly!{Colors.NC}")
                    stop_all()
                    sys.exit(1)
    except KeyboardInterrupt:
        stop_all()


if __name__ == "__main__":
    main()

