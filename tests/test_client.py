"""Tests for the Client class."""

import pytest
from unittest.mock import MagicMock, patch, call
import configparser
import socket
import struct

from conductor.client import Client
from conductor.phase import Phase
from conductor.retval import RetVal, RETVAL_DONE


class TestClientInitialization:
    """Test Client initialization and configuration parsing."""

    def create_test_config(self):
        """Create a test configuration."""
        config = configparser.ConfigParser()
        config["Coordinator"] = {
            "conductor": "192.168.1.1",
            "player": "192.168.1.10",
            "cmdport": "6970",
            "resultsport": "6971",
        }
        config["Startup"] = {
            "step1": 'echo "Starting up"',
            "step2": "mkdir -p /tmp/test",
        }
        config["Run"] = {
            "step1": 'echo "Running"',
            "step2": "spawn:iperf -s",
            "step3": "timeout30:wget http://example.com",
        }
        config["Collect"] = {"step1": "tar -czf results.tgz /tmp/test"}
        config["Reset"] = {"step1": "rm -rf /tmp/test"}
        return config

    def test_initialization_parses_coordinator_config(self):
        """Test that Client parses Coordinator configuration correctly."""
        config = self.create_test_config()

        client = Client(config)

        assert client.conductor == "192.168.1.1"
        assert client.player == "192.168.1.10"
        assert client.cmdport == 6970
        assert client.resultport == 6971

    def test_initialization_creates_phases(self):
        """Test that Client creates all four phases."""
        config = self.create_test_config()

        client = Client(config)

        assert hasattr(client, "startup_phase")
        assert hasattr(client, "run_phase")
        assert hasattr(client, "collect_phase")
        assert hasattr(client, "reset_phase")

        assert isinstance(client.startup_phase, Phase)
        assert isinstance(client.run_phase, Phase)
        assert isinstance(client.collect_phase, Phase)
        assert isinstance(client.reset_phase, Phase)

    def test_startup_phase_has_correct_steps(self):
        """Test that Startup phase has correct steps."""
        config = self.create_test_config()

        client = Client(config)

        assert len(client.startup_phase.steps) == 2
        assert client.startup_phase.steps[0].args == ["echo", "Starting up"]
        assert client.startup_phase.steps[1].args == ["mkdir", "-p", "/tmp/test"]

    def test_run_phase_parses_spawn_and_timeout_correctly(self):
        """Test that Run phase correctly parses spawn and timeout commands."""
        config = self.create_test_config()

        client = Client(config)

        assert len(client.run_phase.steps) == 3

        # Normal command
        assert client.run_phase.steps[0].args == ["echo", "Running"]
        assert client.run_phase.steps[0].spawn is False
        assert client.run_phase.steps[0].timeout == 30  # default

        # Spawn command
        assert client.run_phase.steps[1].args == ["iperf", "-s"]
        assert client.run_phase.steps[1].spawn is True
        assert client.run_phase.steps[1].timeout == 30  # default

        # Timeout command
        assert client.run_phase.steps[2].args == ["wget", "http://example.com"]
        assert client.run_phase.steps[2].spawn is False
        assert client.run_phase.steps[2].timeout == 30  # parsed from config key

    def test_collect_and_reset_phases_have_correct_steps(self):
        """Test that Collect and Reset phases have correct steps."""
        config = self.create_test_config()

        client = Client(config)

        # Collect phase
        assert len(client.collect_phase.steps) == 1
        assert client.collect_phase.steps[0].args == [
            "tar",
            "-czf",
            "results.tgz",
            "/tmp/test",
        ]

        # Reset phase
        assert len(client.reset_phase.steps) == 1
        assert client.reset_phase.steps[0].args == ["rm", "-rf", "/tmp/test"]


