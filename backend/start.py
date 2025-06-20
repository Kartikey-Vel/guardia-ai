#!/usr/bin/env python3
"""
Quick start script for Guardia AI
"""

import subprocess
import sys
import os

def check_python_compatibility():
    """Check Python version compatibility"""
    if sys.version_info >= (3, 13):
        print("⚠️ Python 3.13 detected!")
        print("Some packages may not be compatible with Python 3.13")
        print("Recommended: Use Python 3.9-3.12 for best compatibility")
        
        response = input("Continue anyway? (y/n): ").strip().lower()
        if response != 'y':
            print("Consider installing Python 3.11:")
            print("https://www.python.org/downloads/release/python-3110/")
            return False
    
    return True

def main():
    print("🚀 Quick Start - Guardia AI")
    print("=" * 30)
    
    # Check Python compatibility
    if not check_python_compatibility():
        return
    
    # Check if this is the first run
    if not os.path.exists("data") or not os.path.exists("src"):
        print("🔧 First run detected. Setting up environment...")
        subprocess.run([sys.executable, "runner.py", "setup"])
    
    print("🎯 Starting Guardia AI...")
    try:
        subprocess.run([sys.executable, "runner.py", "run"])
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n🔧 Troubleshooting steps:")
        print("1. Run: python setup.py")
        print("2. Check: python runner.py status")
        print("3. Consider using Python 3.9-3.12")

if __name__ == "__main__":
    main()
