"""Test error handling for network failures in conductor/player."""

import pytest
import subprocess
import socket
import time
import tempfile
import os
import sys
from unittest.mock import patch, MagicMock
import threading


class TestNetworkErrorHandling:
    """Test how conductor and player handle network errors."""

    def create_test_configs(self, port=20970):
        """Create temporary test configurations."""
        test_dir = tempfile.mkdtemp()

        # Master config
        coordinator_config = os.path.join(test_dir, "coordinator.cfg")

        # Client config
        client_config = os.path.join(test_dir, "client.cfg")
        with open(client_config, "w") as f:
            f.write(f"""[Coordinator]
player = 127.0.0.1
conductor = 127.0.0.1
cmdport = {port}
resultsport = {port + 1}

[Startup]
step1 = echo "test"

[Run]
step1 = echo "test"

[Collect]
step1 = echo "test"

[Reset]
step1 = echo "test"
""")

        with open(coordinator_config, "w") as f:
            f.write(f"""[Test]
trials = 1

[Clients]
test_client = {client_config}
""")

        return coordinator_config, client_config, test_dir

    def test_conductor_handles_no_player_running(self):
        """Test conductor behavior when no player is running."""
        coordinator_config, client_config, test_dir = self.create_test_configs(21000)

        try:
            # Run conductor without starting player
            result = subprocess.run(
                [sys.executable, "scripts/conduct", coordinator_config],
                capture_output=True,
                text=True,
                timeout=5,
            )

            # Should show connection error
            output = result.stdout + result.stderr
            assert "Failed to connect" in output
            # Note: Current implementation exits with 0, which could be improved

        finally:
            import shutil

            shutil.rmtree(test_dir)

    def test_player_handles_invalid_conductor_address(self):
        """Test player behavior with invalid conductor address."""
        # Create config with invalid conductor address
        test_dir = tempfile.mkdtemp()
        client_config = os.path.join(test_dir, "client.cfg")

        with open(client_config, "w") as f:
            f.write("""[Coordinator]
player = 127.0.0.1
conductor = 999.999.999.999
cmdport = 21100
resultsport = 21101

[Startup]
step1 = echo "test"
""")

        try:
            # Start player - should start successfully even with bad conductor
            player_proc = subprocess.Popen(
                [sys.executable, "scripts/player", client_config],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Give it time to start
            time.sleep(0.5)

            # Player should be running
            assert player_proc.poll() is None  # Still running

            # Cleanup
            player_proc.terminate()
            player_proc.wait()

        finally:
            import shutil

            shutil.rmtree(test_dir)

    def test_conductor_timeout_waiting_for_results(self):
        """Test conductor handling timeout waiting for results."""
        from conductor.client import Client
        import configparser

        # Create a mock phase that doesn't send results properly
        config = configparser.ConfigParser()
        config["Coordinator"] = {
            "conductor": "127.0.0.1",
            "player": "127.0.0.1",
            "cmdport": "21200",
            "resultsport": "21201",
        }
        config["Startup"] = {}
        config["Run"] = {}
        config["Collect"] = {}
        config["Reset"] = {}

        client = Client(config)

        # Mock socket operations
        with patch("socket.create_connection") as mock_create:
            mock_sock = MagicMock()
            mock_create.return_value = mock_sock

            # Test download phase
            try:
                client.download(client.startup_phase)
            except SystemExit:
                # Expected when connection fails
                pass

            # Verify connection was attempted
            mock_create.assert_called_with(("127.0.0.1", 21200))

    def test_player_handles_malformed_messages(self):
        """Test player handling of malformed pickle messages."""
        from scripts.player import Player

        # Create player
        player = Player("127.0.0.1", 21300)

        # Create mock socket with malformed data
        mock_sock = MagicMock()
        mock_addr = ("127.0.0.1", 12345)

        # Simulate bad pickle data
        mock_sock.recv.return_value = b"This is not valid pickle data"

        # Mock accept to return our mock socket once then timeout
        player.cmdsock.accept = MagicMock(
            side_effect=[(mock_sock, mock_addr), socket.timeout()]
        )
        player.cmdsock.settimeout = MagicMock()

        # Set done after one iteration
        def set_done(*args):
            player.done = True

        mock_sock.close.side_effect = set_done

        # Run should handle the error gracefully
        player.run()

        # Should have tried to close the socket
        mock_sock.close.assert_called()

    def test_conductor_handles_player_disconnect_mid_test(self):
        """Test conductor behavior when player disconnects during test."""
        coordinator_config, client_config, test_dir = self.create_test_configs(21400)

        try:
            # Start player
            player_proc = subprocess.Popen(
                [sys.executable, "scripts/player", client_config],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Wait for player to start
            time.sleep(0.5)

            # Start conductor in thread
            conductor_result = {"returncode": None, "output": ""}

            def run_conductor():
                result = subprocess.run(
                    [sys.executable, "scripts/conduct", coordinator_config],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                conductor_result["returncode"] = result.returncode
                conductor_result["output"] = result.stdout + result.stderr

            conductor_thread = threading.Thread(target=run_conductor)
            conductor_thread.start()

            # Kill player after conductor starts
            time.sleep(1)
            player_proc.terminate()
            player_proc.wait()

            # Wait for conductor to finish
            conductor_thread.join(timeout=5)

            # Conductor should have failed
            assert conductor_result["returncode"] != 0

        finally:
            import shutil

            shutil.rmtree(test_dir)

    @pytest.mark.slow
    def test_player_recovers_from_conductor_crash(self):
        """Test that player continues running after conductor crashes."""
        coordinator_config, client_config, test_dir = self.create_test_configs(21500)

        try:
            # Start player
            player_proc = subprocess.Popen(
                [sys.executable, "scripts/player", "-v", client_config],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Wait for player to start
            time.sleep(0.5)

            # Verify player is running
            assert player_proc.poll() is None

            # Simulate conductor connecting and disconnecting
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("127.0.0.1", 21500))
            sock.close()

            # Give player time to handle disconnection
            time.sleep(0.5)

            # Player should still be running
            assert player_proc.poll() is None

            # Can connect again
            sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock2.connect(("127.0.0.1", 21500))
            sock2.close()

            # Cleanup
            player_proc.terminate()
            player_proc.wait()

        finally:
            import shutil

            shutil.rmtree(test_dir)

    def test_results_port_unavailable(self):
        """Test conductor behavior when results port is blocked."""
        coordinator_config, client_config, test_dir = self.create_test_configs(21600)

        # Block the results port
        blocking_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        blocking_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            blocking_socket.bind(("0.0.0.0", 21601))  # Results port
            blocking_socket.listen(1)

            # Start player
            player_proc = subprocess.Popen(
                [sys.executable, "scripts/player", client_config],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Wait for player
            time.sleep(0.5)

            try:
                # Run conductor - should fail to bind results port
                result = subprocess.run(
                    [sys.executable, "scripts/conduct", coordinator_config],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                # Should fail
                assert result.returncode != 0

            finally:
                player_proc.terminate()
                player_proc.wait()

        finally:
            blocking_socket.close()
            import shutil

            shutil.rmtree(test_dir)
