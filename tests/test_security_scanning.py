"""Test for automated security scanning."""

import pytest
import subprocess
import os
import json
from pathlib import Path


class TestSecurityScanning:
    """Test automated security scanning implementation."""
    
    def test_security_scanner_exists(self):
        """Test that security scanner script exists."""
        scanner_path = Path(__file__).parent.parent / "security_scan.py"
        assert scanner_path.exists(), "security_scan.py should exist"
    
    def test_can_run_security_scan(self):
        """Test that we can run a basic security scan."""
        result = subprocess.run(
            ["python", "security_scan.py", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        assert result.returncode == 0, "Security scanner should run without errors"
        assert "usage:" in result.stdout.lower(), "Should show help message"
    
    def test_scan_detects_hardcoded_passwords(self):
        """Test that scanner detects hardcoded passwords."""
        # Create a test file with hardcoded password
        test_file = Path(__file__).parent / "test_insecure.py"
        test_file.write_text('password = "hardcoded123"\n')
        
        try:
            result = subprocess.run(
                ["python", "security_scan.py", str(test_file)],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )
            
            assert result.returncode != 0, "Should fail when hardcoded password found"
            assert "hardcoded password" in result.stdout.lower(), "Should report password issue"
        finally:
            test_file.unlink()
    
    def test_scan_detects_pickle_usage(self):
        """Test that scanner detects pickle usage (security risk)."""
        test_file = Path(__file__).parent / "test_pickle.py"
        test_file.write_text('import pickle\ndata = pickle.loads(input_data)\n')
        
        try:
            result = subprocess.run(
                ["python", "security_scan.py", str(test_file)],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )
            
            assert result.returncode != 0, "Should fail when pickle usage found"
            assert "pickle" in result.stdout.lower(), "Should report pickle security risk"
        finally:
            test_file.unlink()
    
    def test_scan_allows_conductor_shell_usage(self):
        """Test that scanner allows shell=True for conductor's legitimate use case."""
        # Conductor NEEDS shell=True to execute arbitrary commands - this is NOT a vulnerability
        test_file = Path(__file__).parent / "test_conductor_shell.py"
        test_file.write_text(
            'import subprocess\n'
            '# Conductor executes user-provided commands\n' 
            'cmd = step.command  # User command from config\n'
            'subprocess.run(cmd, shell=True)  # Required for full shell features\n'
        )
        
        try:
            result = subprocess.run(
                ["python", "security_scan.py", str(test_file)],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )
            
            # This should PASS - shell=True is required for conductor
            assert result.returncode == 0, "Conductor's use of shell=True should be allowed"
        finally:
            test_file.unlink()
    
    def test_scan_clean_code_passes(self):
        """Test that clean code passes security scan."""
        test_file = Path(__file__).parent / "test_clean.py"
        test_file.write_text(
            'def add(a, b):\n'
            '    """Add two numbers."""\n'
            '    return a + b\n'
        )
        
        try:
            result = subprocess.run(
                ["python", "security_scan.py", str(test_file)],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )
            
            assert result.returncode == 0, "Clean code should pass"
            assert "no security issues found" in result.stdout.lower()
        finally:
            test_file.unlink()
    
    def test_scan_whole_project(self):
        """Test scanning the whole conductor project."""
        result = subprocess.run(
            ["python", "security_scan.py", "conductor/"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        # Project should be clean (we removed pickle usage)
        assert result.returncode == 0, f"Project scan failed: {result.stdout}"
    
    def test_scan_output_format(self):
        """Test that scan output is in expected format."""
        test_file = Path(__file__).parent / "test_format.py"
        test_file.write_text('password = "test123"\n')
        
        try:
            result = subprocess.run(
                ["python", "security_scan.py", str(test_file), "--json"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )
            
            # Should be valid JSON
            output = json.loads(result.stdout)
            assert "issues" in output
            assert isinstance(output["issues"], list)
            assert len(output["issues"]) > 0
            
            issue = output["issues"][0]
            assert "file" in issue
            assert "line" in issue
            assert "issue" in issue
            assert "severity" in issue
        finally:
            test_file.unlink()
    
    def test_scan_ignore_patterns(self):
        """Test that scanner respects ignore patterns."""
        test_file = Path(__file__).parent / "test_ignored.py"
        test_file.write_text(
            '# security: ignore\n'
            'password = "hardcoded123"\n'
        )
        
        try:
            result = subprocess.run(
                ["python", "security_scan.py", str(test_file)],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )
            
            assert result.returncode == 0, "Should pass when issue is ignored"
        finally:
            test_file.unlink()