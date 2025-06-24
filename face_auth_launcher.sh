#!/bin/bash

# Guardia AI - Face Authentication Quick Start
# Simple launcher script for all face authentication features

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔥 Guardia AI - Face Authentication System${NC}"
echo -e "${BLUE}==========================================${NC}"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python
if command_exists python3; then
    echo -e "${GREEN}✅ Python 3 found${NC}"
else
    echo -e "${RED}❌ Python 3 not found${NC}"
    exit 1
fi

# Check if virtual environment exists
if [ -d ".venv" ]; then
    echo -e "${GREEN}✅ Virtual environment found${NC}"
    source .venv/bin/activate
else
    echo -e "${YELLOW}⚠️ No virtual environment found${NC}"
fi

# Check dependencies
echo -e "${YELLOW}📦 Checking dependencies...${NC}"
python3 -c "import cv2, face_recognition, numpy; print('✅ All dependencies available')" 2>/dev/null || {
    echo -e "${RED}❌ Missing dependencies. Installing...${NC}"
    pip install opencv-python face-recognition numpy
}

# Create storage directory
mkdir -p storage/faces
echo -e "${GREEN}✅ Storage directory ready${NC}"

echo
echo -e "${PURPLE}🎯 Choose what to run:${NC}"
echo -e "${PURPLE}=====================${NC}"
echo "1. 🎥 Real-Time Face Authentication (Full System)"
echo "2. 🎪 Interactive Demo"
echo "3. 🧪 Test System"
echo "4. 🔗 Integration Example"
echo "5. 📖 View Documentation"
echo "6. 🚪 Exit"

read -p "Select option (1-6): " choice

case $choice in
    1)
        echo -e "${GREEN}🎥 Starting Real-Time Face Authentication...${NC}"
        echo -e "${YELLOW}Controls: 'r'=register, 't'=training, 's'=stats, 'q'=quit${NC}"
        python3 real_time_face_auth.py
        ;;
    2)
        echo -e "${GREEN}🎪 Starting Interactive Demo...${NC}"
        python3 demo_face_auth.py
        ;;
    3)
        echo -e "${GREEN}🧪 Running System Tests...${NC}"
        python3 test_face_auth.py
        ;;
    4)
        echo -e "${GREEN}🔗 Starting Integration Example...${NC}"
        echo -e "${YELLOW}This shows how to integrate with the main surveillance system${NC}"
        python3 integration_example.py
        ;;
    5)
        echo -e "${GREEN}📖 Documentation Available:${NC}"
        echo "• README_FACE_AUTH.md - Complete guide"
        echo "• README.md - Main documentation"
        echo "• CREDENTIALS_GUIDE.md - Setup guide"
        echo
        if command_exists code; then
            read -p "Open README_FACE_AUTH.md in VS Code? (y/n): " open_doc
            if [ "$open_doc" = "y" ] || [ "$open_doc" = "Y" ]; then
                code README_FACE_AUTH.md
            fi
        fi
        ;;
    6)
        echo -e "${GREEN}👋 Goodbye!${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}❌ Invalid option${NC}"
        exit 1
        ;;
esac

echo
echo -e "${GREEN}✅ Session completed!${NC}"
echo -e "${BLUE}🚀 Run ./face_auth_launcher.sh again to restart${NC}"
