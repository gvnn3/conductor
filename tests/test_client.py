"""Tests for the Client class."""

import pytest
from unittest.mock import MagicMock, patch, call
import configparser
import socket
import pickle

from conductor.client import Client
from conductor.phase import Phase
from conductor.step import Step
from conductor.run import Run
from conductor.retval import RetVal
from conductor.config import Config


class TestClientInitialization:
    """Test Client initialization and configuration parsing."""
    
    def create_test_config(self):
        """Create a test configuration."""
        config = configparser.ConfigParser()
        config['Master'] = {
            'conductor': '192.168.1.1',
            'player': '192.168.1.10',
            'cmdport': '6970',
            'resultsport': '6971'
        }
        config['Startup'] = {
            'step1': 'echo "Starting up"',
            'step2': 'mkdir -p /tmp/test'
        }
        config['Run'] = {
            'step1': 'echo "Running"',
            'spawn1': 'iperf -s',
            'timeout30': 'wget http://example.com'
        }
        config['Collect'] = {
            'step1': 'tar -czf results.tgz /tmp/test'
        }
        config['Reset'] = {
            'step1': 'rm -rf /tmp/test'
        }
        return config
    
    def test_initialization_parses_master_config(self):
        """Test that Client parses Master configuration correctly."""
        config = self.create_test_config()
        
        client = Client(config)
        
        assert client.conductor == '192.168.1.1'
        assert client.player == '192.168.1.10'
        assert client.cmdport == 6970
        assert client.resultport == 6971
    
    def test_initialization_creates_phases(self):
        """Test that Client creates all four phases."""
        config = self.create_test_config()
        
        client = Client(config)
        
        assert hasattr(client, 'startup_phase')
        assert hasattr(client, 'run_phase')
        assert hasattr(client, 'collect_phase')
        assert hasattr(client, 'reset_phase')
        
        assert isinstance(client.startup_phase, Phase)
        assert isinstance(client.run_phase, Phase)
        assert isinstance(client.collect_phase, Phase)
        assert isinstance(client.reset_phase, Phase)
    
    def test_startup_phase_has_correct_steps(self):
        """Test that Startup phase has correct steps."""
        config = self.create_test_config()
        
        client = Client(config)
        
        assert len(client.startup_phase.steps) == 2
        assert client.startup_phase.steps[0].args == ['echo', 'Starting up']
        assert client.startup_phase.steps[1].args == ['mkdir', '-p', '/tmp/test']
    
    def test_run_phase_parses_spawn_and_timeout_correctly(self):
        """Test that Run phase correctly parses spawn and timeout commands."""
        config = self.create_test_config()
        
        client = Client(config)
        
        assert len(client.run_phase.steps) == 3
        
        # Normal command
        assert client.run_phase.steps[0].args == ['echo', 'Running']
        assert client.run_phase.steps[0].spawn is False
        assert client.run_phase.steps[0].timeout == 30  # default
        
        # Spawn command
        assert client.run_phase.steps[1].args == ['iperf', '-s']
        assert client.run_phase.steps[1].spawn is True
        assert client.run_phase.steps[1].timeout == 30  # default
        
        # Timeout command
        assert client.run_phase.steps[2].args == ['wget', 'http://example.com']
        assert client.run_phase.steps[2].spawn is False
        assert client.run_phase.steps[2].timeout == 30  # parsed from config key
    
    def test_collect_and_reset_phases_have_correct_steps(self):
        """Test that Collect and Reset phases have correct steps."""
        config = self.create_test_config()
        
        client = Client(config)
        
        # Collect phase
        assert len(client.collect_phase.steps) == 1
        assert client.collect_phase.steps[0].args == ['tar', '-czf', 'results.tgz', '/tmp/test']
        
        # Reset phase
        assert len(client.reset_phase.steps) == 1
        assert client.reset_phase.steps[0].args == ['rm', '-rf', '/tmp/test']


class TestClientCommunication:
    """Test Client socket communication methods."""
    
    def create_test_client(self):
        """Create a test client with minimal config."""
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
        return Client(config)
    
    @patch('socket.create_connection')
    def test_download_sends_phase_to_player(self, mock_create_connection):
        """Test that download sends a phase to the player."""
        client = self.create_test_client()
        mock_socket = MagicMock()
        mock_create_connection.return_value = mock_socket
        
        # Mock len_recv to return a pickled RetVal
        retval = RetVal(0, "phase received")
        client.len_recv = MagicMock(return_value=pickle.dumps(retval))
        
        # Create a phase to download
        test_phase = Phase("localhost", 6971)
        
        # Call download
        with patch('builtins.print') as mock_print:
            client.download(test_phase)
            mock_print.assert_called_once_with(0, "phase received")
        
        # Verify connection was made
        mock_create_connection.assert_called_once_with(('localhost', 6970))
        
        # Verify data was sent (phase was pickled and sent)
        mock_socket.sendall.assert_called_once()
        
        # Verify socket was closed
        mock_socket.close.assert_called_once()
    
    @patch('socket.create_connection')
    @patch('builtins.print')
    def test_download_handles_connection_failure(self, mock_print, mock_create_connection):
        """Test that download handles connection failures."""
        client = self.create_test_client()
        mock_create_connection.side_effect = socket.error("Connection refused")
        
        # Create a phase to download
        test_phase = Phase("localhost", 6971)
        
        # Mock exit to prevent actual exit and raise exception instead
        with patch('builtins.exit', side_effect=SystemExit):
            with pytest.raises(SystemExit):
                client.download(test_phase)
        
        mock_print.assert_called_once_with("Failed to connect to: ", 'localhost', 6970)