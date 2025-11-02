# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Banner
echo -e "${CYAN}"
cat << "EOF"
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
EOF
echo -e "${NC}"

echo -e "${GREEN}Initializing MedlarTV systems...${NC}\n"

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down MedlarTV...${NC}"
    kill $(jobs -p) 2>/dev/null
    echo -e "${GREEN}All systems offline. Standing by.${NC}\n"
    exit 0
}

# Trap Ctrl+C
trap cleanup INT TERM

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}[ERROR] .env file not found!${NC}"
    exit 1
fi

# Start Core API
echo -e "${CYAN}[START] Core API (FastAPI)...${NC}"
python3 MedlarTV/core/main.py > logs/core.log 2>&1 &
CORE_PID=$!
sleep 3

# Check if Core started
if ! kill -0 $CORE_PID 2>/dev/null; then
    echo -e "${RED}[FAIL] Core API failed to start${NC}"
    exit 1
fi
echo -e "${GREEN}[OK] Core API running (PID: $CORE_PID)${NC}"

# Start WebSocket Bridge
echo -e "${CYAN}[START] WebSocket Bridge...${NC}"
python3 MedlarTV/avatar/bridge.py > logs/bridge.log 2>&1 &
BRIDGE_PID=$!
sleep 2

# Check if Bridge started
if ! kill -0 $BRIDGE_PID 2>/dev/null; then
    echo -e "${RED}[FAIL] Bridge failed to start${NC}"
    kill $CORE_PID
    exit 1
fi
echo -e "${GREEN}[OK] Bridge running (PID: $BRIDGE_PID)${NC}"

# Start Twitch Listener
echo -e "${CYAN}[START] Twitch Listener...${NC}"
python3 MedlarTV/tools/twitch_listener.py > logs/twitch.log 2>&1 &
TWITCH_PID=$!
sleep 2

# Check if Twitch started
if ! kill -0 $TWITCH_PID 2>/dev/null; then
    echo -e "${RED}[FAIL] Twitch Listener failed to start${NC}"
    kill $CORE_PID $BRIDGE_PID
    exit 1
fi
echo -e "${GREEN}[OK] Twitch Listener running (PID: $TWITCH_PID)${NC}"

# Show status
echo -e "\n${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}MedlarTV Systems Operational${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}\n"

echo -e "${YELLOW}Active Components:${NC}"
echo -e "  🟢 Core API (PID: $CORE_PID)"
echo -e "  🟢 WebSocket Bridge (PID: $BRIDGE_PID)"
echo -e "  🟢 Twitch Listener (PID: $TWITCH_PID)"

echo -e "\n${YELLOW}Logs:${NC}"
echo -e "  📄 logs/core.log"
echo -e "  📄 logs/bridge.log"
echo -e "  📄 logs/twitch.log"

echo -e "\n${CYAN}Press Ctrl+C to shutdown all systems${NC}\n"

# Keep script running
wait