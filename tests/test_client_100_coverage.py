"""Tests to achieve 100% coverage for client.py."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import configparser
import socket
from conductor.client import Client
from conductor.retval import RETVAL_DONE
from conductor.json_protocol import send_message, receive_message, MSG_RUN, MSG_DONE, MSG_RESULT


class TestClientFullCoverage:
    """Test edge cases for complete client.py coverage."""
    
    def test_invalid_cmdport_out_of_range(self):
        """Test command port validation - out of range (lines 65-69)."""
        config = configparser.ConfigParser()
        config.read_string("""
[Coordinator]
conductor = localhost
player = testplayer
cmdport = 70000
resultsport = 6971

[Startup]
[Run]
[Collect]
[Reset]
""")
        
        with pytest.raises(ValueError, match="Invalid command port: 70000"):
            Client(config)
    
    def test_invalid_cmdport_not_number(self):
        """Test command port validation - not a number."""
        config = configparser.ConfigParser()
        config.read_string("""
[Coordinator]
conductor = localhost
player = testplayer
cmdport = notanumber
resultsport = 6971

[Startup]
[Run]
[Collect]
[Reset]
""")
        
        with pytest.raises(ValueError, match="Invalid command port: notanumber"):
            Client(config)
    
    def test_invalid_resultsport_out_of_range(self):
        """Test results port validation - out of range (lines 74-78)."""
        config = configparser.ConfigParser()
        config.read_string("""
[Coordinator]
conductor = localhost
player = testplayer
cmdport = 6970
resultsport = 0

[Startup]
[Run]
[Collect]
[Reset]
""")
        
        with pytest.raises(ValueError, match="Invalid results port: 0"):
            Client(config)
    
    def test_spawn_key_in_run_phase(self):
        """Test spawn key handling in Run phase (line 96)."""
        config = configparser.ConfigParser()
        config.read_string("""
[Coordinator]
conductor = localhost
player = testplayer
cmdport = 6970
resultsport = 6971

[Startup]
[Run]
spawn1 = sleep 10
[Collect]
[Reset]
""")
        
        client = Client(config)
        
        assert len(client.run_phase.steps) == 1
        assert client.run_phase.steps[0].spawn is True
        assert client.run_phase.steps[0].command == "sleep 10"
    
    def test_timeout_key_without_number(self):
        """Test timeout key without number (lines 104-105)."""
        config = configparser.ConfigParser()
        config.read_string("""
[Coordinator]
conductor = localhost
player = testplayer
cmdport = 6970
resultsport = 6971

[Startup]
[Run]
timeoutabc = echo test
[Collect]
[Reset]
""")
        
        client = Client(config)
        
        # Should create normal step since timeout has no number
        assert len(client.run_phase.steps) == 1
        assert client.run_phase.steps[0].spawn is False
        assert client.run_phase.steps[0].timeout == 30  # default
    
    def test_timeout_command_malformed(self):
        """Test malformed timeout command (lines 121-123)."""
        config = configparser.ConfigParser()
        config.read_string("""
[Coordinator]
conductor = localhost
player = testplayer
cmdport = 6970
resultsport = 6971

[Startup]
[Run]
cmd1 = timeout
cmd2 = timeoutabc:echo test
[Collect]
[Reset]
""")
        
        client = Client(config)
        
        # Both should be normal steps
        assert len(client.run_phase.steps) == 2
        for step in client.run_phase.steps:
            assert step.spawn is False
            assert step.timeout == 30
    
    def test_len_recv_exact_size(self):
        """Test len_recv when data is exactly the requested size (line 196)."""
        # Create a mock socket
        mock_socket = Mock()
        mock_socket.recv.side_effect = [b"1234"]  # Exactly 4 bytes
        
        # Create client with minimal config
        config = configparser.ConfigParser()
        config.read_string("""
[Coordinator]
conductor = localhost
player = testplayer
cmdport = 6970
resultsport = 6971

[Startup]
[Run]
[Collect]
[Reset]
""")
        client = Client(config)
        
        # Test len_recv
        data = client.len_recv(mock_socket, 4)
        assert data == b"1234"
        assert mock_socket.recv.call_count == 1
    
    def test_download_socket_connect_error(self):
        """Test download with socket connection error (lines 227-228)."""
        config = configparser.ConfigParser()
        config.read_string("""
[Coordinator]
conductor = localhost
player = testplayer
cmdport = 6970
resultsport = 6971

[Startup]
[Run]
[Collect]
[Reset]
""")
        client = Client(config)
        
        with patch('socket.socket') as mock_socket_class:
            mock_socket = Mock()
            mock_socket.connect.side_effect = socket.error("Connection refused")
            mock_socket_class.return_value = mock_socket
            
            # Should handle the error gracefully
            client.download(client.startup_phase)
            
            # Verify socket was closed
            mock_socket.close.assert_called_once()
    
    def test_doit_socket_error_handling(self):
        """Test doit with socket errors (lines 237, 241)."""
        config = configparser.ConfigParser()
        config.read_string("""
[Coordinator]
conductor = localhost
player = testplayer
cmdport = 6970
resultsport = 6971

[Startup]
[Run]
[Collect]
[Reset]
""")
        client = Client(config)
        
        # Test cmd socket error (line 237)
        with patch('socket.socket') as mock_socket_class:
            mock_cmd_socket = Mock()
            mock_cmd_socket.connect.side_effect = socket.error("Connection refused")
            mock_socket_class.return_value = mock_cmd_socket
            
            client.doit()
            
            # Verify socket was closed
            mock_cmd_socket.close.assert_called_once()
    
    def test_results_socket_close_error(self):
        """Test results method when socket close fails (line 250)."""
        config = configparser.ConfigParser()
        config.read_string("""
[Coordinator]
conductor = localhost
player = testplayer
cmdport = 6970
resultsport = 6971

[Startup]
[Run]
[Collect]
[Reset]
""")
        client = Client(config)
        
        # Create mock result socket
        mock_socket = Mock()
        
        # Mock receive_message to return DONE immediately
        with patch('conductor.client.receive_message') as mock_receive:
            mock_receive.return_value = (MSG_DONE, {"code": RETVAL_DONE})
            
            # Make close raise an exception
            mock_socket.close.side_effect = socket.error("Already closed")
            
            # Should handle the error gracefully
            client.results(mock_socket)
            
            # Verify close was attempted
            mock_socket.close.assert_called_once()