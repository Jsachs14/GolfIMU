#!/usr/bin/env python3
"""
GolfIMU System Launcher
Simple launcher script for the complete GolfIMU system.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add scripts directory to path for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

# Import common utilities
from utils import setup_project_paths, verify_project_structure, find_test_directories

# Setup project paths
project_root = setup_project_paths()
scripts_dir = Path(__file__).parent


def print_banner():
    """Print the GolfIMU banner"""
    print("🏌️  GolfIMU System Launcher")
    print("=" * 50)
    print("Advanced Golf Swing Analysis System")
    print("Real-time IMU-based golf swing tracking and analysis")
    print("=" * 50)


def check_prerequisites():
    """Check if all prerequisites are met"""
    print("Checking prerequisites...")
    
    # Verify project structure
    if not verify_project_structure(project_root):
        print("❌ Error: Invalid project structure")
        return False
    
    # Check if virtual environment is activated
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Warning: Virtual environment not detected")
        print("   It's recommended to activate the virtual environment first:")
        print("   source venv/bin/activate  # macOS/Linux")
        print("   venv\\Scripts\\activate     # Windows")
        response = input("   Continue anyway? (y/N): ").strip().lower()
        if response != 'y':
            return False
    
    # Check if Redis is available
    try:
        result = subprocess.run(['redis-cli', 'ping'], 
                              capture_output=True, text=True, timeout=2)
        if result.returncode == 0 and 'PONG' in result.stdout:
            print("✅ Redis server is running")
        else:
            print("⚠️  Redis server not detected")
            print("   The system will attempt to start Redis automatically")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("⚠️  Redis CLI not found")
        print("   Please install Redis: brew install redis (macOS)")
        response = input("   Continue anyway? (y/N): ").strip().lower()
        if response != 'y':
            return False
    
    print("✅ Prerequisites check completed")
    return True


def show_menu():
    """Show the main menu"""
    print("\nChoose an option:")
    print("1. 🚀 Launch Complete System (Backend + Embedded)")
    print("2. 🔧 Upload Arduino Firmware Only")
    print("3. 🖥️  Launch Backend Only (No Arduino)")
    print("4. 📊 Run Tests")
    print("5. 📖 Show Setup Instructions")
    print("6. ❌ Exit")
    
    while True:
        try:
            choice = input("\nEnter your choice (1-6): ").strip()
            if choice in ['1', '2', '3', '4', '5', '6']:
                return choice
            else:
                print("Please enter a number between 1 and 6")
        except KeyboardInterrupt:
            print("\nExiting...")
            return '6'


def launch_complete_system():
    """Launch the complete GolfIMU system"""
    print("\n🚀 Launching Complete GolfIMU System...")
    print("This will start Redis, connect to Arduino, and begin monitoring.")
    
    try:
        # Run the main system runner
        result = subprocess.run([
            sys.executable, str(scripts_dir / "run_golfimu_system.py")
        ])
        
        if result.returncode == 0:
            print("✅ System stopped normally")
        else:
            print(f"❌ System exited with code {result.returncode}")
            
    except KeyboardInterrupt:
        print("\n⏹️  System interrupted by user")
    except Exception as e:
        print(f"❌ Error launching system: {e}")


def upload_firmware():
    """Upload Arduino firmware"""
    print("\n🔧 Uploading Arduino Firmware...")
    print("This will compile and upload the firmware to your Teensy 4.0.")
    
    try:
        result = subprocess.run([
            sys.executable, str(scripts_dir / "upload_arduino_firmware.py")
        ])
        
        if result.returncode == 0:
            print("✅ Firmware upload completed")
        else:
            print(f"❌ Firmware upload failed with code {result.returncode}")
            
    except KeyboardInterrupt:
        print("\n⏹️  Upload interrupted by user")
    except Exception as e:
        print(f"❌ Error uploading firmware: {e}")


def launch_backend_only():
    """Launch backend only (no Arduino)"""
    print("\n🖥️  Launching Backend Only...")
    print("This will start Redis and the backend system without Arduino.")
    
    try:
        # Start Redis first
        print("Starting Redis server...")
        redis_process = subprocess.Popen([
            'redis-server', str(project_root / "redis.conf")
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a moment for Redis to start
        import time
        time.sleep(3)
        
        # Run the backend
        print("Starting backend...")
        result = subprocess.run([
            sys.executable, str(project_root / "backend" / "run_backend.py")
        ])
        
        # Stop Redis
        redis_process.terminate()
        redis_process.wait()
        
        if result.returncode == 0:
            print("✅ Backend stopped normally")
        else:
            print(f"❌ Backend exited with code {result.returncode}")
            
    except KeyboardInterrupt:
        print("\n⏹️  Backend interrupted by user")
        if 'redis_process' in locals():
            redis_process.terminate()
    except Exception as e:
        print(f"❌ Error launching backend: {e}")


def run_tests():
    """Run the test suite"""
    print("\n📊 Running Tests...")
    
    # Find all test directories
    test_dirs = find_test_directories(project_root)
    
    if not test_dirs:
        print("❌ No test directories found")
        return
    
    print(f"Found {len(test_dirs)} test directory(ies):")
    for test_dir in test_dirs:
        print(f"  - {test_dir.relative_to(project_root)}")
    
    try:
        # Run tests for each directory
        all_passed = True
        for test_dir in test_dirs:
            print(f"\nRunning tests in {test_dir.relative_to(project_root)}...")
            
            result = subprocess.run([
                sys.executable, '-m', 'pytest', str(test_dir), '-v'
            ])
            
            if result.returncode != 0:
                all_passed = False
                print(f"❌ Tests in {test_dir.relative_to(project_root)} failed")
            else:
                print(f"✅ Tests in {test_dir.relative_to(project_root)} passed")
        
        if all_passed:
            print("\n✅ All tests passed!")
        else:
            print("\n❌ Some tests failed")
            
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
    except Exception as e:
        print(f"❌ Error running tests: {e}")


def show_setup_instructions():
    """Show setup instructions"""
    print("\n📖 GolfIMU Setup Instructions")
    print("=" * 50)
    
    print("\n1. 🏗️  Hardware Setup:")
    print("   - Connect Teensy 4.0 to your computer via USB")
    print("   - Connect SparkFun BNO08x IMU to Teensy:")
    print("     * VIN -> 3.3V")
    print("     * GND -> GND")
    print("     * SDA -> 18")
    print("     * SCL -> 19")
    
    print("\n2. 🔧 Software Setup:")
    print("   - Install Arduino CLI:")
    print("     macOS: brew install arduino-cli")
    print("     Linux: curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh")
    print("     Windows: Download from https://github.com/arduino/arduino-cli/releases")
    
    print("\n3. 🐍 Python Setup:")
    print("   - Create virtual environment: python3 -m venv venv")
    print("   - Activate: source venv/bin/activate (macOS/Linux)")
    print("   - Install dependencies: pip install -r requirements.txt")
    
    print("\n4. 🗄️  Redis Setup:")
    print("   - Install Redis: brew install redis (macOS)")
    print("   - Or use the provided config: redis-server redis.conf")
    
    print("\n5. 🚀 Running the System:")
    print("   - Upload firmware: python scripts/upload_arduino_firmware.py")
    print("   - Launch system: python scripts/run_golfimu_system.py")
    print("   - Or use this launcher: python scripts/launch_golfimu.py")
    
    print("\n6. 📊 Testing:")
    print("   - Run tests: python -m pytest backend/tests/ -v")
    print("   - Run with coverage: python -m pytest backend/tests/ --cov=backend")
    
    print("\n📚 For more details, see SETUP.md and README.md")


def main():
    """Main launcher function"""
    print_banner()
    
    if not check_prerequisites():
        sys.exit(1)
    
    while True:
        choice = show_menu()
        
        if choice == '1':
            launch_complete_system()
        elif choice == '2':
            upload_firmware()
        elif choice == '3':
            launch_backend_only()
        elif choice == '4':
            run_tests()
        elif choice == '5':
            show_setup_instructions()
        elif choice == '6':
            print("\n👋 Goodbye!")
            break
        
        # Ask if user wants to continue
        if choice != '6':
            response = input("\nReturn to main menu? (Y/n): ").strip().lower()
            if response == 'n':
                print("\n👋 Goodbye!")
                break


if __name__ == "__main__":
    main() 