#!/usr/bin/env python3
"""
MedlarTV Unified Launcher
Cross-platform launcher that works on Windows, Linux, and macOS
"""

import os
import sys
import time
import platform
import subprocess
import signal
import socket
from pathlib import Path
from typing import List, Optional

class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'
    
    @classmethod
    def disable_on_windows(cls):
        if platform.system() == 'Windows':
            try:
                import colorama
                colorama.init()
            except ImportError:
                cls.RED = cls.GREEN = cls.YELLOW = cls.CYAN = cls.NC = ''

Colors.disable_on_windows()


class MedlarTVLauncher:
    def __init__(self):
        self.processes: List[subprocess.Popen] = []
        self.root_dir = Path(__file__).parent
        self.python_cmd = self._get_python_command()

    def _get_python_command(self) -> str:
        return "python" if platform.system() == "Windows" else "python3"

    def _print_banner(self):
        banner = f"""{Colors.CYAN}
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ███╗   ███╗███████╗██████╗ ██╗      █████╗ ██████╗    ║
║   ████╗ ████║██╔════╝██╔══██╗██║     ██╔══██╗██╔══██╗   ║
║   ██╔████╔██║█████╗  ██║  ██║██║     ███████║██████╔╝   ║
║   ██║╚██╔╝██║██╔══╝  ██║  ██║██║     ██╔══██║██╔══██╗   ║
║   ██║ ╚═╝ ██║███████╗██████╔╝███████╗██║  ██║██║  ██║   ║
║   ╚═╝     ╚═╝╚══════╝╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝   ║
║                                                           ║
║              T A C T I C A L   A I   S Y S T E M         ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
{Colors.NC}"""
        print(banner)

    def _check_env_file(self) -> bool:
        env_path = self.root_dir / ".env"
        if not env_path.exists():
            print(f"{Colors.RED}[ERROR] .env file not found!{Colors.NC}")
            return False
        return True

    def _create_logs_dir(self):
        logs_dir = self.root_dir / "logs"
        logs_dir.mkdir(exist_ok=True)

    def _is_port_in_use(self, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) == 0

    def _start_component(self, name: str, command: str, wait_time: int = 2, port: Optional[int] = None) -> Optional[subprocess.Popen]:
        print(f"{Colors.CYAN}[START] {name}...{Colors.NC}")

        if port and self._is_port_in_use(port):
            print(f"{Colors.YELLOW}[INFO] {name} already running on port {port}{Colors.NC}")
            return None

        try:
            env = os.environ.copy()
            env["PYTHONPATH"] = str(self.root_dir)
            process = subprocess.Popen(command, shell=True, env=env, cwd=str(self.root_dir))
            time.sleep(wait_time)

            if process.poll() is None:
                print(f"{Colors.GREEN}[OK] {name} running (PID: {process.pid}){Colors.NC}")
                return process
            else:
                print(f"{Colors.RED}[FAIL] {name} failed to start{Colors.NC}")
                return None
        except Exception as e:
            print(f"{Colors.RED}[ERROR] Failed to start {name}: {e}{Colors.NC}")
            return None

    def _stop_all(self):
        print(f"\n{Colors.YELLOW}Shutting down MedlarTV...{Colors.NC}")
        for process in self.processes:
            try:
                if platform.system() == "Windows":
                    process.terminate()
                else:
                    process.send_signal(signal.SIGTERM)
            except Exception as e:
                print(f"{Colors.YELLOW}Warning: {e}{Colors.NC}")

        for process in self.processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        print(f"{Colors.GREEN}All systems offline. Standing by.{Colors.NC}\n")

    def start(self):
        self._print_banner()
        print(f"{Colors.GREEN}Initializing MedlarTV systems...{Colors.NC}\n")

        if not self._check_env_file():
            sys.exit(1)
        self._create_logs_dir()

        libretranslate_path = Path("C:/LibreTranslate/venv/Scripts/python.exe")
        if not libretranslate_path.exists():
            print(f"{Colors.RED}[ERROR] LibreTranslate venv not found at {libretranslate_path}{Colors.NC}")
            sys.exit(1)

        components = [
            {
                "name": "LibreTranslate (Local Translation API)",
                "command": f'"{libretranslate_path}" -m libretranslate.main',
                "wait": 5,
                "port": 5000
            },
            {
                "name": "Ollama Server",
                "command": "ollama serve",
                "wait": 3,
                "port": 11434
            },
            {
                "name": "Core API (FastAPI)",
                "command": f"{self.python_cmd} MedlarTV/core/main.py",
                "wait": 4
            },
            {
                "name": "Twitch Listener",
                "command": f"{self.python_cmd} MedlarTV/tools/twitch_listener.py",
                "wait": 2
            }
        ]

        for comp in components:
            proc = self._start_component(comp["name"], comp["command"], comp["wait"], comp.get("port"))
            if proc:
                self.processes.append(proc)
            elif comp.get("port") and self._is_port_in_use(comp["port"]):
                print(f"{Colors.YELLOW}[SKIP] {comp['name']} already active.{Colors.NC}")
            else:
                print(f"{Colors.RED}[ABORT] Failed to start {comp['name']}{Colors.NC}")
                self._stop_all()
                sys.exit(1)

        print(f"\n{Colors.CYAN}{'='*60}{Colors.NC}")
        print(f"{Colors.GREEN}MedlarTV Systems Operational{Colors.NC}")
        print(f"{Colors.CYAN}{'='*60}{Colors.NC}\n")

        print(f"{Colors.YELLOW}Active Components:{Colors.NC}")
        for proc in self.processes:
            status = "🟢 RUNNING" if proc.poll() is None else "🔴 STOPPED"
            print(f"  {status} PID: {proc.pid}")

        print(f"\n{Colors.CYAN}Commands:{Colors.NC}")
        print(f"  {Colors.GREEN}Ctrl+C{Colors.NC} - Shutdown all systems")
        print(f"\n{Colors.YELLOW}Press Ctrl+C to shutdown...{Colors.NC}\n")

        try:
            while True:
                time.sleep(1)
                for proc in self.processes:
                    if proc.poll() is not None:
                        print(f"{Colors.RED}[ALERT] A component stopped unexpectedly!{Colors.NC}")
                        self._stop_all()
                        sys.exit(1)
        except KeyboardInterrupt:
            self._stop_all()


def main():
    launcher = MedlarTVLauncher()
    launcher.start()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n{Colors.RED}[FATAL] Unexpected error: {e}{Colors.NC}\n")
        sys.exit(1)
