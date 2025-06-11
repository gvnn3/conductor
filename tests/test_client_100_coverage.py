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
    
    
    def test_download_socket_connect_error(self):
        """Test download with socket connection error - now handles gracefully."""
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
        
        with patch('socket.create_connection') as mock_create_connection:
            mock_create_connection.side_effect = socket.error("Connection refused")
            
            # Should handle the error gracefully without exiting
            with patch('builtins.print') as mock_print:
                client.download(client.startup_phase)
                
                # Should print error message
                mock_print.assert_called_once()
                args = mock_print.call_args[0]
                assert "Failed to connect to testplayer:6970" in args[0]
    
    def test_doit_socket_error_handling(self):
        """Test doit with socket errors - now handles gracefully."""
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
        
        # Test cmd socket error
        with patch('socket.create_connection') as mock_create_connection:
            mock_create_connection.side_effect = socket.error("Connection refused")
            
            # Should handle the error gracefully without exiting
            with patch('builtins.print') as mock_print:
                client.doit()
                
                # Should print error message
                mock_print.assert_called_once()
                args = mock_print.call_args[0]
                assert "Failed to connect to testplayer:6970" in args[0]
    
    def test_so_reuseport_not_available(self):
        """Test handling when SO_REUSEPORT is not available on platform."""
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
        
        # Test that doit handles missing SO_REUSEPORT gracefully
        with patch('socket.create_connection') as mock_create_connection:
            with patch('socket.socket') as mock_socket_class:
                mock_cmd_socket = Mock()
                mock_create_connection.return_value = mock_cmd_socket
                
                mock_results_socket = Mock()
                mock_socket_class.return_value = mock_results_socket
                
                # Make SO_REUSEPORT raise AttributeError
                mock_results_socket.setsockopt.side_effect = lambda level, optname, value: (
                    None if optname != socket.SO_REUSEPORT else (_ for _ in ()).throw(AttributeError)
                )
                
                # Should not raise exception
                client.doit()
                
                # Verify SO_REUSEADDR was still set
                mock_results_socket.setsockopt.assert_any_call(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    def test_results_with_reporter(self):
        """Test results method with a reporter object."""
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
        
        # Create mock result socket and reporter
        mock_ressock = Mock()
        mock_conn = Mock()
        mock_reporter = Mock()
        client.ressock = mock_ressock
        
        # Mock receive_message to return results then DONE
        with patch('conductor.client.receive_message') as mock_receive:
            mock_receive.side_effect = [
                (MSG_RESULT, {"code": 0, "message": "Step 1 complete"}),
                (MSG_RESULT, {"code": RETVAL_DONE, "message": "All done"})
            ]
            
            # Setup accept to return connections
            mock_ressock.accept.side_effect = [
                (mock_conn, ("127.0.0.1", 12345)),
                (mock_conn, ("127.0.0.1", 12346))
            ]
            
            # Call results with reporter
            client.results(reporter=mock_reporter)
            
            # Verify reporter was called
            assert mock_reporter.add_result.call_count == 2
            mock_reporter.add_result.assert_any_call(0, "Step 1 complete")
            mock_reporter.add_result.assert_any_call(RETVAL_DONE, "All done")
    
    def test_timeout_key_with_non_digit_number(self):
        """Test timeout key where the number part contains non-digits."""
        config = configparser.ConfigParser()
        config.read_string("""
[Coordinator]
conductor = localhost
player = testplayer
cmdport = 6970
resultsport = 6971

[Startup]
[Run]
timeout10a = echo test
[Collect]
[Reset]
""")
        
        client = Client(config)
        
        # Should create normal step since timeout number is not all digits
        assert len(client.run_phase.steps) == 1
        assert client.run_phase.steps[0].spawn is False
        assert client.run_phase.steps[0].timeout == 30  # default
    
    def test_spawn_in_startup_phase(self):
        """Test spawn command in startup phase."""
        config = configparser.ConfigParser()
        config.read_string("""
[Coordinator]
conductor = localhost
player = testplayer
cmdport = 6970
resultsport = 6971

[Startup]
spawn1 = iperf -s
[Run]
[Collect]
[Reset]
""")
        
        client = Client(config)
        
        # Should create spawn step in startup phase
        assert len(client.startup_phase.steps) == 1
        assert client.startup_phase.steps[0].spawn is True
        assert client.startup_phase.steps[0].command == "iperf -s"
    
    def test_timeout_key_with_valid_number(self):
        """Test timeout key with valid number that triggers line 101."""
        config = configparser.ConfigParser()
        config.read_string("""
[Coordinator]
conductor = localhost
player = testplayer
cmdport = 6970
resultsport = 6971

[Startup]
[Run]
timeout15 = wget http://example.com
[Collect]
[Reset]
""")
        
        client = Client(config)
        
        # Should create step with custom timeout
        assert len(client.run_phase.steps) == 1
        assert client.run_phase.steps[0].spawn is False
        assert client.run_phase.steps[0].timeout == 15  # custom timeout from key name
