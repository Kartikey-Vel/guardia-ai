#!/usr/bin/env python3
"""
Guardia AI Enhanced Surveillance - Installation & Verification
Complete setup and verification script for enhanced surveillance features
"""

import subprocess
import sys
import os
import importlib.util

def install_package(package):
    """Install a Python package"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        return False

def check_package(package_name, import_name=None):
    """Check if a package is installed and can be imported"""
    if import_name is None:
        import_name = package_name
    
    try:
        spec = importlib.util.find_spec(import_name)
        if spec is not None:
            return True
    except ImportError:
        pass
    return False

def install_enhanced_dependencies():
    """Install all enhanced surveillance dependencies"""
    print("🔧 ENHANCED SURVEILLANCE SETUP")
    print("=" * 50)
    
    # Essential enhanced packages
    enhanced_packages = [
        ('psutil', 'psutil'),           # System monitoring
        ('plyer', 'plyer'),             # Desktop notifications  
        ('schedule', 'schedule'),       # Task scheduling
        ('face_recognition', 'face_recognition'),  # Advanced face recognition
        ('requests', 'requests'),       # HTTP requests
        ('opencv-python', 'cv2'),       # Computer vision
        ('numpy', 'numpy'),             # Numerical computing
        ('pymongo', 'pymongo'),         # MongoDB driver
    ]
    
    results = {}
    
    print("🔍 Checking enhanced surveillance dependencies...")
    
    for package, import_name in enhanced_packages:
        print(f"\n📦 Checking {package}...")
        
        if check_package(package, import_name):
            print(f"   ✅ {package} is already installed")
            results[package] = "✅ Available"
        else:
            print(f"   ⚠️ {package} not found, installing...")
            if install_package(package):
                print(f"   ✅ {package} installed successfully")
                results[package] = "✅ Installed"
            else:
                print(f"   ❌ Failed to install {package}")
                results[package] = "❌ Failed"
    
    return results

def verify_enhanced_surveillance():
    """Verify enhanced surveillance system"""
    print("\n🧪 ENHANCED SURVEILLANCE VERIFICATION")
    print("=" * 50)
    
    # Add src to path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    src_path = os.path.join(current_dir, 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    try:
        print("🤖 Testing enhanced surveillance import...")
        from modules.advanced_surveillance import AdvancedSurveillanceSystem, start_enhanced_advanced_surveillance
        print("   ✅ Enhanced surveillance module imported successfully")
        
        print("🏥 Testing system initialization...")
        surveillance = AdvancedSurveillanceSystem("setup@test.com")
        print("   ✅ Enhanced surveillance system initialized")
        
        print("📊 Testing health monitoring...")
        report = surveillance.get_system_health_report()
        print(f"   ✅ Health report generated: {len(report)} metrics")
        
        print("📱 Testing notification system...")
        import time
        test_alert = {
            'type': 'SETUP_TEST',
            'priority': 'MEDIUM', 
            'timestamp': time.time(),
            'data': {'description': 'Enhanced surveillance setup test'}
        }
        surveillance._send_desktop_notification(test_alert, "Setup verification test")
        print("   ✅ Desktop notification system working")
        
        print("🎥 Testing recording system...")
        surveillance._initialize_video_recording()
        print("   ✅ Video recording system initialized")
        
        return True
        
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Verification error: {e}")
        return False

def create_startup_scripts():
    """Create convenient startup scripts"""
    print("\n📝 Creating startup scripts...")
    
    # Windows batch script
    batch_content = """@echo off
echo 🚀 Guardia AI Enhanced Surveillance Launcher
echo =========================================

cd /d "%~dp0"

echo 🔍 Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Please install Python 3.7+ and try again.
    pause
    exit /b 1
)

echo ✅ Python found
echo 🏁 Starting Enhanced Surveillance...
echo.

python launch_enhanced_surveillance.py

echo.
echo 👋 Enhanced Surveillance session ended.
pause
"""
    
    try:
        with open('start_enhanced_surveillance.bat', 'w') as f:
            f.write(batch_content)
        print("   ✅ Windows batch script created: start_enhanced_surveillance.bat")
    except Exception as e:
        print(f"   ⚠️ Failed to create batch script: {e}")

def main():
    """Main setup function"""
    print("🛡️ GUARDIA AI - ENHANCED SURVEILLANCE SETUP")
    print("=" * 60)
    print("Setting up enhanced surveillance with all advanced features...")
    
    # Install dependencies
    install_results = install_enhanced_dependencies()
    
    # Verify installation
    verification_success = verify_enhanced_surveillance()
    
    # Create startup scripts
    create_startup_scripts()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SETUP SUMMARY")
    print("=" * 60)
    
    print("🔧 Dependencies:")
    for package, status in install_results.items():
        print(f"   • {package}: {status}")
    
    print(f"\n🤖 Enhanced Surveillance: {'✅ VERIFIED' if verification_success else '❌ ISSUES'}")
    
    if verification_success and all(status.startswith('✅') for status in install_results.values()):
        print("\n🎉 SETUP COMPLETE! Enhanced Surveillance Ready!")
        print("\n🚀 Start Options:")
        print("   1. Windows: Double-click start_enhanced_surveillance.bat")
        print("   2. Python: python launch_enhanced_surveillance.py")
        print("   3. Main App: cd src && python main.py (select option 3)")
        print("\n✨ Enhanced Features Available:")
        print("   ✅ Advanced Face Recognition")
        print("   ✅ Desktop Notifications")
        print("   ✅ Automatic Video Recording") 
        print("   ✅ System Health Monitoring")
        print("   ✅ Scheduled Maintenance")
        print("   ✅ Multi-channel Alerts")
    else:
        print("\n⚠️ SETUP INCOMPLETE - Some issues detected")
        print("🔧 Troubleshooting:")
        print("   • Check Python version (3.7+ required)")
        print("   • Install missing packages manually")
        print("   • Check file permissions")
        print("   • Try running as administrator")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
