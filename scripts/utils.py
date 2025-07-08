#!/usr/bin/env python3
"""
Common utilities for GolfIMU scripts
"""

import sys
from pathlib import Path
from typing import List
import os


def find_project_root() -> Path:
    """Find the GolfIMU project root by looking for backend and embedded directories"""
    current_path = Path(__file__).resolve()
    
    # Walk up the directory tree looking for GolfIMU project structure
    for parent in [current_path] + list(current_path.parents):
        backend_dir = parent / "backend"
        embedded_dir = parent / "embedded"
        
        # Check if this looks like the GolfIMU project root
        if backend_dir.exists() and embedded_dir.exists():
            # Additional check: look for key files
            if (backend_dir / "main.py").exists() and (embedded_dir / "firmware").exists():
                return parent
    
    # If not found, fall back to the old method
    return current_path.parent.parent


def setup_project_paths():
    """Setup project paths and add to Python path"""
    project_root = find_project_root()
    sys.path.insert(0, str(project_root))
    return project_root


def find_test_directories(project_root: Path) -> List[Path]:
    """Find all test directories in the project"""
    test_dirs = []
    
    # Directories to exclude from test discovery
    exclude_dirs = {
        'venv', 'env', '.venv', '.env',  # Virtual environments
        '__pycache__', '.pytest_cache',  # Python cache
        '.git', '.hg', '.svn',  # Version control
        'node_modules',  # Node.js
        'build', 'dist',  # Build artifacts
        '.tox', '.coverage', 'htmlcov'  # Testing artifacts
    }
    
    # Convert project_root to absolute path for comparison
    project_root = project_root.resolve()
    
    # Search for directories named 'tests' in the project
    for root, dirs, files in os.walk(project_root):
        root_path = Path(root).resolve()
        
        # Skip if we're in a virtual environment or other excluded directory
        if any(exclude_dir in str(root_path) for exclude_dir in exclude_dirs):
            continue
            
        # Remove excluded directories from dirs to prevent walking into them
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        if 'tests' in dirs:
            test_path = root_path / 'tests'
            # Check if it contains Python files
            if any(f.suffix == '.py' for f in test_path.iterdir() if f.is_file()):
                test_dirs.append(test_path)
    
    return test_dirs


def verify_project_structure(project_root: Path) -> bool:
    """Verify that the project has the expected structure"""
    required_dirs = ["backend", "embedded"]
    required_files = [
        "backend/main.py",
        "embedded/firmware/GolfIMU_Firmware/GolfIMU_Firmware.ino"
    ]
    
    for dir_name in required_dirs:
        if not (project_root / dir_name).exists():
            print(f"❌ Required directory not found: {dir_name}")
            return False
    
    for file_path in required_files:
        if not (project_root / file_path).exists():
            print(f"❌ Required file not found: {file_path}")
            return False
    
    return True 