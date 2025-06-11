"""Tests for the Step class."""

from unittest.mock import patch, MagicMock
import subprocess

from conductor.step import Step
from conductor.retval import RetVal


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


class TestStepExecution:
    """Test command execution functionality of Step class."""

    @patch("subprocess.check_output")
    def test_executes_simple_command_successfully(self, mock_check_output):
        """Test successful execution of a simple command."""
        mock_check_output.return_value = "hello world\n"

        step = Step("echo hello world")
        result = step.run()

        assert isinstance(result, RetVal)
        assert result.code == 0
        assert result.message == "hello world\n"
        mock_check_output.assert_called_once_with(
            "echo hello world",
            shell=True,
            timeout=30,
            universal_newlines=True,
            errors="replace",
        )

    @patch("subprocess.Popen")
    def test_spawns_command_without_waiting(self, mock_popen):
        """Test that spawn commands don't wait for completion."""
        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        step = Step("iperf -s", spawn=True)
        result = step.run()

        assert isinstance(result, RetVal)
        assert result.code == 0
        assert result.message == "Spawned"
        mock_popen.assert_called_once_with("iperf -s", shell=True)
        # Should not call wait() or communicate() on the process
        mock_process.wait.assert_not_called()
        mock_process.communicate.assert_not_called()

    @patch("subprocess.check_output")
    def test_handles_command_failure(self, mock_check_output):
        """Test handling of command that returns non-zero exit code."""
        mock_check_output.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd="false", output="error output"
        )

        step = Step("false")
        result = step.run()

        assert isinstance(result, RetVal)
        assert result.code == 1
        assert result.message == "false"

    @patch("subprocess.check_output")
    def test_handles_command_timeout(self, mock_check_output):
        """Test handling of command timeout."""
        mock_check_output.side_effect = subprocess.TimeoutExpired(
            cmd=["sleep", "100"], timeout=1
        )

        step = Step("sleep 100", timeout=1)
        result = step.run()

        assert isinstance(result, RetVal)
        assert result.code == 1  # RETVAL_ERROR
        assert result.message == f"Command timed out after {step.timeout} seconds"
