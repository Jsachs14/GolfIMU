#!/usr/bin/env python3
"""
Simple script to run the GolfIMU backend
"""
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import main

if __name__ == "__main__":
    main() 