class TestClientCommunication:
    """Test Client socket communication methods."""

    def create_test_client(self):
        """Create a test client with minimal config."""
        config = configparser.ConfigParser()
        config["Coordinator"] = {
            "conductor": "localhost",
            "player": "localhost",
            "cmdport": "6970",
            "resultsport": "6971",
        }
        config["Startup"] = {}
        config["Run"] = {}
        config["Collect"] = {}
        config["Reset"] = {}
        return Client(config)

    @patch("socket.create_connection")
    @patch("conductor.client.receive_message")
    def test_download_sends_phase_to_player(self, mock_receive_message, mock_create_connection):
        """Test that download sends a phase to the player."""
        client = self.create_test_client()
        mock_socket = MagicMock()
        mock_create_connection.return_value = mock_socket

        # Mock receive_message to return JSON response
        mock_receive_message.return_value = ("result", {"code": 0, "message": "phase received"})

        # Create a phase to download
        test_phase = Phase("localhost", 6971)

        # Call download
        with patch("builtins.print") as mock_print:
            client.download(test_phase)
            mock_print.assert_called_once_with(0, "phase received")

        # Verify connection was made
        mock_create_connection.assert_called_once_with(("localhost", 6970))

        # Verify data was sent
        mock_socket.sendall.assert_called_once()

        # Verify socket was closed
        mock_socket.close.assert_called_once()

    @patch("socket.create_connection")
    @patch("builtins.print")
    def test_download_handles_connection_failure(
        self, mock_print, mock_create_connection
    ):
        """Test that download handles connection failures."""
        client = self.create_test_client()
        mock_create_connection.side_effect = socket.error("Connection refused")

        # Create a phase to download
        test_phase = Phase("localhost", 6971)

        # Mock exit to prevent actual exit and raise exception instead
        with patch("builtins.exit", side_effect=SystemExit):
            with pytest.raises(SystemExit):
                client.download(test_phase)

        # We now print two lines: the connection error and the actual error
        assert mock_print.call_count == 2
        assert mock_print.call_args_list[0] == (
            ("Failed to connect to: ", "localhost", 6970),
        )
        assert mock_print.call_args_list[1][0][0] == "Error:"

    @patch("socket.create_connection")
    @patch("socket.socket")
    def test_doit_sends_run_command_and_sets_up_results_socket(
        self, mock_socket_class, mock_create_connection
    ):
        """Test that doit sends Run command and sets up results socket."""
        client = self.create_test_client()

        # Mock command socket
        mock_cmd_socket = MagicMock()
        mock_create_connection.return_value = mock_cmd_socket

        # Mock results socket
        mock_results_socket = MagicMock()
        mock_socket_class.return_value = mock_results_socket

        # Call doit
        with patch("builtins.print"):  # Suppress Run() print
            client.doit()

        # Verify command socket operations
        mock_create_connection.assert_called_once_with(("localhost", 6970))
        mock_cmd_socket.settimeout.assert_called_once_with(1.0)
        mock_cmd_socket.sendall.assert_called_once()
        mock_cmd_socket.close.assert_called_once()

        # Verify results socket setup
        mock_socket_class.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM, 0)
        mock_results_socket.setsockopt.assert_any_call(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
        )
        mock_results_socket.setsockopt.assert_any_call(
            socket.SOL_SOCKET, socket.SO_REUSEPORT, 1
        )
        mock_results_socket.bind.assert_called_once_with(("0.0.0.0", 6971))
        mock_results_socket.listen.assert_called_once_with(5)

        # Verify socket is stored
        assert client.ressock is mock_results_socket

    @patch("socket.create_connection")
    @patch("builtins.print")
    def test_doit_handles_connection_failure(self, mock_print, mock_create_connection):
        """Test that doit handles connection failures."""
        client = self.create_test_client()
        mock_create_connection.side_effect = socket.error("Connection refused")

        # Mock exit to prevent actual exit and raise exception instead
        with patch("builtins.exit", side_effect=SystemExit):
            with pytest.raises(SystemExit):
                client.doit()

        # We now print two lines: the connection error and the actual error
        assert mock_print.call_count == 2
        assert mock_print.call_args_list[0] == (
            ("Failed to connect to: ", "localhost", 6970),
        )
        assert mock_print.call_args_list[1][0][0] == "Error:"

    @patch("conductor.client.receive_message")
    def test_results_receives_messages_until_done(self, mock_receive_message):
        """Test that results receives messages until RETVAL_DONE."""
        client = self.create_test_client()

        # Create mock results socket
        mock_ressock = MagicMock()
        client.ressock = mock_ressock

        # Create mock connections with different messages
        mock_conn1 = MagicMock()
        mock_conn2 = MagicMock()
        mock_conn3 = MagicMock()

        # Set up accept to return connections in sequence
        mock_ressock.accept.side_effect = [
            (mock_conn1, ("127.0.0.1", 12345)),
            (mock_conn2, ("127.0.0.1", 12346)),
            (mock_conn3, ("127.0.0.1", 12347)),
        ]

        # Mock receive_message to return different messages
        mock_receive_message.side_effect = [
            ("result", {"code": 0, "message": "Step 1 complete"}),
            ("result", {"code": 1, "message": "Step 2 failed"}),
            ("result", {"code": RETVAL_DONE, "message": "All done"}),
        ]

        # Call results
        with patch("builtins.print") as mock_print:
            client.results()

        # Verify correct number of accepts
        assert mock_ressock.accept.call_count == 3

        # Verify all connections were closed
        mock_conn1.close.assert_called_once()
        mock_conn2.close.assert_called_once()
        mock_conn3.close.assert_called_once()

        # Verify results socket was closed
        mock_ressock.close.assert_called_once()

        # Verify prints
        expected_prints = [
            call(0, "Step 1 complete"),
            call(1, "Step 2 failed"),
            call("done"),
        ]
        mock_print.assert_has_calls(expected_prints)


