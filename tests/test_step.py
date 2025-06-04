"""Tests for the Step class."""

import pytest
from conductor.step import Step


class TestStepParsing:
    """Test command parsing functionality of Step class."""
    
    def test_parses_simple_command(self):
        """Test that a simple command is parsed correctly."""
        step = Step("echo hello")
        assert step.args == ["echo", "hello"]
        assert step.spawn is False
        assert step.timeout == 30  # default timeout
    
    def test_parses_command_with_spawn_parameter(self):
        """Test that spawn parameter is set correctly."""
        step = Step("iperf -s", spawn=True)
        assert step.args == ["iperf", "-s"]
        assert step.spawn is True
        assert step.timeout == 30  # default timeout
    
    def test_parses_command_with_timeout_parameter(self):
        """Test that timeout parameter is set correctly."""
        step = Step("wget http://example.com/large_file", timeout=60)
        assert step.args == ["wget", "http://example.com/large_file"]
        assert step.spawn is False
        assert step.timeout == 60
    
    def test_parses_quoted_command(self):
        """Test that quoted arguments are parsed correctly."""
        step = Step('echo "hello world"')
        assert step.args == ["echo", "hello world"]
        assert step.spawn is False
        assert step.timeout == 30