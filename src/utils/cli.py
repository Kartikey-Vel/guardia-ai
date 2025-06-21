"""
CLI utilities for user interaction
Simple and clean command line interface
"""
import sys
from typing import List, Optional

def display_banner():
    """Display the application banner"""
    banner = """
╔══════════════════════════════════════════════════════╗
║                    🛡️ GUARDIA AI                     ║
║              Advanced Surveillance System            ║
║                                                      ║
║    Protecting your home with AI-powered intelligence ║
╚══════════════════════════════════════════════════════╝
    """
    print(banner)

def get_user_choice(prompt: str, valid_choices: List[str]) -> str:
    """Get user input with validation"""
    while True:
        try:
            choice = input(f"\n{prompt}").strip()
            if choice in valid_choices:
                return choice
            else:
                print(f"❌ Invalid choice. Please select from: {', '.join(valid_choices)}")
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Goodbye!")
            sys.exit(0)

def get_user_input(prompt: str, required: bool = True) -> Optional[str]:
    """Get user input with optional validation"""
    while True:
        try:
            value = input(f"\n{prompt}").strip()
            if value or not required:
                return value if value else None
            else:
                print("❌ This field is required.")
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Goodbye!")
            sys.exit(0)

def confirm_action(message: str) -> bool:
    """Ask user for confirmation"""
    choice = get_user_choice(f"{message} (y/n): ", ["y", "yes", "n", "no"])
    return choice.lower() in ["y", "yes"]

def display_menu(title: str, options: List[str]) -> str:
    """Display a menu and get user choice"""
    print(f"\n{'='*50}")
    print(f"🎯 {title}")
    print("="*50)
    
    for i, option in enumerate(options, 1):
        print(f"{i}. {option}")
    
    valid_choices = [str(i) for i in range(1, len(options) + 1)]
    choice = get_user_choice(f"Select an option (1-{len(options)}): ", valid_choices)
    return choice

def print_status(message: str, status: str = "INFO"):
    """Print a status message with appropriate formatting"""
    icons = {
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "LOADING": "🔄"
    }
    
    icon = icons.get(status, "ℹ️")
    print(f"{icon} {message}")

def print_separator():
    """Print a visual separator"""
    print("-" * 50)
