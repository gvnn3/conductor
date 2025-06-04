# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Setup and Installation
```bash
# Create/activate virtual environment
python3 -m venv venv

# Install dependencies
venv/bin/pip install setuptools configparser pytest pytest-cov pytest-mock

# Install conductor in development mode
venv/bin/python setup.py install
```

### Running Tests
```bash
# Run all tests with pytest
venv/bin/pytest

# Run with coverage
venv/bin/pytest --cov=conductor --cov-report=term-missing

# Run specific test categories
venv/bin/pytest -m unit
venv/bin/pytest -m integration

# Run the example integration test
./test_conductor.sh
```

### Manual Testing
```bash
# Terminal 1: Start a player
cd tests/localhost
../../venv/bin/player dut.cfg

# Terminal 2: Run conductor
cd tests/localhost
../../venv/bin/conduct conductor.cfg
```

## Architecture Overview

Conductor is a distributed testing framework following a coordinator-worker pattern:

- **Conductor (Coordinator)**: Orchestrates tests across multiple nodes
- **Player (Worker)**: Executes commands on remote systems

### Communication Protocol
- TCP sockets using Python's pickle protocol
- Length-prefixed messages (4-byte header + pickled object)
- Default ports: 6970 (commands), 6971 (results)

### Test Execution Flow
1. **Startup Phase**: Sequential initialization on all players
2. **Run Phase**: Parallel command execution (spawn/timeout modes supported)
3. **Collect Phase**: Sequential result gathering
4. **Reset Phase**: Sequential cleanup

### Key Classes
- `client.Client`: Manages player connections from conductor side
- `phase.Phase`: Container for test steps (one per test phase)
- `step.Step`: Individual command with execution modes (normal/spawn/timeout)
- `retval.RetVal`: Standardized communication protocol

### Step Execution Modes
- **Normal**: `command` - Waits for completion
- **Spawn**: `spawn:command` - Fire and forget
- **Timeout**: `timeout30:command` - Kill after N seconds

### Configuration Structure
Test configuration (`conductor.cfg`) defines trials and player list.
Player configuration (`*.cfg`) defines connection info and test steps for each phase.

## Testing Status

- **Framework**: pytest with coverage reporting configured
- **Current State**: No unit tests implemented yet (TDD approach documented but not started)
- **Integration Tests**: Example tests exist in `tests/localhost/` and `tests/timeout/`

When implementing tests, prioritize:
1. `step.py` - Complex subprocess handling
2. `client.py` - Core orchestration logic
3. `phase.py` - Step sequencing
4. `retval.py` - Communication protocol