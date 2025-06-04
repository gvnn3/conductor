"""Hypothesis-based property tests for Step execution."""

import os
import tempfile
from hypothesis import given, strategies as st, assume, settings
import pytest

from conductor.step import Step
from conductor.retval import RETVAL_OK, RETVAL_ERROR


class TestStepProperties:
    """Property-based tests for Step class."""
    
    @given(
        command=st.text(min_size=1).filter(
            lambda x: x.strip() and not any(c in x for c in ['\0', '\n', '\r'])
        )
    )
    def test_step_creation_preserves_command(self, command):
        """Test that Step creation preserves the command."""
        step = Step(command)
        
        # The args should be the parsed command
        assert step.args is not None
        
        # For simple commands without quotes, args should not be empty
        if command.strip():
            assert len(step.args) > 0
        
        # For commands without special shell characters, we can verify preservation
        if not any(c in command for c in ['\\', '"', "'", '|', '&', ';', '<', '>', '$']):
            rejoined = ' '.join(step.args)
            # Allow for whitespace normalization
            assert command.split() == rejoined.split()
    
    @given(
        command=st.text(min_size=1).filter(lambda x: x.strip()),
        spawn=st.booleans(),
        timeout=st.integers(min_value=1, max_value=300)
    )
    def test_step_attributes(self, command, spawn, timeout):
        """Test that Step correctly stores all attributes."""
        step = Step(command, spawn=spawn, timeout=timeout)
        
        assert step.spawn == spawn
        assert step.timeout == timeout
        assert isinstance(step.args, list)
    
    @given(
        executable=st.sampled_from(["echo", "true", "false"]),
        args=st.lists(
            st.text(min_size=1, max_size=20).filter(lambda x: '\0' not in x and '\n' not in x),
            max_size=5
        )
    )
    def test_step_execution_with_safe_commands(self, executable, args):
        """Test step execution with safe system commands."""
        # Build command
        command_parts = [executable] + args
        command = ' '.join(command_parts)
        
        step = Step(command)
        result = step.run()
        
        # These commands should always complete
        assert result is not None
        assert hasattr(result, 'code')
        
        if executable == "true":
            assert result.code == RETVAL_OK
        elif executable == "false":
            assert result.code == RETVAL_ERROR
        elif executable == "echo":
            assert result.code == RETVAL_OK
    
    @given(
        text_content=st.text(min_size=1, max_size=20).filter(
            lambda x: '\n' not in x and '\0' not in x and '%' not in x
        )
    )
    def test_step_handles_quotes(self, text_content):
        """Test that steps handle quoted arguments correctly."""
        # Skip if text has both quote types (shell parsing gets complex)
        assume(not ("'" in text_content and '"' in text_content))
        
        # Build a safe command with quotes using echo (safer than printf)
        if "'" in text_content:
            # Use double quotes
            command = f'echo "{text_content}"'
        else:
            # Use single quotes
            command = f"echo '{text_content}'"
        
        step = Step(command)
        
        # Should parse into base command and argument
        assert len(step.args) >= 1
        assert step.args[0] == "echo"
        
        # Echo should always succeed
        result = step.run()
        assert result.code == RETVAL_OK
    
    @given(timeout=st.integers(min_value=1, max_value=5))
    @settings(deadline=10000)  # 10 second deadline
    def test_step_timeout_enforcement(self, timeout):
        """Test that step timeout is enforced."""
        # Create a command that sleeps longer than timeout
        sleep_time = timeout + 2
        command = f"sleep {sleep_time}"
        
        step = Step(command, timeout=timeout)
        result = step.run()
        
        # Should timeout and return error
        assert result.code == RETVAL_ERROR
        assert "timed out" in result.message.lower() or "timeout" in result.message.lower()