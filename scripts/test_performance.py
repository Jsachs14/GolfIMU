#!/usr/bin/env python3
"""
Performance test script for GolfIMU system
Tests the optimized data collection for consistent 200 Hz performance
"""

import sys
import os
import time
from datetime import datetime

# Add backend to path and set up for relative imports
backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_path)
sys.path.insert(0, os.path.dirname(__file__))

# Set up for relative imports
os.chdir(backend_path)

try:
    from main import GolfIMUBackend
except ImportError as e:
    print(f"Import error: {e}")
    print("Trying alternative import method...")
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from backend.main import GolfIMUBackend


def test_data_collection_c():
    """Test C-based high-performance data collection"""
    print("=== Testing C-Based High-Performance Data Collection ===")
    
    backend = GolfIMUBackend()
    
    # Start session
    backend.start_session("test_user", "test_club", 1.07, 0.205)
    
    # Connect to Arduino
    if not backend.connect_arduino():
        print("Failed to connect to Arduino")
        return
    
    print("Starting C-based high-performance data collection...")
    start_time = time.time()
    
    try:
        backend.start_data_collection_c()
    except KeyboardInterrupt:
        print("\nData collection stopped by user")
    
    end_time = time.time()
    duration = end_time - start_time
    print(f"Data collection completed in {duration:.2f} seconds")





def main():
    """Main test function"""
    print("GolfIMU Performance Test")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        
        if test_type == "data_collection_c":
            test_data_collection_c()
        else:
            print("Unknown test type. Use: data_collection_c")
    else:
        print("Running C-based high-performance data collection test...")
        print("Press Ctrl+C to stop the test")
        
        try:
            test_data_collection_c()
        except KeyboardInterrupt:
            print("Test completed")


if __name__ == "__main__":
    main() 