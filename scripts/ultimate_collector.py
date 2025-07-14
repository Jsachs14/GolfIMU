#!/usr/bin/env python3
"""
Ultimate data collector - uses C program for maximum speed collection
"""

import subprocess
import time
import json
import os
from datetime import datetime

def collect_data_with_c(port, duration=30):
    """Collect data using the C program for maximum speed."""
    print(f"Starting C-based data collection for {duration} seconds...")
    
    # Start the C program
    cmd = ["./fast_serial_reader", port, "temp_data.txt"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    start_time = time.time()
    data_count = 0
    
    try:
        # Monitor the process for the specified duration
        while time.time() - start_time < duration:
            time.sleep(1)
            
            # Check if process is still running
            if process.poll() is not None:
                print("C program stopped unexpectedly")
                break
                
            # Count current data points
            try:
                with open("temp_data.txt", "r") as f:
                    lines = f.readlines()
                    current_count = sum(1 for line in lines if line.strip().startswith('{'))
                    
                if current_count > data_count:
                    elapsed = time.time() - start_time
                    rate = current_count / elapsed if elapsed > 0 else 0
                    print(f"Collected {current_count} data points ({rate:.1f} Hz)")
                    data_count = current_count
                    
            except FileNotFoundError:
                pass
                
    except KeyboardInterrupt:
        print("\nStopping data collection...")
    
    # Stop the C program
    process.terminate()
    process.wait()
    
    # Final count
    try:
        with open("temp_data.txt", "r") as f:
            lines = f.readlines()
            final_count = sum(1 for line in lines if line.strip().startswith('{'))
    except FileNotFoundError:
        final_count = 0
    
    total_duration = time.time() - start_time
    final_rate = final_count / total_duration if total_duration > 0 else 0
    
    print(f"\nData collection completed!")
    print(f"Total: {final_count} data points in {total_duration:.1f}s ({final_rate:.1f} Hz)")
    
    return final_count, final_rate

def process_collected_data():
    """Process the collected data and store in database."""
    print("\nProcessing collected data...")
    
    try:
        with open("temp_data.txt", "r") as f:
            lines = f.readlines()
        
        # Filter JSON lines
        json_lines = [line.strip() for line in lines if line.strip().startswith('{')]
        
        print(f"Processing {len(json_lines)} JSON data points...")
        
        # Process each line
        processed_count = 0
        for line in json_lines:
            try:
                data = json.loads(line)
                processed_count += 1
                
                # Here you would normally store in Redis/database
                # For now, just count them
                
            except json.JSONDecodeError:
                continue
        
        print(f"Successfully processed {processed_count} data points")
        
        # Clean up temp file
        os.remove("temp_data.txt")
        
    except FileNotFoundError:
        print("No data file found to process")

def main():
    """Main function."""
    print("Ultimate GolfIMU Data Collector")
    print("=" * 40)
    
    # Arduino port (you may need to adjust this)
    port = "/dev/cu.usbmodem157382101"
    
    # Check if C program exists
    if not os.path.exists("./fast_serial_reader"):
        print("Error: fast_serial_reader not found. Please compile it first:")
        print("gcc -o fast_serial_reader fast_serial_reader.c")
        return
    
    # Check if port exists
    if not os.path.exists(port):
        print(f"Error: Serial port {port} not found")
        print("Please check your Arduino connection")
        return
    
    # Collect data for 30 seconds
    count, rate = collect_data_with_c(port, duration=30)
    
    # Process the data
    process_collected_data()
    
    print(f"\nFinal result: {count} data points at {rate:.1f} Hz average")

if __name__ == "__main__":
    main() 