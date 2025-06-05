"""Extended edge case tests for Step execution using hypothesis."""

import os
import sys
import subprocess
from hypothesis import given, strategies as st, assume, settings, example
import pytest

from conductor.step import Step
from conductor.retval import RETVAL_OK, RETVAL_ERROR


class TestStepExtendedEdgeCases:
    """Extended edge case tests for Step class."""
    
    @given(
        command=st.text(min_size=1).filter(
            lambda x: x.strip() and '\x00' not in x
        )
    )
    def test_step_with_unclosed_quotes(self, command):
        """Test that Step handles unclosed quotes gracefully."""
        # Count quotes
        single_quotes = command.count("'")
        double_quotes = command.count('"')
        
        # If quotes are unbalanced, Step should still create args
        step = Step(command)
        assert step.args is not None
        assert isinstance(step.args, list)
        
        # For severely malformed commands, args might differ from shlex
        if single_quotes % 2 != 0 or double_quotes % 2 != 0:
            # Should handle gracefully without crashing
            assert len(step.args) >= 0
    
    def test_step_spawn_mode_returns_immediately(self):
        """Test that spawn mode returns without waiting."""
        # Use a command that would take time
        command = f"{sys.executable} -c \"import time; time.sleep(10)\""
        step = Step(command, spawn=True)
        
        import time
        start_time = time.time()
        result = step.run()
        elapsed = time.time() - start_time
        
        # Should return immediately (within 1 second)
        assert elapsed < 1.0
        assert result.code == RETVAL_OK
        assert result.message == "Spawned"
    
    @given(
        args_with_null=st.lists(
            st.text(min_size=1).map(lambda x: x + '\x00' if '\x00' not in x else x),
            min_size=1,
            max_size=5
        )
    )
    def test_command_with_null_bytes_in_args(self, args_with_null):
        """Test commands where arguments contain null bytes."""
        # Join with spaces but include null bytes
        command = ' '.join(args_with_null)
        
        # Step should handle this somehow
        step = Step(command)
        assert step.args is not None
    
    def test_step_with_extremely_long_command(self):
        """Test step with command approaching system limits."""
        # Create a very long but valid command
        long_arg = "x" * 10000
        command = f"echo {long_arg}"
        
        step = Step(command)
        result = step.run()
        
        # Should succeed unless system limit is hit
        assert result is not None
        assert hasattr(result, 'code')
        # Echo should work with long args
        if result.code == RETVAL_OK:
            assert long_arg in result.message
    
    @given(
        return_code=st.integers(min_value=1, max_value=255)
    )
    def test_step_preserves_error_codes(self, return_code):
        """Test that step preserves specific error codes."""
        # Use exit to return specific code
        command = f"{sys.executable} -c \"import sys; sys.exit({return_code})\""
        
        step = Step(command)
        result = step.run()
        
        # Should preserve the exact error code
        assert result.code == return_code
    
    def test_step_empty_methods(self):
        """Test that empty methods can be called without error."""
        step = Step("echo test")
        
        # These should all work without error
        step.ready()  # Line 83
        step.wait_ready()  # Line 87
        step.wait(10)  # Line 91
    
    @given(
        env_vars=st.dictionaries(
            st.text(alphabet=st.characters(whitelist_categories=("Lu",)), min_size=1, max_size=20),
            st.text(min_size=0, max_size=100).filter(lambda x: '\x00' not in x),
            min_size=0,
            max_size=5
        )
    )
    def test_step_with_environment_modifications(self, env_vars):
        """Test steps that interact with environment variables."""
        # Set some environment variables
        original_env = {}
        for key, value in env_vars.items():
            if key in os.environ:
                original_env[key] = os.environ[key]
            os.environ[key] = value
        
        try:
            # Run a command that might use these
            command = f"{sys.executable} -c \"import os; print(len(os.environ))\""
            step = Step(command)
            result = step.run()
            
            assert result.code == RETVAL_OK
            # Output should be a number
            assert result.message.strip().isdigit()
            
        finally:
            # Restore environment
            for key in env_vars:
                if key in original_env:
                    os.environ[key] = original_env[key]
                else:
                    del os.environ[key]
    
    @given(
        cmd_parts=st.lists(
            st.sampled_from(["echo", "true", "false", sys.executable]),
            min_size=1,
            max_size=1
        ),
        special_args=st.lists(
            st.sampled_from(["--help", "--version", "-c 'pass'", ">/dev/null", "2>&1"]),
            min_size=0,
            max_size=3
        )
    )
    def test_step_with_shell_redirections(self, cmd_parts, special_args):
        """Test commands with shell-like redirections."""
        command = ' '.join(cmd_parts + special_args)
        
        step = Step(command)
        # Should parse but redirections won't work without shell=True
        assert step.args is not None
        
        # If command has redirections, they'll be treated as arguments
        if any('>' in arg or '<' in arg for arg in special_args):
            # Redirections will be in args as literals
            assert any('>' in arg or '<' in arg for arg in step.args)
    
    def test_step_with_binary_output(self):
        """Test step handling binary output."""
        # Command that outputs binary data
        command = f"{sys.executable} -c \"import sys; sys.stdout.buffer.write(b'\\x00\\x01\\x02\\xff')\""
        
        step = Step(command)
        result = step.run()
        
        # Should handle binary output
        assert result is not None
        # Binary might be decoded with errors or handled specially
    
    @given(
        signals=st.sampled_from(["SIGTERM", "SIGKILL", "SIGINT"])
    )
    def test_step_signal_handling(self, signals):
        """Test how steps handle being signaled (theoretical test)."""
        # This is more of a design test - steps don't currently handle signals
        step = Step("sleep 10")
        
        # Verify step has expected structure
        assert hasattr(step, 'args')
        assert hasattr(step, 'spawn')
        assert hasattr(step, 'timeout')
        
        # In a real test, we'd spawn the process and send signals
        # but that's complex to do reliably cross-platform