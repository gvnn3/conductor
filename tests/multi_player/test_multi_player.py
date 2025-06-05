#!/usr/bin/env python3
"""
Multi-player end-to-end test for Conductor framework.
Tests with 2-10 players running concurrently.
"""

import os
import sys
import time
import subprocess
import tempfile
import signal
import socket
from contextlib import contextmanager


def find_free_port():
    """Find a free port to use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def get_venv_python():
    """Get the correct Python executable from venv."""
    import os
    import sys
    # Look for venv in the conductor project root
    for i in range(4):  # Try up to 4 parent directories
        venv_path = os.path.join(os.path.dirname(__file__), *(['..'] * i), 'venv', 'bin', 'python')
        if os.path.exists(venv_path):
            return venv_path
    # Fallback to current interpreter
    return sys.executable

def create_player_config(player_id, cmd_port, results_port):
    """Create a player configuration file."""
    config = f"""[Coordinator]
player = 127.0.0.1
conductor = 127.0.0.1
cmdport = {cmd_port}
resultsport = {results_port}

[Startup]
step1 = echo "Player {player_id} starting up"
step2 = hostname

[Run]
step1 = echo "Player {player_id} running tests"
step2 = echo "Player {player_id} was here" > /tmp/player_{player_id}_test.txt
step3 = ping -c 1 localhost
step4 = python -c "import time; print('Player {player_id} working...'); time.sleep(0.5)"
step5 = echo "Player {player_id} test complete"
spawn1 = bash -c "sleep 0.1 && echo 'Player {player_id} spawn process ran at $(date)' > /tmp/player_{player_id}_spawn.txt"

[Collect]
step1 = echo "Player {player_id} collecting results"
step2 = cat /tmp/player_{player_id}_test.txt
step3 = ls -la /tmp/player_{player_id}_spawn.txt 2>/dev/null || echo "No spawn file yet"
step4 = cat /tmp/player_{player_id}_spawn.txt 2>/dev/null || echo "No spawn content yet"

[Reset]
step1 = echo "Player {player_id} resetting"
step2 = rm -f /tmp/player_{player_id}_test.txt /tmp/player_{player_id}_spawn.txt
"""
    return config


def create_conductor_config(num_players, player_configs):
    """Create conductor configuration for multiple players."""
    workers_section = "\n".join([f"player{i} = {cfg}" for i, cfg in enumerate(player_configs, 1)])
    
    config = f"""[Test]
trials = 2

[Workers]
{workers_section}
"""
    return config


@contextmanager
def player_process(config_file, player_id):
    """Context manager to start and stop a player process."""
    print(f"Starting player {player_id}...")
    cmd = [get_venv_python(), "-m", "conductor.scripts.player", config_file]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Give player time to start
    time.sleep(1)
    
    try:
        yield proc
    finally:
        print(f"Stopping player {player_id}...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def run_multi_player_test(num_players):
    """Run end-to-end test with specified number of players."""
    print(f"\n{'='*60}")
    print(f"Running test with {num_players} players")
    print(f"{'='*60}\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create player configurations
        player_configs = []
        player_procs = []
        
        for i in range(1, num_players + 1):
            cmd_port = find_free_port()
            results_port = find_free_port()
            
            # Create player config file
            config_file = os.path.join(tmpdir, f"player{i}.cfg")
            with open(config_file, 'w') as f:
                f.write(create_player_config(i, cmd_port, results_port))
            
            player_configs.append(config_file)
            
            # Start player process
            print(f"Starting player {i} on ports {cmd_port}/{results_port}")
            cmd = [get_venv_python(), "-m", "conductor.scripts.player", config_file]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            player_procs.append(proc)
        
        # Give all players time to start
        print(f"Waiting for all {num_players} players to start...")
        time.sleep(2)
        
        # Create conductor config
        conductor_config = os.path.join(tmpdir, "conductor.cfg")
        with open(conductor_config, 'w') as f:
            f.write(create_conductor_config(num_players, player_configs))
        
        # Run conductor
        print(f"\nRunning conductor with {num_players} players...")
        conductor_cmd = [get_venv_python(), "-m", "conductor.scripts.conduct", conductor_config]
        
        start_time = time.time()
        result = subprocess.run(conductor_cmd, capture_output=True, text=True)
        end_time = time.time()
        
        print(f"\nConductor completed in {end_time - start_time:.2f} seconds")
        print(f"Return code: {result.returncode}")
        
        if result.returncode == 0:
            print("✅ SUCCESS")
        else:
            print("❌ FAILED")
            # Show output only on failure
            print("\nConductor Output:")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        
        # Wait a bit for spawn commands to complete
        print(f"\nWaiting for spawn files...")
        time.sleep(1.5)
        
        # Check for spawn files
        print(f"Checking spawn files...")
        for i in range(1, num_players + 1):
            spawn_file = f"/tmp/player_{i}_spawn.txt"
            if os.path.exists(spawn_file):
                with open(spawn_file, 'r') as f:
                    content = f.read().strip()
                print(f"  Player {i} spawn file: {content if content else 'EMPTY'}")
                os.unlink(spawn_file)
            else:
                print(f"  Player {i} spawn file: NOT FOUND")
        
        # Stop all players
        print(f"\nStopping all players...")
        for i, proc in enumerate(player_procs, 1):
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"  Player {i} didn't stop gracefully, killing...")
                proc.kill()
                proc.wait()
        
        print(f"\nTest with {num_players} players complete!")
        return result.returncode == 0


def main():
    """Run multi-player tests with 2-10 players."""
    print("Multi-Player End-to-End Tests")
    print("="*60)
    
    # Test with different numbers of players
    test_sizes = [2, 3, 5, 10]
    results = {}
    
    for num_players in test_sizes:
        success = run_multi_player_test(num_players)
        results[num_players] = success
        
        # Small delay between tests
        time.sleep(2)
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for num_players, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{num_players} players: {status}")
    
    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 All multi-player tests PASSED!")
        return 0
    else:
        print("\n❌ Some multi-player tests FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(main())