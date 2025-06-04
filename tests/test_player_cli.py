"""Integration tests for player CLI with argparse options."""

import pytest
import subprocess
import os
import tempfile
import sys
import socket
import threading
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPlayerCLIHelp:
    """Test player CLI help and version options."""
    
    def test_help_option(self):
        """Test that --help displays usage information."""
        result = subprocess.run(
            [sys.executable, 'scripts/player', '--help'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert 'Player - Execute commands from conductor' in result.stdout
        assert '--bind' in result.stdout
        assert '--port' in result.stdout
        assert '--log-file' in result.stdout
    
    def test_help_short_option(self):
        """Test that -h displays usage information."""
        result = subprocess.run(
            [sys.executable, 'scripts/player', '-h'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert 'usage: player' in result.stdout
    
    def test_version_option(self):
        """Test that --version displays version."""
        result = subprocess.run(
            [sys.executable, 'scripts/player', '--version'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert 'Player 1.0' in result.stdout


class TestPlayerCLIErrors:
    """Test player CLI error handling."""
    
    def test_missing_config_file(self):
        """Test error when config file doesn't exist."""
        result = subprocess.run(
            [sys.executable, 'scripts/player', 'nonexistent.cfg'],
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
                [sys.executable, 'scripts/player', config_file],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 1
            assert 'Configuration missing [Master] section' in result.stderr
        finally:
            os.unlink(config_file)
    
    def test_missing_cmdport(self):
        """Test error when cmdport is missing from config."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cfg', delete=False) as f:
            f.write("""[Master]
player = 127.0.0.1
conductor = 127.0.0.1
""")
            config_file = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, 'scripts/player', config_file],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 1
            assert 'cmdport' in result.stderr
        finally:
            os.unlink(config_file)


class TestPlayerCLIOptions:
    """Test player CLI option functionality."""
    
    def create_test_config(self, port=16970):
        """Create a test player configuration."""
        config = tempfile.NamedTemporaryFile(mode='w', suffix='.cfg', delete=False)
        config.write(f"""[Master]
player = 127.0.0.1
conductor = 127.0.0.1
cmdport = {port}
resultsport = {port + 1}

[Startup]
step1 = echo "startup"

[Run]
step1 = echo "running"

[Collect]
step1 = echo "collecting"

[Reset]
step1 = echo "reset"
""")
        config.close()
        return config.name
    
    def test_bind_option(self):
        """Test -b/--bind option."""
        config_file = self.create_test_config(port=17000)
        
        try:
            # Start player with specific bind address
            proc = subprocess.Popen(
                [sys.executable, 'scripts/player', '-b', '127.0.0.1', config_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Give it time to start
            time.sleep(0.5)
            
            # Check if it's listening
            try:
                # Try to connect
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('127.0.0.1', 17000))
                sock.close()
                assert result == 0  # Connected successfully
            finally:
                proc.terminate()
                proc.wait()
                
        finally:
            os.unlink(config_file)
    
    def test_port_option_override(self):
        """Test -p/--port overrides config file."""
        config_file = self.create_test_config(port=17000)
        
        try:
            # Start player with different port
            proc = subprocess.Popen(
                [sys.executable, 'scripts/player', '-p', '17100', config_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Give it time to start
            time.sleep(0.5)
            
            # Check if it's listening on the override port
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('127.0.0.1', 17100))
                sock.close()
                assert result == 0  # Connected successfully
            finally:
                proc.terminate()
                proc.wait()
                
        finally:
            os.unlink(config_file)
    
    def test_log_file_option(self):
        """Test -l/--log-file creates log file."""
        config_file = self.create_test_config(port=17200)
        log_file = tempfile.mktemp(suffix='.log')
        
        try:
            # Start player with log file
            proc = subprocess.Popen(
                [sys.executable, 'scripts/player', '-l', log_file, config_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Give it time to start and create log
            time.sleep(0.5)
            
            # Check if log file was created
            assert os.path.exists(log_file)
            
            # Check log content
            with open(log_file, 'r') as f:
                log_content = f.read()
                assert 'Player started' in log_content or 'Player listening' in log_content
            
            proc.terminate()
            proc.wait()
            
        finally:
            os.unlink(config_file)
            if os.path.exists(log_file):
                os.unlink(log_file)
    
    def test_verbose_option(self):
        """Test -v/--verbose enables debug output."""
        config_file = self.create_test_config(port=17300)
        
        try:
            # Start player with verbose
            proc = subprocess.Popen(
                [sys.executable, 'scripts/player', '-v', config_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Give it time to start
            time.sleep(0.5)
            
            # Terminate and check output
            proc.terminate()
            stdout, stderr = proc.communicate()
            
            # Should have debug-level output
            output = stdout + stderr
            assert 'Player listening on' in output or 'DEBUG' in output
            
        finally:
            os.unlink(config_file)
    
    def test_quiet_option(self):
        """Test -q/--quiet suppresses output."""
        config_file = self.create_test_config(port=17400)
        
        try:
            # Start player with quiet
            proc = subprocess.Popen(
                [sys.executable, 'scripts/player', '-q', config_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Give it time to start
            time.sleep(0.5)
            
            # Terminate and check output
            proc.terminate()
            stdout, stderr = proc.communicate()
            
            # Should have minimal output
            assert len(stdout) < 100  # Very little output
            
        finally:
            os.unlink(config_file)


class TestPlayerCLISignalHandling:
    """Test player signal handling."""
    
    def test_ctrl_c_handling(self):
        """Test that player handles Ctrl+C gracefully."""
        config_file = TestPlayerCLIOptions().create_test_config(port=17500)
        
        try:
            # Start player
            proc = subprocess.Popen(
                [sys.executable, 'scripts/player', config_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Give it time to start
            time.sleep(0.5)
            
            # Send interrupt signal (like Ctrl+C)
            proc.send_signal(subprocess.signal.SIGINT)
            
            # Wait for it to exit
            proc.wait(timeout=2)
            
            # Should exit cleanly with code 0
            assert proc.returncode == 0
            
        finally:
            os.unlink(config_file)
    
    def test_port_already_in_use(self):
        """Test error when port is already in use."""
        config_file = TestPlayerCLIOptions().create_test_config(port=17600)
        
        # Create a socket to block the port
        blocking_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        blocking_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        blocking_socket.bind(('127.0.0.1', 17600))
        blocking_socket.listen(1)
        
        try:
            # Try to start player on same port
            result = subprocess.run(
                [sys.executable, 'scripts/player', config_file],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            assert result.returncode == 1
            assert 'Failed to bind' in result.stderr or 'Address already in use' in result.stderr
            
        finally:
            blocking_socket.close()
            os.unlink(config_file)