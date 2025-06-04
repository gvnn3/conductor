"""Test the modern build system configuration."""

import subprocess
import sys
import tempfile
import os
from pathlib import Path


class TestBuildSystem:
    """Test that the package can be built with modern tools."""
    
    def test_pyproject_toml_exists(self):
        """Test that pyproject.toml exists."""
        project_root = Path(__file__).parent.parent
        pyproject_path = project_root / "pyproject.toml"
        assert pyproject_path.exists(), "pyproject.toml should exist"
    
    def test_build_with_pip(self):
        """Test that package can be built with pip."""
        # Create a temporary directory for the build
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(__file__).parent.parent
            
            # Try to build a wheel
            result = subprocess.run(
                [sys.executable, "-m", "pip", "wheel", "--wheel-dir", tmpdir, 
                 "--no-deps", str(project_root)],
                capture_output=True,
                text=True
            )
            
            # Check if build succeeded
            assert result.returncode == 0, f"Build failed: {result.stderr}"
            
            # Check if wheel was created
            wheels = list(Path(tmpdir).glob("conductor-*.whl"))
            assert len(wheels) == 1, f"Expected 1 wheel, found {len(wheels)}"
    
    def test_package_metadata(self):
        """Test that package metadata is correctly defined."""
        project_root = Path(__file__).parent.parent
        
        # Use python -m build to check metadata
        result = subprocess.run(
            [sys.executable, "-c", 
             "import tomllib; "
             f"with open('{project_root}/pyproject.toml', 'rb') as f: "
             "    data = tomllib.load(f); "
             "    print(data['project']['name']); "
             "    print(data['project']['version'])"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            # Python < 3.11 doesn't have tomllib, try with toml
            result = subprocess.run(
                [sys.executable, "-c", 
                 "import toml; "
                 f"data = toml.load('{project_root}/pyproject.toml'); "
                 "print(data['project']['name']); "
                 "print(data['project']['version'])"],
                capture_output=True,
                text=True
            )
        
        if result.returncode == 0:
            output_lines = result.stdout.strip().split('\n')
            assert output_lines[0] == "conductor"
            assert output_lines[1] == "0.0.1"
        else:
            # If no toml library available, just check the file contains expected content
            with open(project_root / "pyproject.toml", 'r') as f:
                content = f.read()
                assert 'name = "conductor"' in content
                assert 'version = "0.0.1"' in content