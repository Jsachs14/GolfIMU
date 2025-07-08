#!/usr/bin/env python3
"""
Arduino Firmware Upload Script for GolfIMU
Uploads the embedded firmware to the Teensy 4.0 board.
"""

import os
import sys
import subprocess
import time
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add scripts directory to path for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

# Import common utilities
from utils import setup_project_paths, verify_project_structure

# Setup project paths
project_root = setup_project_paths()

# Import global configuration
from global_config import *
firmware_path = project_root / "embedded" / "firmware" / "GolfIMU_Firmware"
firmware_file = firmware_path / "GolfIMU_Firmware.ino"


def check_arduino_cli():
    """Check if Arduino CLI is installed"""
    try:
        result = subprocess.run(['arduino-cli', 'version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info(f"Arduino CLI found: {result.stdout.strip()}")
            return True
        else:
            logger.error("Arduino CLI not working properly")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        logger.error("Arduino CLI not found. Please install it first.")
        logger.info("Installation instructions:")
        logger.info("  macOS: brew install arduino-cli")
        logger.info("  Linux: curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh")
        logger.info("  Windows: Download from https://github.com/arduino/arduino-cli/releases")
        return False


def check_teensy_board():
    """Check if Teensy board is connected"""
    try:
        result = subprocess.run(['arduino-cli', 'board', 'list'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if 'teensy' in line.lower() or 'usb serial' in line.lower():
                    logger.info(f"Found board: {line}")
                    return True
            logger.warning("No Teensy board found. Please connect your Teensy 4.0.")
            return False
        else:
            logger.error("Failed to list boards")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.error(f"Error checking boards: {e}")
        return False


def install_teensy_core():
    """Install Teensy core for Arduino CLI"""
    try:
        logger.info("Installing Teensy core...")
        
        # Add Teensy core index
        result = subprocess.run([
            'arduino-cli', 'core', 'update-index', 
            '--additional-urls', 'https://www.pjrc.com/teensy/package_teensy_index.json'
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            logger.error(f"Failed to update core index: {result.stderr}")
            return False
        
        # Install Teensy core
        result = subprocess.run([
            'arduino-cli', 'core', 'install', 'teensy:avr',
            '--additional-urls', 'https://www.pjrc.com/teensy/package_teensy_index.json'
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            logger.info("Teensy core installed successfully")
            return True
        else:
            logger.error(f"Failed to install Teensy core: {result.stderr}")
            return False
            
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.error(f"Error installing Teensy core: {e}")
        return False


def install_sparkfun_library():
    """Install SparkFun BNO08x library"""
    try:
        logger.info("Installing SparkFun BNO08x library...")
        
        # Add SparkFun library index
        result = subprocess.run([
            'arduino-cli', 'lib', 'update-index',
            '--additional-urls', 'https://raw.githubusercontent.com/sparkfun/Arduino_Boards/master/IDE_Board_Manager/package_sparkfun_index.json'
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            logger.error(f"Failed to update library index: {result.stderr}")
            return False
        
        # Install SparkFun BNO08x library
        result = subprocess.run([
            'arduino-cli', 'lib', 'install', 'SparkFun_BNO08x_Arduino_Library'
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            logger.info("SparkFun BNO08x library installed successfully")
            return True
        else:
            logger.error(f"Failed to install library: {result.stderr}")
            return False
            
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.error(f"Error installing library: {e}")
        return False


def compile_firmware():
    """Compile the firmware"""
    try:
        logger.info("Compiling firmware...")
        
        result = subprocess.run([
            'arduino-cli', 'compile',
            '--fqbn', TEENSY_BOARD,
            str(firmware_path)
        ], capture_output=True, text=True, timeout=ARDUINO_CLI_TIMEOUT)
        
        if result.returncode == 0:
            logger.info("Firmware compiled successfully")
            return True
        else:
            logger.error(f"Compilation failed: {result.stderr}")
            return False
            
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.error(f"Error compiling firmware: {e}")
        return False


def upload_firmware():
    """Upload firmware to Teensy board"""
    try:
        logger.info("Uploading firmware to Teensy...")
        
        # Find Teensy port
        result = subprocess.run(['arduino-cli', 'board', 'list'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            logger.error("Failed to list boards")
            return False
        
        # Parse board list to find Teensy
        teensy_port = None
        lines = result.stdout.strip().split('\n')
        for line in lines:
            if 'teensy' in line.lower() or 'usb serial' in line.lower():
                parts = line.split()
                if len(parts) >= 2:
                    teensy_port = parts[0]
                    break
        
        if not teensy_port:
            logger.error("No Teensy port found")
            return False
        
        logger.info(f"Found Teensy on port: {teensy_port}")
        
        # Upload firmware
        result = subprocess.run([
            'arduino-cli', 'upload',
            '--fqbn', TEENSY_BOARD,
            '--port', teensy_port,
            str(firmware_path)
        ], capture_output=True, text=True, timeout=ARDUINO_CLI_TIMEOUT)
        
        if result.returncode == 0:
            logger.info("Firmware uploaded successfully!")
            return True
        else:
            logger.error(f"Upload failed: {result.stderr}")
            return False
            
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.error(f"Error uploading firmware: {e}")
        return False


def verify_firmware_file():
    """Verify that the firmware file exists"""
    if not firmware_file.exists():
        logger.error(f"Firmware file not found: {firmware_file}")
        logger.info("Expected location: embedded/firmware/GolfIMU_Firmware/GolfIMU_Firmware.ino")
        return False
    
    logger.info(f"Found firmware file: {firmware_file}")
    return True


def main():
    """Main upload process"""
    print("🏌️  GolfIMU Arduino Firmware Uploader")
    print("=" * 50)
    
    # Verify project structure
    if not verify_project_structure(project_root):
        print("Error: Invalid project structure")
        sys.exit(1)
    
    # Verify firmware file exists
    if not verify_firmware_file():
        sys.exit(1)
    
    # Check Arduino CLI
    if not check_arduino_cli():
        sys.exit(1)
    
    # Install Teensy core if needed
    if not install_teensy_core():
        logger.warning("Failed to install Teensy core. Continuing anyway...")
    
    # Install SparkFun library if needed
    if not install_sparkfun_library():
        logger.warning("Failed to install SparkFun library. Continuing anyway...")
    
    # Check for Teensy board
    if not check_teensy_board():
        logger.warning("No Teensy board detected. Make sure it's connected.")
        response = input("Continue with compilation only? (y/N): ").strip().lower()
        if response != 'y':
            sys.exit(1)
    
    # Compile firmware
    if not compile_firmware():
        logger.error("Compilation failed. Please check the firmware code.")
        sys.exit(1)
    
    # Upload firmware (if board is connected)
    if check_teensy_board():
        if upload_firmware():
            print("\n✅ Firmware upload completed successfully!")
            print("The Teensy is now running the GolfIMU firmware.")
            print("You can now run the main system with: python scripts/run_golfimu_system.py")
        else:
            logger.error("Upload failed. Please check the connection and try again.")
            sys.exit(1)
    else:
        print("\n⚠️  No Teensy board detected for upload.")
        print("The firmware has been compiled successfully.")
        print("Connect your Teensy and run this script again to upload.")


if __name__ == "__main__":
    main() 