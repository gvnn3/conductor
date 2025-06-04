"""Tests for the Phase class."""

from unittest.mock import MagicMock, patch, call

from conductor.phase import Phase
from conductor.step import Step
from conductor.retval import RetVal


class TestPhaseInitialization:
    """Test Phase initialization."""

    def test_initialization_with_host_and_port(self):
        """Test Phase initialization with result host and port."""
        phase = Phase("192.168.1.100", 6971)
        assert phase.resulthost == "192.168.1.100"
        assert phase.resultport == 6971
        assert phase.steps == []
        assert phase.results == []


class TestPhaseStepManagement:
    """Test Phase step management functionality."""

    def test_append_adds_step_to_list(self):
        """Test that append adds a step to the steps list."""
        phase = Phase("localhost", 6971)
        step = Step("echo hello")

        phase.append(step)

        assert len(phase.steps) == 1
        assert phase.steps[0] is step

    def test_append_multiple_steps(self):
        """Test appending multiple steps maintains order."""
        phase = Phase("localhost", 6971)
        step1 = Step("echo first")
        step2 = Step("echo second")
        step3 = Step("echo third")

        phase.append(step1)
        phase.append(step2)
        phase.append(step3)

        assert len(phase.steps) == 3
        assert phase.steps[0] is step1
        assert phase.steps[1] is step2
        assert phase.steps[2] is step3


class TestPhaseExecution:
    """Test Phase execution functionality."""

    def test_run_executes_all_steps_in_order(self):
        """Test that run executes all steps and collects results."""
        phase = Phase("localhost", 6971)

        # Create mock steps
        step1 = MagicMock()
        step1.run.return_value = RetVal(0, "Step 1 done")

        step2 = MagicMock()
        step2.run.return_value = RetVal(0, "Step 2 done")

        step3 = MagicMock()
        step3.run.return_value = RetVal(1, "Step 3 failed")

        phase.append(step1)
        phase.append(step2)
        phase.append(step3)

        # Run the phase
        phase.run()

        # Verify all steps were executed
        step1.run.assert_called_once()
        step2.run.assert_called_once()
        step3.run.assert_called_once()

        # Verify results were collected
        assert len(phase.results) == 3
        assert phase.results[0].code == 0
        assert phase.results[0].message == "Step 1 done"
        assert phase.results[1].code == 0
        assert phase.results[1].message == "Step 2 done"
        assert phase.results[2].code == 1
        assert phase.results[2].message == "Step 3 failed"

    def test_run_with_no_steps(self):
        """Test that run handles empty step list gracefully."""
        phase = Phase("localhost", 6971)

        # Run with no steps
        phase.run()

        # Should complete without error and have no results
        assert len(phase.results) == 0


class TestPhaseResultsReporting:
    """Test Phase results reporting functionality."""

    @patch("socket.create_connection")
    def test_return_results_sends_all_results(self, mock_create_connection):
        """Test that return_results sends all results to conductor."""
        phase = Phase("localhost", 6971)

        # Add some results
        phase.results = [
            RetVal(0, "Step 1 success"),
            RetVal(1, "Step 2 failed"),
            RetVal(0, "Step 3 success"),
        ]

        # Create mock sockets
        mock_sockets = [MagicMock() for _ in range(4)]  # 3 results + 1 done message
        mock_create_connection.side_effect = mock_sockets

        # Call return_results
        phase.return_results()

        # Verify socket connections were created
        expected_calls = [call(("localhost", 6971)) for _ in range(4)]
        mock_create_connection.assert_has_calls(expected_calls)

        # Verify each result was sent
        for i, result in enumerate(phase.results):
            # The result's send method should have been called with the socket
            mock_sockets[i].sendall.assert_called_once()
            mock_sockets[i].close.assert_called_once()

        # Verify DONE message was sent
        mock_sockets[3].sendall.assert_called_once()
        mock_sockets[3].close.assert_called_once()

    @patch("socket.create_connection")
    def test_return_results_with_no_results(self, mock_create_connection):
        """Test that return_results still sends DONE with no results."""
        phase = Phase("localhost", 6971)

        # No results
        phase.results = []

        # Create mock socket for DONE message
        mock_socket = MagicMock()
        mock_create_connection.return_value = mock_socket

        # Call return_results
        phase.return_results()

        # Should only create one connection for DONE message
        mock_create_connection.assert_called_once_with(("localhost", 6971))

        # Verify DONE message was sent
        mock_socket.sendall.assert_called_once()
        mock_socket.close.assert_called_once()
