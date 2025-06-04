# Conductor Setup Notes

## Overview
Conductor is a distributed systems test framework that orchestrates tests across multiple clients (players) from a central controller (conductor).

## Setup Process

1. **Create Python Virtual Environment**
   ```bash
   python3 -m venv venv
   ```

2. **Install Conductor** (dependencies are handled automatically)
   ```bash
   venv/bin/pip install .
   # Or for development:
   venv/bin/pip install -e .
   ```

## Issues Encountered and Solutions

1. **Missing Shebang Lines**: The original scripts (`conduct` and `player`) were missing shebang lines, causing them to be incorrectly interpreted by the shell. Fixed by adding `#!/usr/bin/env python3` to both scripts.

2. **Working Directory**: The conductor expects configuration files to be in the current directory. When running tests, you need to either:
   - Run from the test directory
   - Use full paths to configuration files

## Running Tests

To test the setup, use the provided test script:
```bash
./test_conductor.sh
```

Or manually:
1. Open two terminals
2. Terminal 1 (Player): `cd tests/localhost && ../../venv/bin/player dut.cfg`
3. Terminal 2 (Conductor): `cd tests/localhost && ../../venv/bin/conduct conductor.cfg`

## Test Output
The localhost test successfully:
- Started a player listening on port 6970
- Connected the conductor to the player
- Executed all four phases (Startup, Run, Collect, Reset)
- Ran a ping command as part of the test
- Properly cleaned up after completion

## Architecture
- **Players**: Run on test machines, execute commands sent by conductor
- **Conductor**: Orchestrates tests, sends commands to players
- **Phases**: Tests are organized in 4 phases:
  - Startup: Initialize test environment
  - Run: Execute test commands (in parallel)
  - Collect: Gather results
  - Reset: Clean up test environment