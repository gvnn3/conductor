"""Integration tests for conduct/player CLI with real network communication."""

import pytest
import subprocess
import os
import tempfile
import time
import socket
import sys
import signal


class TestCLIIntegration:
    """Test real conductor/player interaction with new CLI options."""

    @pytest.fixture
    def test_configs(self):
        """Create test configuration files."""
        # Create temp directory for configs
        test_dir = tempfile.mkdtemp()

        # Master config
        master_config = os.path.join(test_dir, "master.cfg")
        with open(master_config, "w") as f:
            f.write("""[Test]
trials = 1

[Workers]
test_worker = {client_config}
""")

        # Client config
        client_config = os.path.join(test_dir, "client.cfg")
        with open(client_config, "w") as f:
            f.write("""[Coordinator]
player = 127.0.0.1
conductor = 127.0.0.1
cmdport = 18970
resultsport = 18971

[Startup]
step1 = echo "Integration test startup"

[Run]
step1 = echo "Integration test running"
step2 = echo "Test output"

[Collect]
step1 = echo "Integration test collect"

[Reset]
step1 = echo "Integration test reset"
""")

        # Update coordinator config with client path
        with open(master_config, "w") as f:
            f.write(f"""[Test]
trials = 1

[Workers]
test_worker = {client_config}
""")

        yield master_config, client_config, test_dir

        # Cleanup
        import shutil

        shutil.rmtree(test_dir)

    def wait_for_port(self, port, timeout=5):
        """Wait for a port to be open."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(("127.0.0.1", port))
                sock.close()
                if result == 0:
                    return True
            except Exception:
                pass
            time.sleep(0.1)
        return False

    @pytest.mark.slow
    def test_conduct_player_basic_interaction(self, test_configs):
        """Test basic conductor/player interaction."""
        master_config, client_config, test_dir = test_configs

        # Start player
        player_proc = subprocess.Popen(
            [sys.executable, "scripts/player", "-v", client_config],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            # Wait for player to start
            assert self.wait_for_port(18970), "Player did not start in time"

            # Run conductor
            conduct_result = subprocess.run(
                [sys.executable, "scripts/conduct", "-v", master_config],
                capture_output=True,
                text=True,
                timeout=10,
            )

            # Check conductor completed successfully
            assert conduct_result.returncode == 0
            output = conduct_result.stdout + conduct_result.stderr

            # Verify all phases ran
            assert "Starting trial 1 of 1" in output
            assert "Downloading startup phase" in output
            assert "Downloading run phase" in output
            assert "Downloading collect phase" in output
            assert "Downloading reset phase" in output
            assert "All trials completed successfully" in output

        finally:
            # Stop player
            player_proc.terminate()
            player_proc.wait(timeout=2)

    @pytest.mark.slow
    def test_conduct_with_phase_selection(self, test_configs):
        """Test conductor with specific phases only."""
        master_config, client_config, test_dir = test_configs

        # Start player
        player_proc = subprocess.Popen(
            [sys.executable, "scripts/player", client_config],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            # Wait for player to start
            assert self.wait_for_port(18970), "Player did not start in time"

            # Run conductor with only startup and reset phases
            conduct_result = subprocess.run(
                [
                    sys.executable,
                    "scripts/conduct",
                    "-p",
                    "startup",
                    "reset",
                    "--",
                    master_config,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            # Check conductor completed successfully
            assert conduct_result.returncode == 0
            output = conduct_result.stdout + conduct_result.stderr

            # Verify only selected phases ran
            assert "startup" in output
            assert "reset" in output
            # Run and collect should not be present
            assert "Downloading run phase" not in output
            assert "Downloading collect phase" not in output

        finally:
            # Stop player
            player_proc.terminate()
            player_proc.wait(timeout=2)

    @pytest.mark.slow
    def test_conduct_with_multiple_trials(self, test_configs):
        """Test conductor with multiple trials."""
        master_config, client_config, test_dir = test_configs

        # Start player
        player_proc = subprocess.Popen(
            [sys.executable, "scripts/player", client_config],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            # Wait for player to start
            assert self.wait_for_port(18970), "Player did not start in time"

            # Run conductor with 3 trials
            conduct_result = subprocess.run(
                [sys.executable, "scripts/conduct", "-t", "3", master_config],
                capture_output=True,
                text=True,
                timeout=20,
            )

            # Check conductor completed successfully
            assert conduct_result.returncode == 0
            output = conduct_result.stdout + conduct_result.stderr

            # Verify all 3 trials ran
            assert "Starting trial 1 of 3" in output
            assert "Starting trial 2 of 3" in output
            assert "Starting trial 3 of 3" in output
            assert "Completed trial 3 of 3" in output

        finally:
            # Stop player
            player_proc.terminate()
            player_proc.wait(timeout=2)

    @pytest.mark.slow
    def test_player_with_custom_port(self, test_configs):
        """Test player with custom port override."""
        master_config, client_config, test_dir = test_configs

        # Create modified client config for conductor to use custom port
        custom_client_config = os.path.join(test_dir, "custom_client.cfg")
        with open(custom_client_config, "w") as f:
            f.write("""[Coordinator]
