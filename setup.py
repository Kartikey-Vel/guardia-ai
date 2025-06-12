#!/usr/bin/env python3
"""
Setup script for Guardia AI
"""

import sys
import subprocess
import os
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    
    if sys.version_info >= (3, 13):
        print("⚠️  Python 3.13 detected. Some packages may have compatibility issues.")
        print("Consider using Python 3.9-3.12 for best compatibility.")
    
    return True

def install_system_dependencies():
    """Install system dependencies based on OS"""
    if os.name == 'nt':  # Windows
        print("🪟 Windows detected")
        print("Please ensure you have Visual Studio Build Tools installed")
        print("Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/")
    else:  # Linux/Mac
        print("🐧 Unix-like system detected")
        print("Please ensure cmake and build-essential are installed")

def install_packages():
    """Install Python packages with better error handling"""
    packages = [
        "setuptools>=65.0.0",
        "wheel>=0.38.0",
        "cmake>=3.18.0",
        "numpy>=1.24.0,<2.0.0",
        "pillow>=8.3.0",
        "opencv-python>=4.8.0",
        "scipy>=1.9.0",        "google-cloud-videointelligence>=2.0.0", # Ensure version
        "google-cloud-storage>=2.0.0", # For GCS upload
        "python-dotenv>=0.20.0", # Added
        "pymongo>=4.0.0" # Added
    ]
    
    failed_packages = []
    
    for package in packages:
        print(f"📦 Installing {package}...")
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install", 
                "--upgrade", package
            ], check=True, capture_output=True)
            print(f"✅ {package} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {package}")
            failed_packages.append(package)
            
    return failed_packages

def main():
    print("🛡️ Guardia AI Setup")
    print("=" * 40)
    
    if not check_python_version():
        return False
    
    install_system_dependencies()
    
    print("\n📦 Installing Python packages...")
    failed = install_packages()
    
    if failed:
        print(f"\n❌ Failed to install: {', '.join(failed)}")
        print("\n🔧 Troubleshooting:")
        print("1. Update pip: python -m pip install --upgrade pip")
        print("2. Install Visual Studio Build Tools (Windows)")
        print("3. Try installing packages individually")
        print("4. Consider using Python 3.9-3.12 instead of 3.13")
        return False
    else:
        print("\n✅ All packages installed successfully!")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
