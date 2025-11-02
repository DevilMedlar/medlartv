# Stop all MedlarTV processes

echo "Stopping MedlarTV..."

# Kill by process name
pkill -f "MedlarTV/core/main.py"
pkill -f "MedlarTV/avatar/bridge.py"
pkill -f "MedlarTV/tools/twitch_listener.py"

echo "All MedlarTV processes stopped."