player = 127.0.0.1
conductor = 127.0.0.1
cmdport = 19970
resultsport = 19971

[Startup]
step1 = echo "Custom port test"

[Run]
step1 = echo "Running on custom port"

[Collect]
step1 = echo "Collect"

[Reset]
step1 = echo "Reset"
""")

        # Update coordinator config
        custom_master_config = os.path.join(test_dir, "custom_master.cfg")
        with open(custom_master_config, "w") as f:
            f.write(f"""[Test]
trials = 1

[Workers]
test_worker = {custom_client_config}
""")

        # Start player with custom port override
        player_proc = subprocess.Popen(
            [sys.executable, "scripts/player", "-p", "19970", client_config],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            # Wait for player to start on custom port
            assert self.wait_for_port(19970), "Player did not start on custom port"

            # Run conductor
            conduct_result = subprocess.run(
                [sys.executable, "scripts/conduct", custom_master_config],
                capture_output=True,
                text=True,
                timeout=10,
            )

            # Check conductor completed successfully
            assert conduct_result.returncode == 0

        finally:
            # Stop player
            player_proc.terminate()
            player_proc.wait(timeout=2)

    @pytest.mark.slow
    def test_player_graceful_shutdown(self, test_configs):
        """Test player handles signals gracefully."""
        master_config, client_config, test_dir = test_configs

        # Start player
        player_proc = subprocess.Popen(
            [sys.executable, "scripts/player", "-v", client_config],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            # Wait for player to start
            assert self.wait_for_port(18970), "Player did not start in time"

            # Send SIGINT (like Ctrl+C)
            player_proc.send_signal(signal.SIGINT)

            # Wait for graceful shutdown
            player_proc.wait(timeout=2)

            # Check it exited cleanly
            assert player_proc.returncode == 0

            # Check output for graceful shutdown
            output = player_proc.stdout.read() + player_proc.stderr.read()
            assert "Shutting down player" in output or "interrupt" in output.lower()

        except subprocess.TimeoutExpired:
            player_proc.kill()
            pytest.fail("Player did not shutdown gracefully")

    @pytest.mark.slow
    def test_conduct_dry_run_does_not_connect(self, test_configs):
        """Test that --dry-run doesn't actually connect to players."""
        master_config, client_config, test_dir = test_configs

        # Don't start any player

        # Run conductor with dry-run
        conduct_result = subprocess.run(
            [sys.executable, "scripts/conduct", "--dry-run", master_config],
            capture_output=True,
            text=True,
            timeout=5,
        )

        # Should succeed without connecting
        assert conduct_result.returncode == 0
        output = conduct_result.stdout + conduct_result.stderr

        assert "DRY RUN MODE" in output
        assert "Would run 1 trial(s)" in output
        # Should not have any connection errors
        assert "Failed to connect" not in output
