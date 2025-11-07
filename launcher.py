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
from pathlib import Path
from typing import List, Optional

# ANSI color codes
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color
    
    @classmethod
    def disable_on_windows(cls):
        """Disable colors on Windows if not supported"""
        if platform.system() == 'Windows':
            try:
                import colorama
                colorama.init()
            except ImportError:
                # Disable colors if colorama not available
                cls.RED = cls.GREEN = cls.YELLOW = cls.CYAN = cls.NC = ''


Colors.disable_on_windows()


class MedlarTVLauncher:
    def __init__(self):
        self.processes: List[subprocess.Popen] = []
        self.root_dir = Path(__file__).parent
        self.python_cmd = self._get_python_command()
        
    def _get_python_command(self) -> str:
        """Get the appropriate Python command for the platform"""
        if platform.system() == 'Windows':
            return 'python'
        return 'python3'
    
    def _print_banner(self):
        """Print MedlarTV banner"""
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
        """Check if .env file exists"""
        env_path = self.root_dir / '.env'
        if not env_path.exists():
            print(f"{Colors.RED}[ERROR] .env file not found!{Colors.NC}")
            return False
        return True
    
    def _create_logs_dir(self):
        """Create logs directory if it doesn't exist"""
        logs_dir = self.root_dir / 'logs'
        logs_dir.mkdir(exist_ok=True)
    
    def _start_component(self, name: str, command: str, wait_time: int = 2) -> Optional[subprocess.Popen]:
        """Start a component and return the process"""
        print(f"{Colors.CYAN}[START] {name}...{Colors.NC}")
        
        try:
            # CRITICAL FIX: Set PYTHONPATH environment variable (this was missing!)
            env = os.environ.copy()
            env['PYTHONPATH'] = str(self.root_dir)
            
            # CRITICAL FIX: Use shell=True like the working launcher
            process = subprocess.Popen(
                command,
                shell=True,
                env=env,
                cwd=str(self.root_dir)
            )
            
            time.sleep(wait_time)
            
            # Check if process is still running
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
        """Stop all running processes"""
        print(f"\n{Colors.YELLOW}Shutting down MedlarTV...{Colors.NC}")
        
        for process in self.processes:
            try:
                if platform.system() == 'Windows':
                    process.terminate()
                else:
                    process.send_signal(signal.SIGTERM)
            except Exception as e:
                print(f"{Colors.YELLOW}Warning: {e}{Colors.NC}")
        
        # Wait for processes to terminate
        for process in self.processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        
        print(f"{Colors.GREEN}All systems offline. Standing by.{Colors.NC}\n")
    
    def start(self):
        """Start all MedlarTV components"""
        self._print_banner()
        print(f"{Colors.GREEN}Initializing MedlarTV systems...{Colors.NC}\n")
        
        # Pre-flight checks
        if not self._check_env_file():
            sys.exit(1)
        
        self._create_logs_dir()
        
        # Start components (using shell commands like the working launcher)
        components = [
            {
                "name": "Ollama Server",
                "command": "ollama serve",
                "wait": 3
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
        
        for component in components:
            process = self._start_component(
                component["name"], 
                component["command"], 
                component["wait"]
            )
            if process:
                self.processes.append(process)
            else:
                print(f"\n{Colors.RED}[ABORT] Failed to start {component['name']}{Colors.NC}")
                print(f"{Colors.RED}[ABORT] Shutting down already running components...{Colors.NC}\n")
                self._stop_all()
                sys.exit(1)
        
        # Show status
        print(f"\n{Colors.CYAN}{'='*60}{Colors.NC}")
        print(f"{Colors.GREEN}MedlarTV Systems Operational{Colors.NC}")
        print(f"{Colors.CYAN}{'='*60}{Colors.NC}\n")
        
        print(f"{Colors.YELLOW}Active Components:{Colors.NC}")
        for i, process in enumerate(self.processes):
            status = "🟢 RUNNING" if process.poll() is None else "🔴 STOPPED"
            print(f"  {status} PID: {process.pid}")
        
        print(f"\n{Colors.CYAN}Commands:{Colors.NC}")
        print(f"  {Colors.GREEN}Ctrl+C{Colors.NC} - Shutdown all systems")
        print(f"\n{Colors.YELLOW}Press Ctrl+C to shutdown...{Colors.NC}\n")
        
        # Wait for interrupt
        try:
            while True:
                time.sleep(1)
                # Check if any process died
                for process in self.processes:
                    if process.poll() is not None:
                        print(f"{Colors.RED}[ALERT] A component stopped unexpectedly!{Colors.NC}")
                        print(f"{Colors.YELLOW}[ALERT] Initiating emergency shutdown...{Colors.NC}\n")
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