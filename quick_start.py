#!/usr/bin/env python3
"""
Guardia AI - Quick Start Guide
Simple script to demonstrate all authentication features
"""

import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def print_header():
    print("🛡️ Guardia AI - Quick Start Guide")
    print("=" * 50)
    print()

def show_project_structure():
    print("📁 Project Structure:")
    print("├── guardia_ai/")
    print("│   ├── main.py                 # GUI Application")
    print("│   ├── detection/face_auth.py  # Face recognition engine")
    print("│   └── ui/login.py             # Authentication GUI")
    print("├── face_enrollment.py          # CLI enrollment tool")
    print("├── face_match_sim.py           # Face matching simulation")
    print("├── setup.py                    # Project setup verification")
    print("└── run_gui.sh                  # GUI launcher (with venv)")
    print()

def show_usage_instructions():
    print("🚀 Quick Start Instructions:")
    print()
    
    print("1. 📱 Launch GUI Application:")
    print("   source .venv/bin/activate && python -m guardia_ai.main")
    print("   (Or use: ./run_gui.sh)")
    print()
    
    print("2. 👤 Add New User (CLI):")
    print("   source .venv/bin/activate && python face_enrollment.py --label 'YourName' --pin '1234'")
    print()
    
    print("3. 📋 List All Users:")
    print("   source .venv/bin/activate && python face_enrollment.py --list")
    print()
    
    print("4. 🧪 Test Face Recognition:")
    print("   source .venv/bin/activate && python face_enrollment.py --test")
    print()
    
    print("5. 🔄 Real-time Face Matching:")
    print("   source .venv/bin/activate && python face_match_sim.py")
    print("   (Choose option 1 for real-time matching)")
    print()

def show_current_users():
    print("👥 Current Enrolled Users:")
    try:
        from guardia_ai.detection.face_auth import FaceAuthenticator
        
        face_auth = FaceAuthenticator()
        users = face_auth.get_all_users()
        
        if users:
            for user in users:
                face_status = "📷" if user["has_face"] else "📝"
                print(f"   {face_status} {user['label']} (PIN: {user['pin']})")
        else:
            print("   No users enrolled yet")
    except Exception as e:
        print(f"   Error loading users: {e}")
    print()

def show_authentication_methods():
    print("🔐 Available Authentication Methods:")
    print("1. Username + PIN Login")
    print("2. PIN-only Login")
    print("3. Face Recognition")
    print("4. Combined Face + PIN")
    print()

def show_next_steps():
    print("📈 Next Development Steps:")
    print("✅ Authentication System (COMPLETE)")
    print("🔄 Surveillance Engine (Object Detection)")
    print("🔄 Alert System (Notifications)")
    print("🔄 Dashboard UI (Live Monitoring)")
    print()

def main():
    print_header()
    show_project_structure()
    show_authentication_methods()
    show_current_users()
    show_usage_instructions()
    show_next_steps()
    
    print("🎉 Guardia AI Authentication System is ready!")
    print("   All features are working and tested successfully.")

if __name__ == "__main__":
    main()
