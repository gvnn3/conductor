"""Edge case tests for Step class discovered by property-based testing."""

import pytest
from conductor.step import Step


class TestStepEdgeCases:
    """Test edge cases in Step command parsing."""

    def test_step_handles_unclosed_single_quote(self):
        """Test that Step handles unclosed single quotes gracefully."""
        step = Step("echo 'hello")
        # Should fall back to simple split
        assert step.args == ["echo", "'hello"]
        assert step.spawn is False
        assert step.timeout == 30

    def test_step_handles_unclosed_double_quote(self):
        """Test that Step handles unclosed double quotes gracefully."""
        step = Step('echo "hello world')
        # Should fall back to simple split
        assert step.args == ["echo", '"hello', "world"]

    def test_step_handles_only_quote(self):
        """Test that Step handles a single quote character."""
        step = Step("'")
        assert step.args == ["'"]

    def test_step_handles_mixed_quotes(self):
        """Test that Step handles mixed quote situations."""
        step = Step("echo 'hello\" world")
        # Should fall back to simple split
        assert step.args == ["echo", "'hello\"", "world"]

    def test_step_handles_empty_string(self):
        """Test that Step handles empty string."""
        step = Step("")
        assert step.args == []  # shlex.split of empty string gives []

    def test_step_handles_whitespace_only(self):
        """Test that Step handles whitespace-only strings."""
        step = Step("   ")
        assert step.args == []  # Split removes empty parts

    def test_step_handles_control_characters(self):
        """Test that Step handles strings with control characters."""
        # Form feed character
        step = Step("echo\x0chello")
        # shlex should handle this fine
        assert len(step.args) >= 1
        assert "echo" in step.args[0]

    def test_step_handles_valid_quoted_strings(self):
        """Test that properly quoted strings still work correctly."""
        step = Step('echo "hello world"')
        assert step.args == ["echo", "hello world"]

    def test_step_handles_escaped_quotes(self):
        """Test that escaped quotes work correctly."""
        step = Step("echo \\'hello\\'")
        assert len(step.args) >= 2
        assert step.args[0] == "echo"