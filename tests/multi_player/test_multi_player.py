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
step1 = echo "=== PLAYER {player_id} STARTUP PHASE ==="
step2 = echo "Player {player_id} starting up on $(hostname)"
step3 = date

[Run]
step1 = echo "=== PLAYER {player_id} RUN PHASE ==="
step2 = echo "Player {player_id} executing test steps..."
step3 = echo "Player {player_id} was here at $(date)" > /tmp/player_{player_id}_test.txt
step4 = echo "Creating test file: SUCCESS"
step5 = echo "Player {player_id} pinging localhost..."
step6 = ping -c 2 localhost
step7 = python -c "import time; print('Player {player_id} processing for 0.5 seconds...'); time.sleep(0.5); print('Player {player_id} processing complete!')"
step8 = echo "Player {player_id} launching background spawn process..."
spawn1 = bash -c "echo 'Player {player_id} spawn process ran at $(date)' > /tmp/player_{player_id}_spawn.txt"
step9 = sleep 1
step10 = echo "Player {player_id} RUN PHASE COMPLETE"

[Collect]
step1 = echo "=== PLAYER {player_id} COLLECT PHASE ==="
step2 = echo "Player {player_id} collecting results..."
step3 = echo "Test file contents:"
step4 = cat /tmp/player_{player_id}_test.txt
step5 = echo "Spawn file status:"
step6 = ls -la /tmp/player_{player_id}_spawn.txt 2>/dev/null || echo "No spawn file found"
step7 = echo "Spawn file contents:"
step8 = cat /tmp/player_{player_id}_spawn.txt 2>/dev/null || echo "No spawn content found"
step9 = echo "Player {player_id} COLLECT PHASE COMPLETE"

[Reset]
step1 = echo "=== PLAYER {player_id} RESET PHASE ==="
step2 = echo "Player {player_id} cleaning up..."
step3 = rm -f /tmp/player_{player_id}_test.txt
step4 = echo "Player {player_id} RESET PHASE COMPLETE"
"""
    return config


def create_conductor_config(num_players, player_configs):
    """Create conductor configuration for multiple players."""
    workers_section = "\n".join([f"player{i} = {cfg}" for i, cfg in enumerate(player_configs, 1)])
    
    config = f"""[Test]
trials = 1

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
            # Show conductor's collected output
            print("\n" + "="*60)
            print("CONDUCTOR COLLECTED OUTPUT:")
            print("="*60)
            print(result.stdout)
            print("="*60 + "\n")
        else:
            print("❌ FAILED")
            # Show output only on failure
            print("\nConductor Output:")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        
        # Wait a bit for spawn commands to complete
        print(f"\nWaiting for spawn files...")
        time.sleep(3.0)  # Increased wait time for spawn processes
        
        # Check for spawn files
        print(f"Checking spawn files...")
        spawn_files_found = 0
        for i in range(1, num_players + 1):
            spawn_file = f"/tmp/player_{i}_spawn.txt"
            if os.path.exists(spawn_file):
                with open(spawn_file, 'r') as f:
                    content = f.read().strip()
                print(f"  Player {i} spawn file: {content if content else 'EMPTY'}")
                os.unlink(spawn_file)
                spawn_files_found += 1
            else:
                print(f"  Player {i} spawn file: NOT FOUND")
        
        # Clean up any remaining test files
        for i in range(1, num_players + 1):
            test_file = f"/tmp/player_{i}_test.txt"
            if os.path.exists(test_file):
                os.unlink(test_file)
        
        # Stop all players and collect output
        print(f"\nStopping all players and collecting output...")
        for i, proc in enumerate(player_procs, 1):
            proc.terminate()
            try:
                stdout, stderr = proc.communicate(timeout=5)
                # For tests with many players, show condensed output
                if num_players > 3:
                    print(f"\n=== Player {i} Summary ===")
                    stdout_text = stdout.decode('utf-8', errors='replace')
                    # Extract key lines showing phases completed
                    phase_lines = [line for line in stdout_text.split('\n') 
                                 if 'PHASE' in line or 'SUCCESS' in line or 'spawn process ran' in line]
                    if phase_lines:
                        print("Key outputs:")
                        for line in phase_lines[:10]:  # Show first 10 key lines
                            print(f"  {line.strip()}")
                    
                    # Check for errors in stderr
                    stderr_text = stderr.decode('utf-8', errors='replace')
                    error_lines = [line for line in stderr_text.split('\n') if 'ERROR' in line or 'Exception' in line]
                    if error_lines:
                        print("ERRORS found:")
                        for line in error_lines:
                            print(f"  {line}")
                    else:
                        print("  No errors - player completed successfully")
                else:
                    # For small tests, show full output
                    print(f"\n=== Player {i} Output ===")
                    if stdout:
                        print("STDOUT:")
                        print(stdout.decode('utf-8', errors='replace'))
                    if stderr:
                        print("STDERR:")
                        print(stderr.decode('utf-8', errors='replace'))
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