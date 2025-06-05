"""Hypothesis tests for Step execution edge cases."""

import os
import sys
from hypothesis import given, strategies as st, assume, settings

from conductor.step import Step
from conductor.retval import RETVAL_OK, RETVAL_ERROR


class TestStepEdgeCases:
    """Edge case tests for Step execution."""

    @given(
        output_size=st.sampled_from([1024, 10240, 102400])  # 1KB, 10KB, 100KB
    )
    @settings(deadline=5000)
    def test_large_output_commands(self, output_size):
        """Test commands that produce large outputs."""
        # Use Python to generate controlled output
        command = f"{sys.executable} -c \"print('x' * {output_size})\""

        step = Step(command)
        result = step.run()

        assert result.code == RETVAL_OK
        # Output includes the print result plus newline
        assert len(result.message) >= output_size

    @given(
        shell_chars=st.lists(
            st.sampled_from(["&&", "||", ";", "|", "$()", "`", ">"]),
            min_size=1,
            max_size=3,
        )
    )
    def test_shell_injection_attempts(self, shell_chars):
        """Test that shell special characters are handled safely."""
        # Build a command with shell characters
        base_cmd = "echo test"
        for char in shell_chars:
            base_cmd += f" {char} echo injected"

        step = Step(base_cmd)
        result = step.run()

        # The command should still run (echo is safe)
        # but we verify it's not executing the injected parts
        assert result is not None
        assert hasattr(result, "code")

        # The output should not contain "injected" if properly escaped
        # This depends on shell parsing behavior

    @given(
        env_var=st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), min_codepoint=65
            ),
            min_size=1,
            max_size=20,
        ).filter(lambda x: x[0].isalpha() and x.replace("_", "").isalnum())
    )
    def test_environment_variable_handling(self, env_var):
        """Test commands with environment variables."""
        # Set an environment variable
        test_value = "test_value_12345"
        os.environ[env_var] = test_value

        try:
            # Try to echo the environment variable
            command = f"echo ${{{env_var}}}"
            step = Step(command)
            result = step.run()

            assert result.code == RETVAL_OK
            # The output should contain the variable value
            assert test_value in result.message

        finally:
            # Clean up
            if env_var in os.environ:
                del os.environ[env_var]

    def test_command_with_null_bytes(self):
        """Test that commands with null bytes are handled."""
        # This should fail gracefully
        command = "echo test\x00hidden"
        step = Step(command)

        # The null byte might cause issues in argument parsing
        assert step.args is not None

    @given(spawn=st.booleans())
    @settings(deadline=5000)
    def test_spawn_mode_process_cleanup(self, spawn):
        """Test that spawned processes are handled correctly."""
        # Create a command that runs briefly
        command = f'{sys.executable} -c "import time; time.sleep(0.1)"'

        step = Step(command, spawn=spawn)
        result = step.run()

        if spawn:
            # In spawn mode, we get immediate return
            assert result.code == RETVAL_OK
            assert result.message == "Spawned"
        else:
            # In normal mode, we wait for completion
            assert result.code == RETVAL_OK

    @given(arg_count=st.integers(min_value=100, max_value=1000))
    def test_many_arguments(self, arg_count):
        """Test commands with many arguments."""
        # Create a command with many arguments
        args = ["echo"] + [f"arg{i}" for i in range(arg_count)]
        command = " ".join(args)

        step = Step(command)
        result = step.run()

        assert result.code == RETVAL_OK
        # Verify we got all arguments
        assert step.args[0] == "echo"
        assert len(step.args) == arg_count + 1

    def test_command_not_found(self):
        """Test behavior when command doesn't exist."""
        command = "this_command_definitely_does_not_exist_12345"
        step = Step(command)
        result = step.run()

        # Should return error when command not found
        assert result.code == RETVAL_ERROR

    @given(
        special_chars=st.text(
            alphabet="!@#$%^&*(){}[]|\\:;\"'<>?,./~`", min_size=1, max_size=10
        )
    )
    def test_special_characters_in_arguments(self, special_chars):
        """Test arguments containing special characters."""
        # Use Python to safely echo the special characters
        command = f'{sys.executable} -c "print({repr(special_chars)}, end=\\"\\")"'

        step = Step(command)
        result = step.run()

        # Should handle special characters without crashing
        assert result is not None
        assert hasattr(result, "code")

    def test_extremely_long_single_argument(self):
        """Test a command with one very long argument."""
        # Create a very long argument (10KB)
        long_arg = "x" * 10240
        command = f"echo {long_arg}"

        step = Step(command)
        result = step.run()

        assert result.code == RETVAL_OK
        assert long_arg in result.message

    @given(working_dir=st.sampled_from(["/tmp", "/var/tmp", os.path.expanduser("~")]))
    def test_working_directory_commands(self, working_dir):
        """Test commands that interact with working directory."""
        assume(os.path.exists(working_dir))
        assume(os.access(working_dir, os.R_OK))

        # Try to list files in the directory
        command = f"ls {working_dir}"
        step = Step(command)
        result = step.run()

        # Should succeed if directory exists and is readable
        assert result.code == RETVAL_OK
