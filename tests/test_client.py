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