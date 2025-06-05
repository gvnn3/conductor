# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Setup and Installation
```bash
# Create/activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install conductor with development dependencies
pip install -e ".[dev]"

# This installs:
# - conductor package in editable mode
# - configparser (required dependency)
# - pytest, pytest-cov, pytest-mock, hypothesis (dev dependencies)
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
- TCP sockets using secure JSON protocol (replaced pickle)
- Length-prefixed messages (4-byte header + JSON data)
- Protocol version 1 with validation
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

- **Framework**: pytest with hypothesis for property-based testing
- **Current State**: Comprehensive test suite with edge case testing
- **Unit Tests**: Full coverage for core modules with hypothesis tests
- **Integration Tests**: Example tests exist in `tests/localhost/` and `tests/timeout/`
- **Edge Case Tests**: Hypothesis-based tests for `json_protocol.py`, `step.py`, `phase.py`, `client.py`, `config.py`, and `retval.py`

### Test Coverage
- `json_protocol.py`: 98% coverage with edge case handling
- `step.py`: 100% coverage including binary output handling
- `phase.py`: Good coverage with parallel execution tests
- `client.py`: 54% coverage with port validation and command parsing
- `config.py`: 100% coverage (simple data holder)
- `retval.py`: 81% coverage with serialization safety

### Key Improvements Made
1. **JSON Protocol**: Replaced insecure pickle with JSON, added version field
2. **Edge Case Handling**: Fixed bugs found through hypothesis testing
3. **Binary Output**: Step execution now handles non-UTF-8 output
4. **Serialization Safety**: RetVal handles non-serializable objects
5. **Port Validation**: Client validates port numbers
6. **Modern Build**: Replaced setup.py with pyproject.toml