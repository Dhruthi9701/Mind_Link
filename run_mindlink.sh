#!/bin/bash

# Mind Link Project Launcher
# This script handles environment checks and starts the Mind Link components.

PROJECT_ROOT=$(pwd)
PYTHON_VENV="./bin/python"
MAIN_SCRIPT="mindlink/main.py"
MODELS_DIR="mindlink/models"

# Colors for output
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}==================================================${NC}"
echo -e "${CYAN}         MIND LINK — PROJECT LAUNCHER             ${NC}"
echo -e "${CYAN}==================================================${NC}"

# 1. Check Virtual Environment
if [ ! -f "$PYTHON_VENV" ]; then
    echo -e "${RED}[error] Virtual environment not found at $PYTHON_VENV${NC}"
    echo "Please ensure you are in the project root and the environment is set up."
    exit 1
fi

# 2. Check for Models
if [ ! -d "$MODELS_DIR" ] || [ ! -f "$MODELS_DIR/classical_model.pkl" ]; then
    echo -e "${YELLOW}[warning] Pre-trained models not found in $MODELS_DIR${NC}"
    echo "The system will auto-train on synthetic data if you start inference,"
    echo "or you can run a full training pass [Option 5]."
    echo ""
fi

# 3. Interactive Menu
echo "What would you like to start?"
echo -e "  ${GREEN}[1]${NC} Main Orchestrator (Full 5-Unit Pipeline)"
echo -e "  ${GREEN}[2]${NC} 3D Pygame Simulator (Tron Style, Free Camera)"
echo -e "  ${GREEN}[3]${NC} Pre-flight Hardware Checklist"
echo -e "  ${GREEN}[4]${NC} Train Models (PhysioNet Dataset)"
echo -e "  ${GREEN}[5]${NC} Run Latency Benchmark"
echo -e "  ${YELLOW}[Q]${NC} Quit"
echo ""
read -p "Select an option [1-5]: " choice

case $choice in
    1)
        echo -e "${CYAN}[launching] Starting Main Orchestrator...${NC}"
        $PYTHON_VENV $MAIN_SCRIPT
        ;;
    2)
        echo -e "${CYAN}[launching] Starting 3D Simulator...${NC}"
        cd mindlink && ../$PYTHON_VENV drone_control/sim3d.py
        ;;
    3)
        echo -e "${CYAN}[launching] Running Pre-flight Checklist...${NC}"
        $PYTHON_VENV $MAIN_SCRIPT --checklist
        ;;
    4)
        echo -e "${CYAN}[launching] Starting Training Pass...${NC}"
        $PYTHON_VENV $MAIN_SCRIPT --train
        ;;
    5)
        echo -e "${CYAN}[launching] Running Latency Benchmark...${NC}"
        # Run from mindlink dir for config access
        cd mindlink && ../$PYTHON_VENV main.py --benchmark
        ;;
    q|Q)
        echo "Exiting."
        exit 0
        ;;
    *)
        echo -e "${RED}[error] Invalid selection.${NC}"
        exit 1
        ;;
esac
