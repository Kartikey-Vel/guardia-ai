#!/bin/bash

# Guardia AI Enhanced System - Quick Start Script
# This script sets up and starts the system automatically

set -e

echo "🚀 Starting Guardia AI Enhanced System..."
echo "========================================"

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | grep -oP '(?<=Python )\d+\.\d+' || echo "0.0")
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo "✅ Python $python_version found (required: $required_version+)"
else
    echo "❌ Python $required_version+ required, found: $python_version"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📚 Installing dependencies..."
pip install -r requirements_enhanced.txt

# Create storage directories
echo "📁 Creating storage directories..."
mkdir -p storage/{media,images,videos,faces,logs}

# Check if .env exists, if not copy from .env.example
if [ ! -f ".env" ]; then
    echo "⚙️ Setting up environment configuration..."
    cp .env.example .env
    echo "📝 Environment file created from template"
fi

# Check if Google Cloud credentials are configured
if [ -z "$GOOGLE_SERVICE_ACCOUNT_KEY" ]; then
    echo "⚠️ Warning: Google Cloud credentials not configured"
    echo "Set the GOOGLE_SERVICE_ACCOUNT_KEY environment variable with your service account JSON"
    echo "Or configure individual OAuth credentials in the .env file"
else
    echo "✅ Google Cloud credentials configured"
fi

# Run system tests
echo "🧪 Running system tests..."
if [ -f "test_system.sh" ]; then
    chmod +x test_system.sh
    if ./test_system.sh; then
        echo "✅ System tests passed!"
    else
        echo "⚠️ Some system tests failed, but continuing..."
    fi
fi

# Start the server
echo ""
echo "🎉 Starting Guardia AI Enhanced System..."
echo "📍 API Documentation: http://localhost:8000/docs"
echo "❤️ Health Check: http://localhost:8000/health"
echo "🔌 WebSocket Test: ws://localhost:8000/ws"
echo ""
echo "Press Ctrl+C to stop the server"
echo "========================================"

# Start the application
python start_server.py
