"""Integration tests for conduct CLI with argparse options."""

import pytest
import subprocess
import os
import tempfile
import time
from unittest.mock import patch, MagicMock
import sys
import socket
import threading

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConductCLIHelp:
    """Test conduct CLI help and version options."""
    
    def test_help_option(self):
        """Test that --help displays usage information."""
        result = subprocess.run(
            [sys.executable, 'scripts/conduct', '--help'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert 'Conductor - Orchestrate distributed system tests' in result.stdout
        assert '--trials' in result.stdout
        assert '--phases' in result.stdout
        assert '--dry-run' in result.stdout
    
    def test_help_short_option(self):
        """Test that -h displays usage information."""
        result = subprocess.run(
            [sys.executable, 'scripts/conduct', '-h'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert 'usage: conduct' in result.stdout
    
    def test_version_option(self):
        """Test that --version displays version."""
        result = subprocess.run(
            [sys.executable, 'scripts/conduct', '--version'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert 'Conductor 1.0' in result.stdout


class TestConductCLIErrors:
    """Test conduct CLI error handling."""
    
    def test_missing_config_file(self):
        """Test error when config file doesn't exist."""
        result = subprocess.run(
            [sys.executable, 'scripts/conduct', 'nonexistent.cfg'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 1
        assert 'Configuration file not found' in result.stderr
    
    def test_invalid_config_format(self):
        """Test error with invalid config file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cfg', delete=False) as f:
            f.write("This is not a valid INI file\n")
            config_file = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, 'scripts/conduct', config_file],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 1
            assert 'Failed to read configuration' in result.stderr
        finally:
            os.unlink(config_file)
    
    def test_missing_client_config(self):
        """Test error when client config file doesn't exist."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cfg', delete=False) as f:
            f.write("""[Test]
trials = 1

[Clients]
client1 = missing_client.cfg
""")
            config_file = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, 'scripts/conduct', config_file],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 1
            assert 'Client config not found' in result.stderr
        finally:
            os.unlink(config_file)


class TestConductCLIOptions:
    """Test conduct CLI option functionality."""
    
    def create_test_configs(self):
        """Create temporary test configuration files."""
        # Master config
        master_config = tempfile.NamedTemporaryFile(mode='w', suffix='.cfg', delete=False)
        master_config.write("""[Test]
trials = 2

[Clients]
client1 = {client1}
client2 = {client2}
""")
        master_config.close()
        
        # Client configs
        client1_config = tempfile.NamedTemporaryFile(mode='w', suffix='.cfg', delete=False)
        client1_config.write("""[Master]
player = 127.0.0.1
conductor = 127.0.0.1
cmdport = 16970
resultsport = 16971

[Startup]
step1 = echo "Client 1 startup"

[Run]
step1 = echo "Client 1 running"

[Collect]
step1 = echo "Client 1 collect"

[Reset]
step1 = echo "Client 1 reset"
""")
        client1_config.close()
        
        client2_config = tempfile.NamedTemporaryFile(mode='w', suffix='.cfg', delete=False)
        client2_config.write("""[Master]
player = 127.0.0.1
conductor = 127.0.0.1
cmdport = 16972
resultsport = 16973

[Startup]
step1 = echo "Client 2 startup"

[Run]
step1 = echo "Client 2 running"

[Collect]
step1 = echo "Client 2 collect"

[Reset]
step1 = echo "Client 2 reset"
""")
        client2_config.close()
        
        # Update master config with client paths
        with open(master_config.name, 'w') as f:
            f.write(f"""[Test]
trials = 2

[Clients]
client1 = {client1_config.name}
client2 = {client2_config.name}
""")
        
        return master_config.name, client1_config.name, client2_config.name
    
    def test_dry_run_option(self):
        """Test --dry-run shows what would be executed."""
        master, client1, client2 = self.create_test_configs()
        
        try:
            result = subprocess.run(
                [sys.executable, 'scripts/conduct', '--dry-run', master],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0
            # Check both stdout and stderr as logging may go to stderr
            output = result.stdout + result.stderr
            assert 'DRY RUN MODE' in output
            assert 'Would run 2 trial(s) with 2 client(s)' in output
            assert "Phases: ['all']" in output
        finally:
            os.unlink(master)
            os.unlink(client1)
            os.unlink(client2)
    
    def test_trials_option(self):
        """Test -t/--trials overrides config file."""
        master, client1, client2 = self.create_test_configs()
        
        try:
            result = subprocess.run(
                [sys.executable, 'scripts/conduct', '-t', '5', '--dry-run', master],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0
            output = result.stdout + result.stderr
            assert 'Would run 5 trial(s)' in output
        finally:
            os.unlink(master)
            os.unlink(client1)
            os.unlink(client2)
    
    def test_phases_option_single(self):
        """Test -p/--phases with single phase."""
        master, client1, client2 = self.create_test_configs()
        
        try:
            result = subprocess.run(
                [sys.executable, 'scripts/conduct', '-p', 'startup', '--dry-run', master],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0
            output = result.stdout + result.stderr
            assert "Phases: ['startup']" in output
        finally:
            os.unlink(master)
            os.unlink(client1)
            os.unlink(client2)
    
    def test_phases_option_multiple(self):
        """Test -p/--phases with multiple phases."""
        master, client1, client2 = self.create_test_configs()
        
        try:
            result = subprocess.run(
                [sys.executable, 'scripts/conduct', '-p', 'startup', 'reset', '--dry-run', master],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0
            output = result.stdout + result.stderr
            assert "Phases: ['startup', 'reset']" in output
        finally:
            os.unlink(master)
            os.unlink(client1)
            os.unlink(client2)
    
    def test_clients_option(self):
        """Test -c/--clients filters clients."""
        master, client1, client2 = self.create_test_configs()
        
        try:
            result = subprocess.run(
                [sys.executable, 'scripts/conduct', '-c', 'client1', '--dry-run', master],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0
            output = result.stdout + result.stderr
            assert 'Would run 2 trial(s) with 1 client(s)' in output
        finally:
            os.unlink(master)
            os.unlink(client1)
            os.unlink(client2)
    
    def test_verbose_option(self):
        """Test -v/--verbose enables debug output."""
        master, client1, client2 = self.create_test_configs()
        
        try:
            result = subprocess.run(
                [sys.executable, 'scripts/conduct', '-v', '--dry-run', master],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0
            assert 'DEBUG' in result.stderr or 'Loading client' in result.stderr
        finally:
            os.unlink(master)
            os.unlink(client1)
            os.unlink(client2)
    
    def test_quiet_option(self):
        """Test -q/--quiet suppresses non-error output."""
        master, client1, client2 = self.create_test_configs()
        
        try:
            result = subprocess.run(
                [sys.executable, 'scripts/conduct', '-q', '--dry-run', master],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0
            # In quiet mode, should have minimal output
            assert len(result.stdout) < 100  # Much less output than normal
        finally:
            os.unlink(master)
            os.unlink(client1)
            os.unlink(client2)


class TestConductCLIIntegration:
    """Integration tests with mock players."""
    
    def test_full_execution_with_mock_client(self):
        """Test conduct with mocked client connections."""
        master, client1, client2 = TestConductCLIOptions().create_test_configs()
        
        try:
            # We can't easily test actual network connections in unit tests,
            # so we'll use the existing Client tests approach
            from scripts import conduct
            
            # Mock the Client class
            with patch('conductor.client.Client') as MockClient:
                mock_client = MagicMock()
                MockClient.return_value = mock_client
                
                # Mock sys.argv
                with patch.object(sys, 'argv', ['conduct', '-t', '1', '-p', 'startup', 'run', master]):
                    # Capture stdout
                    from io import StringIO
                    captured_output = StringIO()
                    
                    with patch('sys.stdout', captured_output):
                        with patch('builtins.print'):
                            try:
                                conduct.__main__()
                            except SystemExit as e:
                                # Check for successful exit
                                assert e.code == 0
                
                # Verify client methods were called
                assert mock_client.startup.called
                assert mock_client.run.called
                assert mock_client.doit.called
                assert mock_client.results.called
                
                # Collect and reset should not be called
                assert not mock_client.collect.called
                assert not mock_client.reset.called
                
        finally:
            os.unlink(master)
            os.unlink(client1)
            os.unlink(client2)


class TestConductCLIWithRealNetwork:
    """Test conduct CLI with real network operations."""
    
    @pytest.mark.slow
    def test_conduct_with_mock_player(self):
        """Test conduct connecting to a mock player server."""
        # This would require starting a mock player server
        # and is more complex - marking as slow/optional
        pass