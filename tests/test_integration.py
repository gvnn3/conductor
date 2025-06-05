"""Integration tests that verify real behavior without excessive mocking."""

import socket
import threading
import time
import tempfile
import os
import struct

from conductor.client import Client
from conductor.phase import Phase
from conductor.step import Step
from conductor.retval import RetVal
import configparser


class TestRealStepExecution:
    """Test Step class with real subprocess execution."""

    def test_step_actually_executes_command(self):
        """Test that Step actually runs a command and returns output."""
        # Use a real command that works on all platforms
        step = Step("echo hello world")
        result = step.run()

        assert result.code == 0
        assert "hello world" in result.message

    def test_step_handles_real_command_failure(self):
        """Test Step with a command that actually fails."""
        # Use a command that will definitely fail
        step = Step("false")  # Unix command that always returns 1

        # For cross-platform, we could use Python
        step = Step('python -c "import sys; sys.exit(1)"')
        result = step.run()

        assert result.code == 1

    def test_spawn_command_actually_runs_in_background(self):
        """Test that spawn commands actually run without blocking."""
        # Create a temp file
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            temp_path = f.name

        try:
            # Command that writes to file after a delay
            cmd = f"python -c \"import time; time.sleep(0.1); open('{temp_path}', 'w').write('spawned')\""
            step = Step(cmd, spawn=True)

            # This should return immediately
            start_time = time.time()
            result = step.run()
            elapsed = time.time() - start_time

            assert elapsed < 0.05  # Should return almost immediately
            assert result.code == 0
            assert result.message == "Spawned"

            # Wait a bit and check if file was written
            time.sleep(0.2)
            with open(temp_path, "r") as f:
                assert f.read() == "spawned"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_timeout_actually_kills_long_running_command(self):
        """Test that timeout actually kills commands."""
        # Command that would run forever
        step = Step('python -c "import time; time.sleep(10)"', timeout=0.1)

        start_time = time.time()
        result = step.run()
        elapsed = time.time() - start_time

        assert elapsed < 0.5  # Should timeout quickly
        assert "timed out after" in result.message


class TestRealPhaseExecution:
    """Test Phase with real Step execution."""

    def test_phase_executes_multiple_real_commands(self):
        """Test that Phase actually runs multiple commands in sequence."""
        phase = Phase("localhost", 6971)

        # Add real commands
        phase.append(Step("echo first"))
        phase.append(Step("echo second"))
        phase.append(Step("echo third"))

        # Run the phase
        phase.run()

        # Check results
        assert len(phase.results) == 3
        assert "first" in phase.results[0].message
        assert "second" in phase.results[1].message
        assert "third" in phase.results[2].message

        # Verify they ran in order (each should have code 0)
        for result in phase.results:
            assert result.code == 0


class TestRealNetworkCommunication:
    """Test actual network communication between components."""

    def test_retval_send_over_real_socket(self):
        """Test RetVal actually sends data over a socket."""
        # Create a real socket pair
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(("localhost", 0))  # Bind to any available port
        _, port = server_sock.getsockname()
        server_sock.listen(1)

        # Function to accept connection and receive data
        received_data = []

        def server_thread():
            conn, _ = server_sock.accept()
            # Read length header
            length_data = b""
            while len(length_data) < 4:
                length_data += conn.recv(4 - len(length_data))
            # Read message
            length = socket.ntohl(struct.unpack("!I", length_data)[0])
            message_data = b""
            while len(message_data) < length:
                message_data += conn.recv(length - len(message_data))
            received_data.append(message_data)
            conn.close()

        # Start server thread
        import struct

        server = threading.Thread(target=server_thread)
        server.start()

        # Connect and send RetVal
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_sock.connect(("localhost", port))

        retval = RetVal(42, "Test message")
        retval.send(client_sock)

        client_sock.close()
        server.join()
        server_sock.close()

        # Verify data was received
        assert len(received_data) == 1
        import pickle

        received_retval = pickle.loads(received_data[0])
        assert received_retval.code == 42
        assert received_retval.message == "Test message"


class TestClientServerIntegration:
    """Test real client-server interaction."""

    def test_client_len_recv_with_real_data(self):
        """Test that len_recv actually reads length-prefixed messages correctly."""
        # Create a mock socket that simulates real behavior
        import struct
        import io

        # Create test data
        test_message = b"Hello from the test!"
        length_header = struct.pack("!I", socket.htonl(len(test_message)))
        full_data = length_header + test_message

        # Simulate socket with BytesIO
        class MockSocket:
            def __init__(self, data):
                self.data = io.BytesIO(data)
                self.recv_calls = 0

            def recv(self, size):
                # Simulate partial reads like a real socket might
                self.recv_calls += 1
                if self.recv_calls == 1:
                    # Return partial length header
                    return self.data.read(2)
                elif self.recv_calls == 2:
                    # Return rest of length header
                    return self.data.read(2)
                else:
                    # Return data in chunks
                    return self.data.read(min(size, 5))

        # Test with simulated socket
        mock_socket = MockSocket(full_data)

        # Create a minimal client to test len_recv
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

        from conductor.client import Client

        client = Client(config)

        # Test len_recv
        result = client.len_recv(mock_socket)

        assert result == test_message
        assert mock_socket.recv_calls > 2  # Should have taken multiple reads


