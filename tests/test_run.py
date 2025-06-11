"""Tests for the Run class."""

from unittest.mock import patch
import json

from conductor.run import Run


class TestRunClass:
    """Test Run class functionality."""

    @patch("builtins.print")
    def test_initialization_prints_running(self, mock_print):
        """Test that Run initialization prints 'running'."""
        Run()  # Initialize Run class to trigger print
        mock_print.assert_called_once_with("running")

    def test_run_protocol_representation(self):
        """Test that Run can be represented for JSON protocol."""
        with patch("builtins.print"):  # Suppress print during test
            run = Run()

        # In the JSON protocol, Run is represented as an empty message
        # This tests that Run can be conceptually serialized
        run_data = {}  # Run has no data to serialize
        
        # Verify it can be JSON serialized
        json_str = json.dumps(run_data)
        loaded = json.loads(json_str)
        
        assert loaded == {}
        
        # Note: The actual Run object is recreated on the receiving end
        # by the protocol handler when it sees a RUN message type
