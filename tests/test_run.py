"""Tests for the Run class."""

from unittest.mock import patch
import pickle

from conductor.run import Run


class TestRunClass:
    """Test Run class functionality."""

    @patch("builtins.print")
    def test_initialization_prints_running(self, mock_print):
        """Test that Run initialization prints 'running'."""
        Run()  # Initialize Run class to trigger print
        mock_print.assert_called_once_with("running")

    def test_can_be_pickled(self):
        """Test that Run can be pickled for network transmission."""
        with patch("builtins.print"):  # Suppress print during test
            original = Run()

        # Pickle it
        pickled = pickle.dumps(original)

        # Unpickle it (this will print "running" again)
        with patch("builtins.print") as mock_print:
            unpickled = pickle.loads(pickled)
            # Note: unpickling doesn't call __init__, so no print
            mock_print.assert_not_called()

        # Verify it's a Run instance
        assert isinstance(unpickled, Run)
