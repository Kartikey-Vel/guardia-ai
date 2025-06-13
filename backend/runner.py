#!/usr/bin/env python3
"""
Guardia AI Runner
Main entry point for the Smart Home Surveillance System
"""

import os
import sys
import subprocess
import argparse
import json
from pathlib import Path

class GuardiaRunner:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.src_path = self.project_root / "src"
        self.config_path = self.project_root / "config"
        
    def setup_environment(self):
        """Setup the project environment and directories"""
        print("🔧 Setting up Guardia AI environment...")
        
        # Create necessary directories
        directories = [
            "data", "images", "encodings", "faces",
            "detected/known", "detected/unknown",
            "src/modules", "src/utils",
            "config", "logs"
        ]
        
        for directory in directories:
            dir_path = self.project_root / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            
        # Create __init__.py files
        init_files = [
            "src/__init__.py",
            "src/modules/__init__.py", 
            "src/utils/__init__.py"
        ]
        
        for init_file in init_files:
            init_path = self.project_root / init_file
            init_path.touch()
            
        # Create config file if it doesn't exist
        config_file = self.config_path / "settings.py"
        if not config_file.exists():
            self.create_config_file()
            
        print("✅ Environment setup complete!")
        
    def create_config_file(self):
        """Create the configuration file"""
        config_content = '''# Configuration settings for Guardia AI
import os

# Database settings
DB_FILE = "data/db.json"

# Directory paths
ENCODINGS_DIR = "encodings"
FACES_DIR = "faces"
IMAGES_DIR = "images"
DETECTED_KNOWN_DIR = "detected/known"
DETECTED_UNKNOWN_DIR = "detected/unknown"
LOGS_DIR = "logs"

# Camera settings
DEFAULT_CAMERA_INDEX = 0
FACE_RECOGNITION_TOLERANCE = 0.6

# Security settings
MAX_OWNERS = 3
HASH_ALGORITHM = "sha256"
'''
        
        config_file = self.config_path / "settings.py"
        config_file.write_text(config_content)
        
    def install_dependencies(self):
        """Install missing dependencies"""
        print("📦 Installing dependencies...")
        
        # Update pip first
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                         check=True, capture_output=True)
            print("✅ pip updated")
        except subprocess.CalledProcessError:
            print("⚠️ Could not update pip")
        
        # Install setuptools and wheel first
        essential_packages = ["setuptools>=65.0.0", "wheel>=0.38.0"]
        for package in essential_packages:
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", package], 
                             check=True, capture_output=True)
                print(f"✅ {package} installed")
            except subprocess.CalledProcessError:
                print(f"❌ Failed to install {package}")
        
        # Try to run setup.py
        try:
            subprocess.run([sys.executable, "setup.py"], check=True)
            return True
        except subprocess.CalledProcessError:
            print("❌ Setup failed. Trying manual installation...")
            return self.manual_install()
    
    def manual_install(self):
        """Manual package installation with fallbacks"""
        # Install packages in order of dependency
        package_groups = [
            # Essential packages first
            ["numpy>=1.24.0", "pillow", "scipy"],
            # OpenCV (usually works)
            ["opencv-python"],
            # Problematic packages last
            ["cmake", "dlib", "face-recognition"]
        ]
        
        failed = []
        
        for group in package_groups:
            for package in group:
                try:
                    print(f"📦 Installing {package}...")
                    # Try with different flags for dlib and face-recognition
                    if "dlib" in package or "face-recognition" in package:
                        # Use --no-cache-dir and --verbose for problematic packages
                        result = subprocess.run([
                            sys.executable, "-m", "pip", "install", 
                            "--no-cache-dir", "--verbose", package
                        ], check=True, capture_output=True, text=True, timeout=600)
                    else:
                        result = subprocess.run([
                            sys.executable, "-m", "pip", "install", package
                        ], check=True, capture_output=True, text=True, timeout=300)
                    
                    print(f"✅ {package} installed")
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                    print(f"❌ Failed to install {package}")
                    failed.append(package)
                    
                    # Show specific error for dlib/face-recognition
                    if "dlib" in package or "face-recognition" in package:
                        print(f"   Error: {str(e)[:200]}...")
        
        if failed:
            print(f"\n❌ Could not install: {', '.join(failed)}")
            
            # Check if the problematic packages failed
            problematic = [p for p in failed if "dlib" in p or "face-recognition" in p]
            if problematic:
                print("\n🐳 RECOMMENDED SOLUTION: Use Docker")
                print("These packages have complex C++ dependencies that are easier to install in Docker.")
                print("\nTo use Docker instead:")
                print("1. Install Docker Desktop")
                print("2. Run: python runner.py docker")
                print("\n🔧 Alternative solutions:")
                print("1. Install Visual Studio Build Tools (Windows)")
                print("2. Use conda: conda install -c conda-forge dlib face_recognition")
                print("3. Use Python 3.9-3.11 instead of 3.13")
                
                # Ask if user wants to try Docker
                try:
                    response = input("\nWould you like to try Docker instead? (y/n): ").strip().lower()
                    if response == 'y':
                        return self.run_docker()
                except KeyboardInterrupt:
                    print("\nAborted by user.")
            
            return False
        
        return True

    def check_dependencies(self):
        """Check if all required dependencies are installed"""
        print("🔍 Checking dependencies...")
        
        # Check Python version first
        if sys.version_info >= (3, 13):
            print("⚠️ Python 3.13 detected. dlib and face-recognition may not work properly.")
            print("Consider using Python 3.9-3.12 for best compatibility.")
        elif sys.version_info < (3, 8):
            print("❌ Python 3.8+ is required for this project.")
            return False
        
        required_packages = {
            "numpy": "numpy",
            "cv2": "opencv-python", 
            "PIL": "pillow"
        }
        
        # Optional packages (will suggest Docker if missing)
        optional_packages = {
            "face_recognition": "face-recognition",
            "dlib": "dlib"
        }
        
        missing_packages = []
        missing_optional = []
        
        # Check required packages
        for import_name, package_name in required_packages.items():
            try:
                __import__(import_name)
                print(f"✅ {package_name} - OK")
            except ImportError:
                print(f"❌ {package_name} - MISSING")
                missing_packages.append(package_name)
        
        # Check optional packages
        for import_name, package_name in optional_packages.items():
            try:
                __import__(import_name)
                print(f"✅ {package_name} - OK")
            except ImportError:
                print(f"⚠️ {package_name} - MISSING (needed for face recognition)")
                missing_optional.append(package_name)
                
        # Handle missing packages
        if missing_packages:
            print(f"\n❌ Missing required packages: {', '.join(missing_packages)}")
            response = input("Install required packages? (y/n): ").strip().lower()
            if response == 'y':
                success = self.install_dependencies()
                if not success:
                    return False
            else:
                return False
        
        if missing_optional:
            print(f"\n⚠️ Missing optional packages: {', '.join(missing_optional)}")
            print("Face recognition features will not work without these packages.")
            print("\nOptions:")
            print("1. Try installing locally (may fail on Python 3.13)")
            print("2. Use Docker (recommended)")
            print("3. Continue without face recognition (limited functionality)")
            
            choice = input("Choose option (1/2/3): ").strip()
            if choice == "1":
                return self.install_dependencies()
            elif choice == "2":
                return self.run_docker()
            elif choice == "3":
                print("⚠️ Running with limited functionality (no face recognition)")
                return True
            else:
                return False
            
        print("✅ All dependencies are installed!")
        return True
        
    def run_native(self):
        """Run the application natively (without Docker)"""
        print("🚀 Starting Guardia AI (Native Mode)...")
        
        if not self.check_dependencies():
            return False
            
        # Add src to Python path
        sys.path.insert(0, str(self.src_path))
        
        try:
            # Import and run the main application
            from main import main
            main()
        except KeyboardInterrupt:
            print("\n🛑 Application stopped by user")
        except Exception as e:
            print(f"❌ Error running application: {e}")
            return False
            
        return True
        
    def run_docker(self):
        """Run the application using Docker"""
        print("🐳 Starting Guardia AI (Docker Mode)...")
        
        # Check if Docker is installed
        try:
            subprocess.run(["docker", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Docker is not installed or not in PATH")
            return False
            
        # Check if docker-compose is available
        try:
            subprocess.run(["docker-compose", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Docker Compose is not installed or not in PATH")
            return False
            
        try:
            # Try full version first
            print("🔄 Attempting full Docker build...")
            result = subprocess.run(["docker-compose", "up", "--build"], 
                                 check=True, capture_output=True, text=True, timeout=600)
            return True
        except subprocess.TimeoutExpired:
            print("⏰ Docker build timed out. Trying minimal version...")
            return self.run_minimal_docker()
        except subprocess.CalledProcessError as e:
            print(f"❌ Full Docker build failed: {e}")
            print("🔄 Trying minimal Docker version...")
            return self.run_minimal_docker()
        except KeyboardInterrupt:
            print("\n🛑 Docker container stopped by user")
            return True
    
    def run_minimal_docker(self):
        """Run minimal Docker version with basic functionality"""
        try:
            print("🐳 Starting minimal Docker version (motion detection only)...")
            subprocess.run([
                "docker-compose", "--profile", "minimal", 
                "up", "--build", "guardia-ai-minimal"
            ], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Minimal Docker build also failed: {e}")
            print("\n🔧 Docker troubleshooting:")
            print("1. Make sure Docker Desktop is running")
            print("2. Check Docker Desktop settings")
            print("3. Try: docker system prune")
            print("4. Use native installation instead")
            return False
        except KeyboardInterrupt:
            print("\n🛑 Minimal Docker container stopped by user")
            return True
        
    def create_sample_data(self):
        """Create sample data for testing"""
        print("📝 Creating sample data...")
        
        # Create sample images directory structure
        sample_images = self.project_root / "images" / "samples"
        sample_images.mkdir(exist_ok=True)
        
        # Create a sample database entry
        db_file = self.project_root / "data" / "db.json"
        if not db_file.exists():
            sample_db = {
                "owners": [],
                "settings": {
                    "max_owners": 3,
                    "created_at": "2025-01-01T00:00:00Z"
                }
            }
            
            with open(db_file, "w") as f:
                json.dump(sample_db, f, indent=4)
                
        print("✅ Sample data created!")
        
    def show_status(self):
        """Show the current status of the application"""
        print("📊 Guardia AI Status:")
        print("=" * 50)
        
        # Check directories
        directories = ["data", "images", "encodings", "faces", "detected", "logs"]
        for directory in directories:
            dir_path = self.project_root / directory
            status = "✅ EXISTS" if dir_path.exists() else "❌ MISSING"
            print(f"Directory {directory}: {status}")
            
        # Check database
        db_file = self.project_root / "data" / "db.json"
        if db_file.exists():
            try:
                with open(db_file, "r") as f:
                    data = json.load(f)
                    owner_count = len(data.get("owners", []))
                    print(f"Database: ✅ EXISTS ({owner_count} owners)")
            except Exception as e:
                print(f"Database: ❌ ERROR ({e})")
        else:
            print("Database: ❌ NOT FOUND")
            
        # Check encodings
        encodings_dir = self.project_root / "encodings"
        if encodings_dir.exists():
            encoding_files = list(encodings_dir.glob("*.npy"))
            print(f"Face encodings: ✅ {len(encoding_files)} files")
        else:
            print("Face encodings: ❌ NO ENCODINGS")
            
    def clean_data(self):
        """Clean all generated data"""
        print("🧹 Cleaning Guardia AI data...")
        
        # Directories to clean
        clean_dirs = ["data", "encodings", "faces", "detected", "logs"]
        
        for directory in clean_dirs:
            dir_path = self.project_root / directory
            if dir_path.exists():
                import shutil
                shutil.rmtree(dir_path)
                print(f"🗑️ Cleaned {directory}")
                
        print("✅ Data cleaning complete!")
        
    def show_help(self):
        """Show help information"""
        help_text = """
🛡️ Guardia AI Runner - Smart Home Surveillance System

Usage: python runner.py [command]

Commands:
  setup      - Setup the project environment
  run        - Run the application natively
  docker     - Run using Docker
  status     - Show current status
  sample     - Create sample data
  clean      - Clean all generated data
  help       - Show this help message

Examples:
  python runner.py setup
  python runner.py run
  python runner.py docker
  python runner.py status
"""
        print(help_text)

def main():
    parser = argparse.ArgumentParser(description="Guardia AI Runner")
    parser.add_argument("command", nargs="?", default="help",
                       choices=["setup", "run", "docker", "status", "sample", "clean", "help"],
                       help="Command to execute")
    
    args = parser.parse_args()
    runner = GuardiaRunner()
    
    # Always setup environment first
    runner.setup_environment()
    
    if args.command == "setup":
        print("✅ Setup complete! Run 'python runner.py run' to start the application.")
        
    elif args.command == "run":
        runner.run_native()
        
    elif args.command == "docker":
        runner.run_docker()
        
    elif args.command == "status":
        runner.show_status()
        
    elif args.command == "sample":
        runner.create_sample_data()
        
    elif args.command == "clean":
        runner.clean_data()
        
    elif args.command == "help":
        runner.show_help()
        
    else:
        runner.show_help()

if __name__ == "__main__":
    main()
