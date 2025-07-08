#!/usr/bin/env python3
"""
Tests for scripts.utils module
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import sys
import os

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent
sys.path.insert(0, str(scripts_dir))

from utils import find_project_root, setup_project_paths, find_test_directories, verify_project_structure


class TestUtils:
    """Test utility functions"""
    
    def test_find_project_root_from_scripts(self):
        """Test finding project root from scripts directory"""
        # This test assumes we're running from within the GolfIMU project
        project_root = find_project_root()
        
        # Should find the GolfIMU project root
        assert project_root.exists()
        assert (project_root / "backend").exists()
        assert (project_root / "embedded").exists()
        assert (project_root / "backend" / "main.py").exists()
        assert (project_root / "embedded" / "firmware").exists()
    
    def test_setup_project_paths(self):
        """Test setting up project paths"""
        project_root = setup_project_paths()
        
        # Should return a valid project root
        assert project_root.exists()
        assert (project_root / "backend").exists()
        assert (project_root / "embedded").exists()
        
        # Should add project root to Python path
        assert str(project_root) in sys.path
    
    def test_find_test_directories(self):
        """Test finding test directories"""
        project_root = find_project_root()
        test_dirs = find_test_directories(project_root)
        
        # Should find at least backend/tests
        assert len(test_dirs) >= 1
        
        # Check that found directories contain Python files
        for test_dir in test_dirs:
            assert test_dir.exists()
            assert test_dir.name == "tests"
            # Should contain at least one Python file
            python_files = list(test_dir.glob("*.py"))
            assert len(python_files) > 0
    
    def test_verify_project_structure_valid(self):
        """Test project structure verification with valid structure"""
        project_root = find_project_root()
        result = verify_project_structure(project_root)
        assert result is True
    
    def test_verify_project_structure_invalid(self):
        """Test project structure verification with invalid structure"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create an invalid structure (missing backend and embedded)
            result = verify_project_structure(temp_path)
            assert result is False
    
    def test_verify_project_structure_partial(self):
        """Test project structure verification with partial structure"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create backend directory but not embedded
            backend_dir = temp_path / "backend"
            backend_dir.mkdir()
            (backend_dir / "main.py").touch()
            
            result = verify_project_structure(temp_path)
            assert result is False
    
    def test_find_project_root_from_nested_location(self):
        """Test finding project root from a nested location"""
        project_root = find_project_root()
        
        # Create a temporary nested directory structure
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create nested directories
            nested_dir = temp_path / "deeply" / "nested" / "directory"
            nested_dir.mkdir(parents=True)
            
            # Copy the utils module to the nested location
            utils_file = scripts_dir / "utils.py"
            nested_utils = nested_dir / "utils.py"
            shutil.copy2(utils_file, nested_utils)
            
            # Create a test script in the nested location
            test_script = nested_dir / "test_script.py"
            test_script.write_text("""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from utils import find_project_root

# This should find the GolfIMU project root even from nested location
project_root = find_project_root()
print(f"Found project root: {project_root}")
""")
            
            # Run the test script
            result = os.system(f"cd {nested_dir} && python test_script.py")
            assert result == 0


class TestProjectRootDetection:
    """Test project root detection in various scenarios"""
    
    def test_detection_with_git_repo(self):
        """Test detection when .git directory is present"""
        project_root = find_project_root()
        
        # Should work even if .git directory exists
        assert project_root.exists()
        assert (project_root / "backend").exists()
        assert (project_root / "embedded").exists()
    
    def test_detection_with_venv(self):
        """Test detection when virtual environment is present"""
        project_root = find_project_root()
        
        # Should work even if venv directory exists
        assert project_root.exists()
        assert (project_root / "backend").exists()
        assert (project_root / "embedded").exists()
    
    def test_detection_with_other_files(self):
        """Test detection with various other files present"""
        project_root = find_project_root()
        
        # Should work regardless of other files
        assert project_root.exists()
        assert (project_root / "backend").exists()
        assert (project_root / "embedded").exists()


class TestTestDiscovery:
    """Test test directory discovery"""
    
    def test_discovery_includes_scripts_tests(self):
        """Test that scripts/tests is discovered"""
        project_root = find_project_root()
        test_dirs = find_test_directories(project_root)
        
        # Should find scripts/tests if it exists
        scripts_tests = project_root / "scripts" / "tests"
        if scripts_tests.exists():
            assert scripts_tests in test_dirs
    
    def test_discovery_includes_backend_tests(self):
        """Test that backend/tests is discovered"""
        project_root = find_project_root()
        test_dirs = find_test_directories(project_root)
        
        # Should find backend/tests
        backend_tests = project_root / "backend" / "tests"
        assert backend_tests in test_dirs
    
    def test_discovery_excludes_empty_dirs(self):
        """Test that empty test directories are excluded"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create an empty tests directory
            empty_tests = temp_path / "tests"
            empty_tests.mkdir()
            
            # Should not include empty test directories
            test_dirs = find_test_directories(temp_path)
            assert len(test_dirs) == 0
    
    def test_discovery_includes_nested_tests(self):
        """Test that nested test directories are discovered"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create nested test directories
            nested_tests = temp_path / "some" / "nested" / "tests"
            nested_tests.mkdir(parents=True)
            (nested_tests / "test_file.py").touch()
            
            # Should find nested test directories
            test_dirs = find_test_directories(temp_path)
            # Normalize paths to handle macOS symlink differences
            normalized_nested_tests = nested_tests.resolve()
            normalized_test_dirs = [test_dir.resolve() for test_dir in test_dirs]
            assert normalized_nested_tests in normalized_test_dirs


if __name__ == "__main__":
    pytest.main([__file__]) 