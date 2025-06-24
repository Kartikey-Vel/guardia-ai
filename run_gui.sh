#!/bin/bash
"""
Guardia AI Enhanced Launcher Script
Activates virtual environment and runs the enhanced application
"""

echo "🛡️ Starting Guardia AI Enhanced Security System..."

# Activate virtual environment
if [ -d ".venv" ]; then
    echo "📦 Activating virtual environment..."
    source .venv/bin/activate
else
    echo "❌ Virtual environment not found. Please run: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Check if dependencies are installed
echo "🔍 Checking dependencies..."
python -c "import ultralytics, mediapipe, cv2, numpy, PySide6" 2>/dev/null || {
    echo "⚠️ Some dependencies missing. Installing..."
    pip install -r requirements.txt
}

echo "🚀 Launching Enhanced Dashboard..."
# Launch the enhanced application
python -m guardia_ai.main

echo "👋 Guardia AI session ended."
