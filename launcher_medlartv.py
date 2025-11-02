#!/usr/bin/env python3
"""
MedlarTV Launcher
Starts all MedlarTV components in one command.
"""

import os
import sys
import time
import signal
import subprocess
from pathlib import Path
from colorama import init, Fore, Style

init(autoreset=True)

# Process tracking
processes = []
shutdown_requested = False


def print_banner():
    """Display MedlarTV startup banner."""
    banner = f"""
{Fore.CYAN}{Style.BRIGHT}
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
{Style.RESET_ALL}
    """
    print(banner)
    print(f"{Fore.GREEN}Initializing systems...{Style.RESET_ALL}\n")


def check_requirements():
    """Check if all required files exist."""
    print(f"{Fore.YELLOW}[CHECK] Verifying system files...{Style.RESET_ALL}")
    
    required_files = [
        "MedlarTV/core/main.py",
        "MedlarTV/avatar/bridge.py",
        "MedlarTV/tools/twitch_listener.py",
        ".env"
    ]
    
    missing = []
    for file in required_files:
        if not Path(file).exists():
            missing.append(file)
    
    if missing:
        print(f"{Fore.RED}[ERROR] Missing required files:{Style.RESET_ALL}")
        for file in missing:
            print(f"  ❌ {file}")
        return False
    
    print(f"{Fore.GREEN}[OK] All system files present{Style.RESET_ALL}\n")
    return True


def start_component(name, command, wait_time=2):
    """Start a MedlarTV component."""
    print(f"{Fore.CYAN}[START] {name}...{Style.RESET_ALL}")
    
    try:
        # Set PYTHONPATH environment variable to current directory
        env = os.environ.copy()
        env['PYTHONPATH'] = os.getcwd()
        
        # Determine python command based on OS
        python_cmd = "python" if sys.platform == "win32" else "python3"
        
        # Replace python3 with appropriate command
        if command.startswith("python3"):
            command = command.replace("python3", python_cmd, 1)
        
        # Start process with updated environment
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
            cwd=os.getcwd()  # Ensure we're in the right directory
        )
        
        processes.append({
            "name": name,
            "process": process,
            "command": command
        })
        
        time.sleep(wait_time)
        
        # Check if process started successfully
        if process.poll() is None:
            print(f"{Fore.GREEN}[OK] {name} running (PID: {process.pid}){Style.RESET_ALL}")
            return True
        else:
            # Process failed, try to get error output
            stdout, stderr = process.communicate(timeout=1)
            print(f"{Fore.RED}[FAIL] {name} failed to start{Style.RESET_ALL}")
            if stderr:
                print(f"{Fore.RED}Error: {stderr[:200]}{Style.RESET_ALL}")
            return False
            
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Failed to start {name}: {e}{Style.RESET_ALL}")
        return False


def monitor_processes():
    """Monitor running processes and display status."""
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{Style.BRIGHT}MedlarTV Systems Operational{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
    print(f"{Fore.YELLOW}Active Components:{Style.RESET_ALL}")
    for proc_info in processes:
        status = "🟢 RUNNING" if proc_info["process"].poll() is None else "🔴 STOPPED"
        print(f"  {status} {proc_info['name']} (PID: {proc_info['process'].pid})")
    
    print(f"\n{Fore.CYAN}Commands:{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}Ctrl+C{Style.RESET_ALL} - Shutdown all systems")
    print(f"\n{Fore.YELLOW}Press Ctrl+C to shutdown...{Style.RESET_ALL}\n")


def shutdown_all():
    """Gracefully shutdown all components."""
    global shutdown_requested
    if shutdown_requested:
        return
    
    shutdown_requested = True
    
    print(f"\n{Fore.YELLOW}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Initiating shutdown sequence...{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'='*60}{Style.RESET_ALL}\n")
    
    for proc_info in reversed(processes):
        name = proc_info["name"]
        process = proc_info["process"]
        
        if process.poll() is None:
            print(f"{Fore.CYAN}[STOP] Shutting down {name}...{Style.RESET_ALL}")
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"{Fore.GREEN}[OK] {name} stopped{Style.RESET_ALL}")
            except subprocess.TimeoutExpired:
                print(f"{Fore.RED}[FORCE] Force killing {name}...{Style.RESET_ALL}")
                process.kill()
                process.wait()
    
    print(f"\n{Fore.GREEN}{Style.BRIGHT}All systems offline. Standing by.{Style.RESET_ALL}\n")


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    shutdown_all()
    sys.exit(0)


def start_all_components():
    """Start all MedlarTV components in order."""
    # Determine the correct python command
    python_cmd = "python" if sys.platform == "win32" else "python3"
    
    components = [
        {
            "name": "Ollama Server",
            "command": "ollama serve",
            "wait": 3
        },
        {
            "name": "Core API (FastAPI)",
            "command": f"{python_cmd} MedlarTV/core/main.py",
            "wait": 4
        },
        {
            "name": "WebSocket Bridge",
            "command": f"{python_cmd} MedlarTV/avatar/bridge.py",
            "wait": 2
        },
        {
            "name": "Twitch Listener",
            "command": f"{python_cmd} MedlarTV/tools/twitch_listener.py",
            "wait": 2
        }
    ]
    
    success_count = 0
    for component in components:
        if start_component(component["name"], component["command"], component["wait"]):
            success_count += 1
        else:
            print(f"\n{Fore.RED}[ABORT] Failed to start {component['name']}{Style.RESET_ALL}")
            print(f"{Fore.RED}[ABORT] Shutting down already running components...{Style.RESET_ALL}\n")
            shutdown_all()
            return False
    
    return success_count == len(components)


def main():
    """Main launcher function."""
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Show banner
    print_banner()
    
    # Check requirements
    if not check_requirements():
        print(f"\n{Fore.RED}[ABORT] System check failed. Cannot start MedlarTV.{Style.RESET_ALL}\n")
        print(f"{Fore.YELLOW}Run: python verify_setup.py{Style.RESET_ALL}")
        sys.exit(1)
    
    # Start all components
    if not start_all_components():
        sys.exit(1)
    
    # Show status
    monitor_processes()
    
    # Keep running and monitor
    try:
        while True:
            # Check if any process died
            for proc_info in processes:
                if proc_info["process"].poll() is not None and not shutdown_requested:
                    print(f"\n{Fore.RED}[ALERT] {proc_info['name']} stopped unexpectedly!{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}[ALERT] Initiating emergency shutdown...{Style.RESET_ALL}\n")
                    shutdown_all()
                    sys.exit(1)
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n{Fore.RED}[FATAL] Unexpected error: {e}{Style.RESET_ALL}\n")
        shutdown_all()
        sys.exit(1)