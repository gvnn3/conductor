"""Test to achieve 100% coverage for step.py."""
import pytest
from conductor.step import Step
from conductor.retval import RETVAL_ERROR


class TestStepFullCoverage:
    """Tests to cover remaining lines in step.py."""
    
    def test_step_with_unclosed_quotes(self):
        """Test that Step handles commands with unclosed quotes (lines 49-52)."""
        # This triggers the ValueError in shlex.split
        step = Step('echo "unclosed quote')
        
        # The command should still be parsed using simple split
        assert step.command == 'echo "unclosed quote'
        assert step.args == ['echo', '"unclosed', 'quote']
        
        # It should still execute (shell will handle the quote issue)
        result = step.run()
        # Shell might return an error due to unclosed quote
        # but the exception handling should work
        assert hasattr(result, 'code')
        assert hasattr(result, 'message')
    
    def test_step_with_file_not_found_error(self):
        """Test FileNotFoundError handling (lines 88-90)."""
        # Since we use shell=True, FileNotFoundError is less likely
        # but we can test by mocking subprocess.check_output
        import subprocess
        from unittest.mock import patch
        
        step = Step("nonexistent_command_12345")
        
        # Mock check_output to raise FileNotFoundError
        with patch('subprocess.check_output') as mock_check:
            mock_check.side_effect = FileNotFoundError("Command not found")
            result = step.run()
        
        assert result.code == RETVAL_ERROR
        assert "Command not found: nonexistent_command_12345" in result.message