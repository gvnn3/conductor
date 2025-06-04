"""Integration tests that verify real behavior without excessive mocking."""

import pytest
import socket
import threading
import time
import tempfile
import os
from unittest.mock import patch

from conductor.client import Client
from conductor.phase import Phase
from conductor.step import Step
from conductor.retval import RetVal, RETVAL_DONE
from conductor.run import Run
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
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            temp_path = f.name
        
        try:
            # Command that writes to file after a delay
            cmd = f'python -c "import time; time.sleep(0.1); open(\'{temp_path}\', \'w\').write(\'spawned\')"'
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
            with open(temp_path, 'r') as f:
                assert f.read() == 'spawned'
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
        assert result.message == "Timeout"


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
        server_sock.bind(('localhost', 0))  # Bind to any available port
        _, port = server_sock.getsockname()
        server_sock.listen(1)
        
        # Function to accept connection and receive data
        received_data = []
        def server_thread():
            conn, _ = server_sock.accept()
            # Read length header
            length_data = b''
            while len(length_data) < 4:
                length_data += conn.recv(4 - len(length_data))
            # Read message
            length = socket.ntohl(struct.unpack('!I', length_data)[0])
            message_data = b''
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
        client_sock.connect(('localhost', port))
        
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
        length_header = struct.pack('!I', socket.htonl(len(test_message)))
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
        config['Master'] = {
            'conductor': 'localhost',
            'player': 'localhost',
            'cmdport': '6970',
            'resultsport': '6971'
        }
        config['Startup'] = {}
        config['Run'] = {}
        config['Collect'] = {}
        config['Reset'] = {}
        
        from conductor.client import Client
        client = Client(config)
        
        # Test len_recv
        result = client.len_recv(mock_socket)
        
        assert result == test_message
        assert mock_socket.recv_calls > 2  # Should have taken multiple reads


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
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            spawn_marker = f.name
        
        spawn_cmd = f'python -c "import time; time.sleep(0.1); open(\'{spawn_marker}\', \'w\').write(\'spawn_worked\')"'
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
                with open(spawn_marker, 'r') as f:
                    assert f.read() == 'spawn_worked'
        finally:
            if os.path.exists(spawn_marker):
                os.unlink(spawn_marker)