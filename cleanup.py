#!/usr/bin/env python3
"""
Standalone cleanup script for Guardia AI
Run this if you have too many files in your project
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from utils.cleanup_utils import ProjectCleanup

def main():
    print("🛡️ Guardia AI - Project Cleanup Tool")
    print("=" * 40)
    
    project_root = Path(__file__).parent
    cleaner = ProjectCleanup(str(project_root))
    
    print("Choose cleanup option:")
    print("1. Analyze project size only")
    print("2. Clean temporary files")
    print("3. Clean old detection files (7+ days)")
    print("4. Clean large log files")
    print("5. Full cleanup (recommended)")
    print("6. Exit")
    
    choice = input("\nSelect option (1-6): ").strip()
    
    if choice == "1":
        cleaner.analyze_project_size()
    elif choice == "2":
        cleaner.clean_temp_files()
    elif choice == "3":
        cleaner.clean_detection_cache()
    elif choice == "4":
        cleaner.clean_logs()
    elif choice == "5":
        cleaner.full_cleanup()
    elif choice == "6":
        print("👋 Goodbye!")
        return
    else:
        print("❌ Invalid choice")
        return
    
    print("\n✅ Cleanup operation completed!")

if __name__ == "__main__":
    main()
