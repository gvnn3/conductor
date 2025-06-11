# Conductor - A system for testing distributed systems across a network #

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-BSD-green.svg)](LICENSE)

Many test frameworks exist to test code on a single host or, across a
network, on a single server.  Conductor is a distributed system test
framework, written in Python, that can be used to coordinate a set of
tests among a set of clients.  The Conductor system allows a single
machine to control several systems, orchestrating tests that require
the cooperation of several networked devices.

## Features ##

- **Distributed Testing**: Coordinate tests across multiple networked machines
- **JSON Protocol**: Plain text protocol (NO ENCRYPTION) replacing insecure pickle
- **Phase-based Execution**: Startup → Run → Collect → Reset workflow
- **Parallel & Sequential Control**: Run steps in parallel or sequence as needed
- **Command Types**: Normal, spawn (background), and timeout commands
- **Rich CLI**: Modern command-line interface with helpful options
- **Multiple Output Formats**: Text (human-readable) and JSON (machine-parseable)
- **Flexible Configuration**: INI-based configuration with override options
- **Comprehensive Logging**: Verbose mode, quiet mode, and file logging
- **Test Isolation**: Each trial starts fresh with setup/teardown phases

## Requirements ##

- Python 3.8 or higher
- pip (for installation)
- Network connectivity between conductor and players

## Security ##

⚠️ **IMPORTANT SECURITY WARNING** ⚠️

**DO NOT USE CONDUCTOR OVER THE INTERNET**

- **NO ENCRYPTION**: All network communications are sent in PLAIN TEXT
- **NO AUTHENTICATION**: There is NO authentication mechanism - anyone who can connect can control the system
- **PRIVATE NETWORKS ONLY**: This tool is designed for use in isolated test labs on private networks
- **FIREWALL REQUIRED**: Always use behind a properly configured firewall

### Design Security Features

While not suitable for internet use, Conductor does include some security improvements over its predecessor:

- **No Arbitrary Code Execution**: JSON protocol cannot execute code, unlike the previous pickle-based implementation
- **Protocol Versioning**: Ensures compatibility across versions
- **Message Size Limits**: 10MB maximum to prevent DoS attacks
- **Human-Readable Format**: Easier to debug and audit communications

## Documentation ##

- **[Quick Start Guide](docs/QUICK_START.md)** - Get running in 5 minutes
- **[Installation Guide](docs/INSTALLATION_GUIDE.md)** - Detailed setup instructions
- **[CLI Reference](docs/CLI_REFERENCE.md)** - Command-line options and examples
- **[Architecture Overview](docs/ARCHITECTURE.md)** - System internals
- **[Changelog](docs/CHANGELOG.md)** - Version history and updates
- **[Example Configurations](examples/)** - Real-world test examples

## Installation ##

```bash
# Clone the repository
git clone https://github.com/benroeder/conductor.git
cd conductor

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install using pip (modern method)
pip install .

# Or install in development mode
pip install -e .
```

For detailed installation instructions, see the [Installation Guide](docs/INSTALLATION_GUIDE.md).

## Quick Start ##

### Basic Usage

Start a player on each test node:
```bash
player --help  # See all options
player -v config.cfg  # Verbose mode
```

Run conductor to orchestrate tests:
```bash
conduct --help  # See all options
conduct -t 3 test.cfg  # Run 3 trials
```

### New CLI Features

**Conductor Options:**
- `--trials N` - Override number of trials
- `--phases [startup|run|collect|reset]` - Run specific phases only
- `--clients CLIENT1 CLIENT2` - Test specific clients
- `--dry-run` - Preview what would be executed
- `--verbose/-v` - Enable debug logging
- `--quiet/-q` - Suppress non-error output

**Player Options:**
- `--bind ADDRESS` - Bind to specific interface
- `--port PORT` - Override port from config
- `--log-file FILE` - Log to file
- `--verbose/-v` - Enable debug logging

### Example: Run specific phases with verbose output

```bash
# Terminal 1: Start player with logging
player -v --log-file player.log config.cfg

# Terminal 2: Run only startup and reset phases
conduct -v --phases startup reset test.cfg
```

### Example: Test single client with dry-run

```bash
# See what would be executed without running
conduct --dry-run --clients web_server test.cfg
```

## Simple localhost test ##

To familiarize yourself with the system, try the localhost test:

Terminal 1:
```bash
cd tests/localhost
player dut.cfg
```

Terminal 2:
```bash
cd tests/localhost  
conduct conductor.cfg
```

You *MUST* always start all players before the conductor.

The output of the conductor should look like this:

```
0 phase received
running
0 b'startup\n'
done
0 phase received
running
0 b'running\n'
0 b'PING 127.0.0.1 (127.0.0.1): 56 data bytes\n64 bytes from 127.0.0.1: icmp_seq=0 ttl=64 time=0.046 ms\n64 bytes from 127.0.0.1: icmp_seq=1 ttl=64 time=0.162 ms\n64 bytes from 127.0.0.1: icmp_seq=2 ttl=64 time=0.143 ms\n\n--- 127.0.0.1 ping statistics ---\n3 packets transmitted, 3 packets received, 0.0% packet loss\nround-trip min/avg/max/stddev = 0.046/0.117/0.162/0.051 ms\n'
done
0 phase received
running
0 b'collecting\n'
done
0 phase received
running
0 b'collecting\n'
done
```

Once the test is complete the conduct script will exit and return the
caller back to the shell prompt.  The player will continue to await
commands from another run of the conduct script.

## How It Works ##

### Overview

Conductor orchestrates distributed tests across multiple networked systems:

- **Conductor**: Central coordinator that controls the test
- **Players**: Test nodes that execute commands

Common use case: Testing network devices (routers, firewalls) with multiple traffic generators and receivers.

### Test Phases

Tests execute in four sequential phases:

1. **Startup** - Configure test environment
   - Set up network interfaces
   - Configure routing tables
   - Create result directories

2. **Run** - Execute the main test
   - Start traffic generators
   - Launch monitoring tools
   - Run test workloads

3. **Collect** - Gather results
   - Retrieve log files
   - Copy test data to conductor
   - Save performance metrics

4. **Reset** - Clean up
   - Restore original configuration
   - Clean temporary files
   - Return to pre-test state

### Execution Model

Each phase executes in three steps:

1. **Download** - Conductor sends the phase to all players
2. **Acknowledge** - Players confirm receipt and readiness
3. **Execute** - Conductor triggers simultaneous execution

This approach minimizes timing skew between players, though some small delay exists due to sequential communication.

### Command Execution

Commands within a phase run sequentially on each player. Use special prefixes to control execution behavior:

**spawn:** - Run command in background without waiting
```bash
spawn:iperf3 -s                    # Start server, continue immediately
spawn:tcpdump -w capture.pcap      # Start capture in background
```
Use for: Long-running processes, traffic generators, monitoring tools

**timeout<N>:** - Kill command after N seconds
```bash
timeout10:ping -c 1000 target      # Stop ping after 10 seconds
timeout30:./long_test.sh           # Limit test to 30 seconds
```
Use for: Commands that might hang, tests with time limits, safety boundaries

## Contributing

We welcome contributions to Conductor! Please see our [Contributing Guide](docs/CONTRIBUTING.md) for:

- Development setup and workflow
- Comprehensive testing procedures
- Code quality standards
- Architecture overview
- Common development tasks

For quick testing, see [Quick Start Guide](docs/QUICK_START.md) and [Installation Guide](docs/INSTALLATION_GUIDE.md).