class TestClientPhaseMethods:
    """Test Client phase execution methods."""

    def create_test_client(self):
        """Create a test client with minimal config."""
        config = configparser.ConfigParser()
        config["Coordinator"] = {
            "conductor": "localhost",
            "player": "localhost",
            "cmdport": "6970",
            "resultsport": "6971",
        }
        config["Startup"] = {"step1": "echo startup"}
        config["Run"] = {"step1": "echo run"}
        config["Collect"] = {"step1": "echo collect"}
        config["Reset"] = {"step1": "echo reset"}
        return Client(config)

    def test_startup_calls_download_with_startup_phase(self):
        """Test that startup() calls download with startup_phase."""
        client = self.create_test_client()
        client.download = MagicMock()

        client.startup()

        client.download.assert_called_once_with(client.startup_phase)

    def test_run_calls_download_with_run_phase(self):
        """Test that run() calls download with run_phase."""
        client = self.create_test_client()
        client.download = MagicMock()

        client.run()

        client.download.assert_called_once_with(client.run_phase)

    def test_collect_calls_download_with_collect_phase(self):
        """Test that collect() calls download with collect_phase."""
        client = self.create_test_client()
        client.download = MagicMock()

        client.collect()

        client.download.assert_called_once_with(client.collect_phase)

    def test_reset_calls_download_with_reset_phase(self):
        """Test that reset() calls download with reset_phase."""
        client = self.create_test_client()
        client.download = MagicMock()

        client.reset()

        client.download.assert_called_once_with(client.reset_phase)


class TestClientLenRecv:
    """Test Client len_recv method."""

    def test_len_recv_reads_length_prefixed_message(self):
        """Test that len_recv correctly reads length-prefixed messages."""
        client = TestClientCommunication().create_test_client()

        # Create test message
        test_data = b"Hello, World!"
        length = struct.pack("!I", len(test_data))

        # Mock socket that returns data in chunks
        mock_socket = MagicMock()
        # First call returns length header
        # Second call returns the data
        mock_socket.recv.side_effect = [length, test_data]

        # Call len_recv
        result = client.len_recv(mock_socket)

        # Verify result
        assert result == test_data

        # Verify recv was called correctly
        assert mock_socket.recv.call_count == 2
        mock_socket.recv.assert_any_call(4)
        mock_socket.recv.assert_any_call(len(test_data))

    def test_len_recv_handles_partial_reads(self):
        """Test that len_recv handles partial socket reads."""
        client = TestClientCommunication().create_test_client()

        # Create test message
        test_data = b"Hello, World!"
        length = struct.pack("!I", len(test_data))

        # Mock socket that returns data in small chunks
        mock_socket = MagicMock()
        # Return length in 2 chunks, then data in 3 chunks
        mock_socket.recv.side_effect = [
            length[:2],
            length[2:],  # Length header in 2 parts
            test_data[:5],
            test_data[5:10],
            test_data[10:],  # Data in 3 parts
        ]

        # Call len_recv
        result = client.len_recv(mock_socket)

        # Verify result
        assert result == test_data

        # Verify recv was called 5 times
        assert mock_socket.recv.call_count == 5
