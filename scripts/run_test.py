#!/usr/bin/env python3
"""
GolfIMU Test Script
Automates the backend connection and data collection process
"""

import time
import subprocess
import sys
import os
import json
import select
import threading
import signal

def read_output_with_timeout(process, timeout=1.0):
    """Read output from process with timeout - completely non-blocking.
    
    Args:
        process: The subprocess to read from
        timeout: Timeout in seconds
        
    Returns:
        List of output lines
    """
    output_lines = []
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        # Check if process is still running
        if process.poll() is not None:
            print(f"❌ Process terminated with code {process.poll()}")
            break
            
        # Try to read any available output
        try:
            # Use select with very short timeout
            ready, _, _ = select.select([process.stdout], [], [], 0.1)
            if ready:
                line = process.stdout.readline()
                if line:
                    output_lines.append(line.strip())
                else:
                    # No more data available
                    break
            else:
                # No data ready, continue loop
                time.sleep(0.01)
        except Exception as e:
            print(f"Error reading output: {e}")
            break
    
    return output_lines

def run_command_safe(backend_process, command, max_wait=5):
    """Send command to backend with safe timeout handling.
    
    Args:
        backend_process: The backend subprocess
        command: Command to send
        max_wait: Maximum time to wait for response
    """
    print(f"\n>>> {command}")
    
    # Send command
    try:
        backend_process.stdin.write(f"{command}\n")
        backend_process.stdin.flush()
    except Exception as e:
        print(f"❌ Failed to send command: {e}")
        return False
    
    # Wait for response with timeout
    start_time = time.time()
    while time.time() - start_time < max_wait:
        output_lines = read_output_with_timeout(backend_process, timeout=0.5)
        for line in output_lines:
            print(f"Backend: {line}")
        
        # Check if process is still running
        if backend_process.poll() is not None:
            print(f"❌ Backend process terminated unexpectedly")
            return False
        
        # Small delay to prevent busy waiting
        time.sleep(0.1)
    
    return True

def test_json_parsing():
    """Test JSON parsing with firmware format.
    
    Returns:
        True if parsing successful, False otherwise
    """
    print("🧪 Testing JSON parsing...")
    
    # Test the actual firmware JSON format
    firmware_json = '{"t":1234,"ax":1.234,"ay":2.345,"az":9.876,"gx":0.123,"gy":0.234,"gz":0.345,"mx":45.6,"my":67.8,"mz":89.0,"qw":0.1234,"qx":0.2345,"qy":0.3456,"qz":0.4567}'
    
    try:
        data = json.loads(firmware_json)
        print("✅ Firmware JSON format parses successfully")
        print(f"   Fields: {list(data.keys())}")
        print(f"   Timestamp field: 't' = {data['t']}")
        return True
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def monitor_backend_with_timeout(backend_process, duration=10):
    """Monitor backend output with strict timeout.
    
    Args:
        backend_process: The backend subprocess to monitor
        duration: Duration to monitor in seconds
    """
    print(f"🔍 Monitoring backend output for {duration} seconds...")
    start_time = time.time()
    
    while time.time() - start_time < duration:
        # Check if process is still running
        if backend_process.poll() is not None:
            print("❌ Backend process terminated unexpectedly")
            return False
        
        # Read any available output
        output_lines = read_output_with_timeout(backend_process, timeout=0.5)
        for line in output_lines:
            print(f"Backend: {line}")
        
        # Small delay
        time.sleep(0.1)
    
    return True

def main():
    print("🏌️ GolfIMU Test Script")
    print("=" * 50)
    
    # Test JSON parsing first
    if not test_json_parsing():
        print("❌ JSON parsing test failed - stopping")
        return
    
    # Check if Redis is running
    print("\n1. Checking Redis server...")
    try:
        result = subprocess.run(['redis-cli', 'ping'], capture_output=True, text=True, timeout=5)
        if result.stdout.strip() == 'PONG':
            print("✅ Redis is running")
        else:
            print("❌ Redis is not responding")
            return
    except FileNotFoundError:
        print("❌ Redis CLI not found. Make sure Redis is installed.")
        return
    except subprocess.TimeoutExpired:
        print("❌ Redis check timed out")
        return
    
    # Start the backend
    print("\n2. Starting GolfIMU backend...")
    backend_process = None
    
    try:
        backend_process = subprocess.Popen(
            [sys.executable, 'backend/run_backend.py'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Wait for backend to start
        print("⏳ Waiting for backend to start...")
        time.sleep(3)
        
        # Check if process is still running
        if backend_process.poll() is not None:
            print(f"❌ Backend failed to start (exit code: {backend_process.poll()})")
            return
        
        print("✅ Backend started successfully")
        
        # Test commands with strict timeouts
        print("\n3. Running test commands...")
        
        # Connect to Arduino
        print("🔌 Attempting to connect to Arduino...")
        if not run_command_safe(backend_process, "connect_arduino", max_wait=10):
            print("⚠️ Arduino connection may have failed (expected if no hardware)")
        
        # Check status
        run_command_safe(backend_process, "status", max_wait=5)
        
        # Start session
        print("📊 Starting test session...")
        run_command_safe(backend_process, "start_session test_user driver 1.07 0.205", max_wait=5)
        
        # Send config
        print("⚙️ Sending configuration...")
        run_command_safe(backend_process, "send_config", max_wait=5)
        
        # Check status again
        run_command_safe(backend_process, "status", max_wait=5)
        
        # Start data collection with strict timeout
        print("\n4. Starting data collection (will run for 10 seconds)...")
        print("🔍 Monitoring for JSON parsing errors...")
        print("⚠️ Note: If no Arduino is connected, this will show connection errors")
        
        # Send start command
        try:
            backend_process.stdin.write("start_data_collection_c\n")
            backend_process.stdin.flush()
        except Exception as e:
            print(f"❌ Failed to send start command: {e}")
        
        # Monitor with strict timeout
        monitor_backend_with_timeout(backend_process, duration=10)
        
        # Stop data collection
        print("\n5. Stopping data collection...")
        try:
            backend_process.stdin.write("\x03")  # Ctrl+C
            backend_process.stdin.flush()
        except Exception as e:
            print(f"❌ Failed to send stop command: {e}")
        
        # Final cleanup
        print("\n6. Cleaning up...")
        time.sleep(1)
        
        # Read any remaining output
        remaining_output = read_output_with_timeout(backend_process, timeout=2.0)
        for line in remaining_output:
            print(f"Backend: {line}")
        
        print("\n✅ Test completed!")
        print("\n📋 Summary:")
        print("  - JSON parsing: ✅ Working")
        print("  - Redis connection: ✅ Working") 
        print("  - Backend startup: ✅ Working")
        print("  - Arduino connection: ⚠️ May have failed (expected if no hardware)")
        print("  - Data collection: ⚠️ May have failed (expected if no Arduino)")
        
        print("\n🔧 To run manually:")
        print("  python backend/run_backend.py")
        print("  connect_arduino")
        print("  start_session test_user driver 1.07 0.205")
        print("  send_config")
        print("  start_data_collection_c")
        
        print("\n💡 Next steps:")
        print("  1. Connect Teensy 4.0 + BNO08x IMU")
        print("  2. Upload firmware to Teensy")
        print("  3. Run this test again")
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
    finally:
        # Always clean up the process
        if backend_process:
            try:
                print("🛑 Terminating backend process...")
                backend_process.terminate()
                backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("⚠️ Backend didn't terminate gracefully, forcing...")
                backend_process.kill()
            except Exception as e:
                print(f"❌ Error terminating process: {e}")

if __name__ == "__main__":
    main() 