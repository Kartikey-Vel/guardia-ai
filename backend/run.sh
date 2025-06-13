#!/bin/bash

echo "🛡️ Guardia AI - Smart Home Surveillance System"
echo "==============================================="

# Set up environment variables for Docker
export DISPLAY=host.docker.internal:0

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "❌ Python is not installed or not in PATH"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

# If no arguments provided, show help
if [ $# -eq 0 ]; then
    echo "Usage: ./run.sh [setup|run|docker|status|clean|help]"
    echo ""
    echo "Commands:"
    echo "  setup  - Setup the project environment"
    echo "  run    - Run the application natively"
    echo "  docker - Run using Docker"
    echo "  status - Show current status"
    echo "  clean  - Clean all data"
    echo "  help   - Show help"
    echo ""
    echo "Example: ./run.sh setup"
    exit 0
fi

# Run the Python runner with the provided command
$PYTHON_CMD runner.py "$1"

# Check exit status
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Command failed. Check the output above."
    exit 1
fi

# Guardia AI Docker Runner Script

set -e

echo "🛡️  Guardia AI Docker Setup"
echo "=========================="

# Create required directories
echo "📁 Creating required directories..."
mkdir -p data images encodings faces detected/known detected/unknown logs config

# Function to display usage
usage() {
    echo "Usage: $0 [full|minimal|stop|logs|status]"
    echo ""
    echo "Commands:"
    echo "  full     - Run full AI surveillance (default)"
    echo "  minimal  - Run minimal motion detection"
    echo "  stop     - Stop all containers"
    echo "  logs     - Show container logs"
    echo "  status   - Show container status"
    echo "  clean    - Remove all containers and images"
    exit 1
}

# Parse command line arguments
COMMAND=${1:-full}

case $COMMAND in
    "full")
        echo "🚀 Starting full AI surveillance..."
        docker-compose up --build guardia-ai
        ;;
    "minimal")
        echo "🚀 Starting minimal motion detection..."
        docker-compose --profile minimal up --build guardia-ai-minimal
        ;;
    "stop")
        echo "🛑 Stopping all containers..."
        docker-compose down
        ;;
    "logs")
        echo "📋 Showing container logs..."
        docker-compose logs -f
        ;;
    "status")
        echo "📊 Container status:"
        docker-compose ps
        echo ""
        echo "📊 Health status:"
        docker inspect guardia-surveillance --format='{{.State.Health.Status}}' 2>/dev/null || echo "Container not running"
        ;;
    "clean")
        echo "🧹 Cleaning up containers and images..."
        docker-compose down --rmi all --volumes --remove-orphans
        ;;
    *)
        usage
        ;;
esac
