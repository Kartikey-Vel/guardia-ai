#!/bin/bash

# Guardia AI Desktop Application Launcher
# Modern GUI launcher with dependency checks

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔥 Guardia AI Desktop Application${NC}"
echo -e "${BLUE}======================================${NC}"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python package
check_python_package() {
    python3 -c "import $1" >/dev/null 2>&1
}

# Check Python version
echo -e "${YELLOW}📋 Checking system requirements...${NC}"
python_version=$(python3 --version 2>&1 | grep -oP '(?<=Python )\d+\.\d+' || echo "0.0")
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo -e "${GREEN}✅ Python $python_version found${NC}"
else
    echo -e "${RED}❌ Python $required_version+ required, found: $python_version${NC}"
    exit 1
fi

# Check required packages
echo -e "${YELLOW}📦 Checking dependencies...${NC}"

# Core GUI packages
if check_python_package "customtkinter"; then
    echo -e "${GREEN}✅ CustomTkinter available${NC}"
else
    echo -e "${YELLOW}⚠️ Installing CustomTkinter...${NC}"
    pip install customtkinter pillow
fi

# OpenCV for camera
if check_python_package "cv2"; then
    echo -e "${GREEN}✅ OpenCV available${NC}"
else
    echo -e "${YELLOW}⚠️ Installing OpenCV...${NC}"
    pip install opencv-python
fi

# Optional: Advanced AI features
ai_available=true
if check_python_package "torch"; then
    echo -e "${GREEN}✅ PyTorch available${NC}"
else
    echo -e "${YELLOW}⚠️ PyTorch not found (advanced AI features disabled)${NC}"
    ai_available=false
fi

if check_python_package "ultralytics"; then
    echo -e "${GREEN}✅ YOLO available${NC}"
else
    echo -e "${YELLOW}⚠️ YOLO not found (object detection limited)${NC}"
    ai_available=false
fi

# Check camera access
echo -e "${YELLOW}📹 Checking camera access...${NC}"
if ls /dev/video* >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Camera devices found: $(ls /dev/video* | tr '\n' ' ')${NC}"
else
    echo -e "${YELLOW}⚠️ No camera devices found${NC}"
    echo -e "${YELLOW}   Make sure your camera is connected${NC}"
fi

# Display feature status
echo -e "\n${PURPLE}🎯 Feature Status:${NC}"
echo -e "${GREEN}✅ Modern GUI Interface${NC}"
echo -e "${GREEN}✅ Real-time Camera Feed${NC}"
echo -e "${GREEN}✅ Video Recording${NC}"
echo -e "${GREEN}✅ Snapshot Capture${NC}"

if [ "$ai_available" = true ]; then
    echo -e "${GREEN}✅ AI Face Detection${NC}"
    echo -e "${GREEN}✅ AI Object Detection${NC}"
    echo -e "${GREEN}✅ Smart Alerts${NC}"
else
    echo -e "${YELLOW}⚠️ AI Features (Limited)${NC}"
    echo -e "${YELLOW}   Install: pip install -r requirements_enhanced.txt${NC}"
fi

# Launch application
echo -e "\n${BLUE}🚀 Launching Guardia AI Desktop App...${NC}"
echo -e "${BLUE}======================================${NC}"

# Create directories
mkdir -p recordings snapshots

# Set display for Linux
if [ -z "$DISPLAY" ] && [ -n "$XDG_SESSION_TYPE" ]; then
    export DISPLAY=:0
fi

# Launch with error handling
python3 desktop_app.py 2>&1 | while IFS= read -r line; do
    case "$line" in
        *"✅"*|*"🟢"*) echo -e "${GREEN}$line${NC}" ;;
        *"❌"*|*"🔴"*) echo -e "${RED}$line${NC}" ;;
        *"⚠️"*|*"🟡"*) echo -e "${YELLOW}$line${NC}" ;;
        *"🔥"*|*"🚀"*) echo -e "${PURPLE}$line${NC}" ;;
        *"📹"*|*"🧠"*|*"📊"*) echo -e "${BLUE}$line${NC}" ;;
        *) echo "$line" ;;
    esac
done

echo -e "\n${BLUE}👋 Thank you for using Guardia AI!${NC}"