class TestRealConfigParsing:
    """Test real configuration file parsing."""

    def test_client_parses_real_config_file(self):
        """Test Client can parse a real configuration file."""
        import tempfile
        import configparser

        # Create a real config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False) as f:
            f.write("""[Coordinator]
conductor = 10.0.0.1
player = 10.0.0.2
cmdport = 6970
resultsport = 6971

[Startup]
step1 = echo "Starting test environment"
step2 = mkdir -p /tmp/conductor_test
spawn1 = sleep 5

[Run]
step1 = echo "Running tests"
timeout10 = curl http://localhost:8080
spawn2 = python -m http.server 8080

[Collect]
step1 = tar -czf /tmp/results.tgz /tmp/conductor_test

[Reset]
step1 = rm -rf /tmp/conductor_test
""")
            config_file = f.name

        try:
            # Parse config and create client
            config = configparser.ConfigParser()
            config.read(config_file)

            client = Client(config)

            # Verify parsing worked correctly
            assert client.conductor == "10.0.0.1"
            assert client.player == "10.0.0.2"
            assert client.cmdport == 6970
            assert client.resultport == 6971

            # Check startup phase - spawn not parsed in startup
            assert len(client.startup_phase.steps) == 3
            assert client.startup_phase.steps[0].args == [
                "echo",
                "Starting test environment",
            ]
            assert client.startup_phase.steps[2].args == ["sleep", "5"]

            # Check run phase - spawn and timeout are parsed here
            assert len(client.run_phase.steps) == 3
            assert client.run_phase.steps[0].args == ["echo", "Running tests"]
            assert client.run_phase.steps[1].timeout == 10
            assert client.run_phase.steps[2].spawn is True

        finally:
            os.unlink(config_file)


class TestRealProcessCommunication:
    """Test real inter-process communication."""

    def test_player_style_socket_server(self):
        """Test a simplified version of player socket handling."""
        import threading
        import pickle

        server_ready = threading.Event()
        received_phases = []

        def mock_player_server():
            """Simplified player server that receives phases."""
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind(("localhost", 0))
            _, port = server_sock.getsockname()
            server_sock.listen(1)

            # Store port for client
            mock_player_server.port = port
            server_ready.set()

            # Accept one connection
            conn, _ = server_sock.accept()

            # Read length header
            length_data = b""
            while len(length_data) < 4:
                chunk = conn.recv(4 - len(length_data))
                if not chunk:
                    break
                length_data += chunk

            if len(length_data) == 4:
                # Read phase data
                import struct

                length = socket.ntohl(struct.unpack("!I", length_data)[0])

                phase_data = b""
                while len(phase_data) < length:
                    chunk = conn.recv(length - len(phase_data))
                    if not chunk:
                        break
                    phase_data += chunk

                if len(phase_data) == length:
                    phase = pickle.loads(phase_data)
                    received_phases.append(phase)

                    # Send response
                    response = RetVal(0, "Phase received")
                    response.send(conn)

            conn.close()
            server_sock.close()

        # Start server
        server_thread = threading.Thread(target=mock_player_server)
        server_thread.start()

        # Wait for server to be ready
        server_ready.wait(timeout=2)
        assert hasattr(mock_player_server, "port")

        # Create and send a phase
        test_phase = Phase("localhost", 6971)
        test_phase.append(Step("echo test"))

        # Connect and send
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_sock.connect(("localhost", mock_player_server.port))

        # Send phase using protocol
        phase_data = pickle.dumps(test_phase)
        length = struct.pack("!I", socket.htonl(len(phase_data)))
        client_sock.sendall(length + phase_data)

        # Read response
        response_length_data = b""
        while len(response_length_data) < 4:
            chunk = client_sock.recv(4 - len(response_length_data))
            response_length_data += chunk

        response_length = socket.ntohl(struct.unpack("!I", response_length_data)[0])
        response_data = b""
        while len(response_data) < response_length:
            chunk = client_sock.recv(response_length - len(response_data))
            response_data += chunk

        response = pickle.loads(response_data)

        client_sock.close()
        server_thread.join()

        # Verify
        assert len(received_phases) == 1
        assert len(received_phases[0].steps) == 1
        assert received_phases[0].steps[0].args == ["echo", "test"]
        assert response.code == 0
        assert response.message == "Phase received"


class TestEndToEndScenario:
    """Test a complete scenario with minimal mocking."""

    def test_phase_with_mixed_command_types(self):
        """Test a phase with different command types executing properly."""
        phase = Phase("localhost", 6971)

        # Regular command
        phase.append(Step("echo regular"))

        # Command that fails
        phase.append(Step('python -c "import sys; sys.exit(1)"'))

        # Spawn command (we'll verify it started but not wait)
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            spawn_marker = f.name

        spawn_cmd = f"python -c \"import time; time.sleep(0.1); open('{spawn_marker}', 'w').write('spawn_worked')\""
        phase.append(Step(spawn_cmd, spawn=True))

        # Timeout command
        phase.append(Step('python -c "import time; time.sleep(10)"', timeout=0.1))

        try:
            # Run the phase
            phase.run()

            # Verify results
            assert len(phase.results) == 4

            # First command succeeded
            assert phase.results[0].code == 0
            assert "regular" in phase.results[0].message

            # Second command failed
            assert phase.results[1].code == 1

            # Third command spawned
            assert phase.results[2].code == 0
            assert phase.results[2].message == "Spawned"

            # Fourth command timed out
            assert phase.results[3].code == 0
            assert phase.results[3].message == "Timeout"

            # Verify spawn command actually ran
            time.sleep(0.2)
            if os.path.exists(spawn_marker):
                with open(spawn_marker, "r") as f:
                    assert f.read() == "spawn_worked"
        finally:
            if os.path.exists(spawn_marker):
                os.unlink(spawn_marker)
