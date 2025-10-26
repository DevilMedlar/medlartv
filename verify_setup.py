#!/usr/bin/env python3
"""
MedlarTV Setup Verification Script
Checks that all components are properly configured before running.
"""

import os
import sys
from pathlib import Path
import subprocess
import socket

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(60)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.RESET}")

def check_python_version():
    """Check if Python version is 3.8+"""
    print_info("Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print_success(f"Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print_error(f"Python {version.major}.{version.minor} detected. Need Python 3.8+")
        return False

def check_env_file():
    """Check if .env file exists and has required variables"""
    print_info("Checking .env file...")
    env_path = Path(".env")
    
    if not env_path.exists():
        print_error(".env file not found!")
        print_info("Create one based on .env.example")
        return False
    
    required_vars = [
        "TWITCH_NICK",
        "TWITCH_CHANNEL", 
        "TWITCH_TOKEN",
        "CORE_URL",
        "OLLAMA_URL",
        "BRIDGE_URL"
    ]
    
    missing = []
    with open(env_path, 'r') as f:
        content = f.read()
        for var in required_vars:
            if var not in content or f"{var}=" not in content:
                missing.append(var)
    
    if missing:
        print_error(f"Missing environment variables: {', '.join(missing)}")
        return False
    
    print_success(".env file configured correctly")
    return True

def check_directory_structure():
    """Check if all required directories exist"""
    print_info("Checking directory structure...")
    
    required_dirs = [
        "MedlarTV",
        "MedlarTV/core",
        "MedlarTV/avatar",
        "MedlarTV/avatar_client",
        "MedlarTV/tools",
        "MedlarTV/config",
        "MedlarTV/data"
    ]
    
    missing = []
    for directory in required_dirs:
        if not Path(directory).exists():
            missing.append(directory)
    
    if missing:
        print_error(f"Missing directories: {', '.join(missing)}")
        return False
    
    print_success("Directory structure valid")
    return True

def check_init_files():
    """Check if __init__.py files exist"""
    print_info("Checking __init__.py files...")
    
    required_inits = [
        "MedlarTV/__init__.py",
        "MedlarTV/core/__init__.py",
        "MedlarTV/avatar/__init__.py",
        "MedlarTV/avatar_client/__init__.py",
        "MedlarTV/tools/__init__.py",
        "MedlarTV/config/__init__.py",
        "MedlarTV/data/__init__.py"
    ]
    
    missing = []
    for init_file in required_inits:
        if not Path(init_file).exists():
            missing.append(init_file)
    
    if missing:
        print_warning(f"Missing __init__.py files: {len(missing)}")
        print_info("Run: python3 generate_init_files.py")
        return False
    
    print_success("All __init__.py files present")
    return True

def check_config_files():
    """Check if all config YAML files exist"""
    print_info("Checking configuration files...")
    
    required_configs = [
        "MedlarTV/config/commands.yaml",
        "MedlarTV/config/devices.yaml",
        "MedlarTV/config/moods.yaml",
        "MedlarTV/config/personality.yaml",
        "MedlarTV/config/policy.yaml",
        "MedlarTV/config/style_profiles.yaml"
    ]
    
    missing = []
    for config in required_configs:
        if not Path(config).exists():
            missing.append(config)
    
    if missing:
        print_error(f"Missing config files: {', '.join([Path(f).name for f in missing])}")
        return False
    
    print_success("All configuration files present")
    return True

def check_python_packages():
    """Check if required Python packages are installed"""
    print_info("Checking Python packages...")
    
    required_packages = {
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "websockets": "websockets",
        "yaml": "pyyaml",
        "dotenv": "python-dotenv",
        "colorama": "colorama",
        "requests": "requests"
    }
    
    missing = []
    for module, package in required_packages.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    
    if missing:
        print_error(f"Missing packages: {', '.join(missing)}")
        print_info("Install with: pip install -r requirements.txt")
        return False
    
    print_success("All required packages installed")
    return True

def check_ollama():
    """Check if Ollama is installed and running"""
    print_info("Checking Ollama installation...")
    
    # Check if ollama command exists
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print_success(f"Ollama installed: {result.stdout.strip()}")
        else:
            print_warning("Ollama command found but may not be working")
    except FileNotFoundError:
        print_error("Ollama not installed")
        print_info("Install from: https://ollama.ai")
        return False
    except subprocess.TimeoutExpired:
        print_warning("Ollama check timed out")
        return False
    
    # Check if Ollama is running
    try:
        import requests
        response = requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
        if response.status_code == 200:
            print_success("Ollama server is running")
            
            # Check if llama3 model is available
            data = response.json()
            models = [m.get('name', '') for m in data.get('models', [])]
            if any('llama3' in m for m in models):
                print_success("llama3 model available")
            else:
                print_warning("llama3 model not found")
                print_info("Download with: ollama pull llama3")
        else:
            print_warning("Ollama server returned unexpected status")
    except:
        print_warning("Ollama server not running")
        print_info("Start with: ollama serve")
        return False
    
    return True

def check_ports():
    """Check if required ports are available"""
    print_info("Checking port availability...")
    
    ports_to_check = {
        8000: "FastAPI Core",
        8765: "WebSocket Bridge",
        11434: "Ollama"
    }
    
    all_available = True
    for port, service in ports_to_check.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        
        if result == 0:
            print_warning(f"Port {port} ({service}) is in use")
            all_available = False
        else:
            print_success(f"Port {port} ({service}) available")
    
    return all_available

def check_memory_file():
    """Check if memory.yaml exists, create if not"""
    print_info("Checking memory data file...")
    
    memory_path = Path("MedlarTV/data/memory.yaml")
    
    if not memory_path.exists():
        print_warning("memory.yaml not found, creating default...")
        memory_path.parent.mkdir(parents=True, exist_ok=True)
        
        import yaml
        from datetime import datetime
        
        default_memory = {
            "personality_memory": {
                "last_update": int(datetime.now().timestamp()),
                "mood_weights": {
                    "chill": 1,
                    "hype": 1,
                    "snarky": 1,
                    "supportive": 1
                }
            }
        }
        
        with open(memory_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(default_memory, f)
        
        print_success("Created default memory.yaml")
    else:
        print_success("memory.yaml exists")
    
    return True

def run_all_checks():
    """Run all verification checks"""
    print_header("MedlarTV Setup Verification")
    
    checks = [
        ("Python Version", check_python_version),
        ("Environment File", check_env_file),
        ("Directory Structure", check_directory_structure),
        ("Init Files", check_init_files),
        ("Config Files", check_config_files),
        ("Python Packages", check_python_packages),
        ("Memory File", check_memory_file),
        ("Ollama", check_ollama),
        ("Ports", check_ports),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print_error(f"Error checking {name}: {e}")
            results[name] = False
        print()  # Blank line between checks
    
    # Summary
    print_header("Verification Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        if result:
            print_success(f"{name}")
        else:
            print_error(f"{name}")
    
    print(f"\n{Colors.BOLD}Results: {passed}/{total} checks passed{Colors.RESET}\n")
    
    if passed == total:
        print_success("🎉 All checks passed! MedlarTV is ready to run!")
        print_info("\nTo start MedlarTV:")
        print_info("  1. Terminal 1: python MedlarTV/core/main.py")
        print_info("  2. Terminal 2: python MedlarTV/avatar/bridge.py")
        print_info("  3. Terminal 3: python MedlarTV/tools/twitch_listener.py")
        return True
    else:
        print_warning(f"⚠️  {total - passed} check(s) failed. Fix issues above before running.")
        return False

if __name__ == "__main__":
    try:
        success = run_all_checks()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Interrupted by user{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Fatal error: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
