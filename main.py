#!/usr/bin/env python3
"""
Guardia AI - Main Entry Point
A streamlined AI-powered surveillance system
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.core.guardian import GuardianSystem
from src.utils.logger import setup_logging
from src.utils.cli import display_banner, get_user_choice
import config.settings as settings

def main():
    """Main application entry point"""
    # Setup logging
    setup_logging()
    
    # Display banner
    display_banner()
    
    # Initialize Guardian system
    guardian = GuardianSystem()
    
    while True:
        print("\n" + "="*50)
        print("🛡️  GUARDIA AI - SURVEILLANCE SYSTEM")
        print("="*50)
        print("1. 👤 User Management")
        print("2. 👨‍👩‍👧‍👦 Family Management")
        print("3. 🎥 Start Surveillance")
        print("4. 📊 View System Status")
        print("5. ⚙️  System Settings")
        print("6. 🚪 Exit")
        
        choice = get_user_choice("Select an option (1-6): ", ["1", "2", "3", "4", "5", "6"])
        
        try:
            if choice == "1":
                guardian.user_management_menu()
            elif choice == "2":
                guardian.family_management_menu()
            elif choice == "3":
                guardian.start_surveillance()
            elif choice == "4":
                guardian.show_system_status()
            elif choice == "5":
                guardian.settings_menu()
            elif choice == "6":
                print("👋 Goodbye! Stay safe!")
                break
                
        except KeyboardInterrupt:
            print("\n\n⚠️ Operation cancelled by user")
        except Exception as e:
            print(f"❌ Error: {e}")
            if settings.DEBUG_MODE:
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    main()
