# Conductor Installation and Setup Guide

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Server Setup (Conductor)](#server-setup-conductor)
5. [Client Setup (Player)](#client-setup-player)
6. [Network Configuration](#network-configuration)
7. [Running Your First Test](#running-your-first-test)
8. [Troubleshooting](#troubleshooting)

## Overview

Conductor is a distributed testing framework that follows a coordinator-worker pattern:
- **Conductor (Coordinator)**: Orchestrates tests across multiple nodes
- **Player (Worker)**: Executes commands on remote systems

```
┌─────────────┐
│  Conductor  │
│(Coordinator)│
└──────┬──────┘
       │ Commands (port 6970)
       │ Results (port 6971)
       │
┌──────┴──────┬──────────────┬──────────────┐
│   Player 1  │   Player 2   │   Player N   │
│  (Worker)   │  (Worker)    │  (Worker)    │
└─────────────┴──────────────┴──────────────┘
```

## Prerequisites

### System Requirements
- Python 3.8 or higher
- pip (Python package installer)
- Network connectivity between conductor and all players
- Open ports: 6970 (commands) and 6971 (results) by default

### Python Dependencies
The only required dependency is `configparser`, which will be installed automatically.

## Installation

### Method 1: From Source (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/benroeder/conductor.git
cd conductor
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install conductor:
```bash
# For regular use
pip install .

# For development (editable install)
pip install -e .
```

The installation will automatically handle all dependencies.

### Method 2: Install with Additional Development Tools

For development or testing:
```bash
# Install with development dependencies
pip install -e ".[dev]"
```

This installs conductor in editable mode along with testing tools like pytest and hypothesis.

## Server Setup (Conductor)

The conductor is the coordinator node that orchestrates the distributed tests.

### 1. Create Coordinator Configuration

Create a coordinator configuration file (e.g., `test_config.cfg`):

```ini
# Coordinator Test Configuration
[Test]
# Number of times to run the complete test cycle
trials = 1

[Clients]
# List of client configuration files
# Format: clientN = path/to/client_config.cfg
client1 = configs/web_server.cfg
client2 = configs/load_generator.cfg
client3 = configs/database.cfg
```

### 2. Create Client Configuration Files

For each client listed above, create a configuration file:

**Example: `configs/web_server.cfg`**
```ini
[Master]
# Player's IP address (where player will run)
player = 192.168.1.10
# Conductor's IP address (this machine)
conductor = 192.168.1.100
# Command port (player listens on this)
cmdport = 6970
# Results port (conductor listens on this)
resultsport = 6971

[Startup]
# Sequential setup steps
step1 = echo "Starting web server setup"
step2 = sudo systemctl start nginx
step3 = mkdir -p /tmp/test_results

[Run]
# Parallel execution steps
# Normal command
step1 = curl http://localhost/health
# Spawn command (fire and forget)
spawn1 = tail -f /var/log/nginx/access.log > /tmp/test_results/access.log
# Timeout command (kill after N seconds)
timeout30 = ab -n 10000 -c 100 http://localhost/

[Collect]
# Sequential collection steps
step1 = sudo cp /var/log/nginx/error.log /tmp/test_results/
step2 = tar -czf /tmp/web_results.tgz /tmp/test_results

[Reset]
# Sequential cleanup steps
step1 = sudo systemctl stop nginx
step2 = rm -rf /tmp/test_results
```

### 3. Run the Conductor

From the conductor machine:
```bash
conduct test_config.cfg
```

## Client Setup (Player)

The player is the worker node that executes commands.

### 1. Install Conductor Package

Follow the same installation steps as above on each client machine.

### 2. Start the Player

On each client machine, start the player with its configuration:

```bash
player configs/web_server.cfg
```

The player will:
1. Listen on the configured command port (default: 6970)
2. Wait for phases from the conductor
3. Execute commands as instructed
4. Send results back to the conductor

### 3. Player Command Options

```bash
# Basic usage
player <config_file>

# With custom ports (if needed to override config)
player --cmdport 7000 --resultsport 7001 <config_file>
```

## Network Configuration

### Firewall Rules

Ensure the following ports are open:

**On Player machines:**
- Inbound: Command port (default 6970) from conductor

**On Conductor machine:**
- Inbound: Results port (default 6971) from all players

### Example iptables Rules

**On Player:**
```bash
# Allow conductor to send commands
sudo iptables -A INPUT -p tcp --dport 6970 -s <conductor_ip> -j ACCEPT
```

**On Conductor:**
```bash
# Allow players to send results
sudo iptables -A INPUT -p tcp --dport 6971 -s <player_subnet> -j ACCEPT
```

### Testing Connectivity

Before running tests, verify connectivity:

```bash
# From conductor to player
telnet <player_ip> 6970

# From player to conductor
telnet <conductor_ip> 6971
```

## Running Your First Test

### 1. Simple Localhost Test

For testing the setup, create a localhost configuration:

**`localhost_coordinator.cfg`:**
```ini
[Test]
trials = 1

[Clients]
client1 = localhost_client.cfg
```

**`localhost_client.cfg`:**
```ini
[Master]
player = 127.0.0.1
conductor = 127.0.0.1
cmdport = 6970
resultsport = 6971

[Startup]
step1 = echo "Starting localhost test"

[Run]
step1 = echo "Running test"
step2 = date
step3 = whoami

[Collect]
step1 = echo "Collecting results"

[Reset]
step1 = echo "Test complete"
```

### 2. Start Player

In terminal 1:
```bash
player localhost_client.cfg
```

You should see:
```
('listening on: ', ('0.0.0.0', 6970))
```

### 3. Run Conductor

In terminal 2:
```bash
conduct localhost_coordinator.cfg
```

You should see output from each phase as it executes.

## Command Types

### Normal Commands
Execute and wait for completion:
```ini
step1 = echo "This is a normal command"
step2 = python script.py
```

### Spawn Commands
Start and continue without waiting:
```ini
spawn1 = python long_running_server.py
spawn2 = tcpdump -w capture.pcap
```

### Timeout Commands
Execute with a time limit:
```ini
timeout10 = curl http://slow-server.com
timeout60 = stress --cpu 4 --timeout 60s
```

## Troubleshooting

### Common Issues

#### 1. Connection Refused
**Error:** `Failed to connect to: <ip> <port>`

**Solutions:**
- Verify player is running: `ps aux | grep player`
- Check firewall rules: `sudo iptables -L`
- Verify correct IP/port in configs
- Test with telnet: `telnet <ip> <port>`

#### 2. No Results Received
**Symptom:** Conductor hangs waiting for results

**Solutions:**
- Check results port is open on conductor
- Verify conductor IP in player config
- Look for errors in player output
- Check network routing between machines

#### 3. Commands Not Executing
**Symptom:** Player receives phase but nothing happens

**Solutions:**
- Check command syntax in config
- Verify user permissions for commands
- Test commands manually on player machine
- Check for typos in step definitions

#### 4. Pickle Errors
**Error:** `pickle.loads() failed`

**Solutions:**
- Ensure same Python version on all machines
- Check for version mismatch between conductor/player
- Verify network isn't corrupting data

### Debug Mode

For debugging, add print statements to see what's happening:

```python
# In player script, after receiving phase:
print(f"Received phase with {len(phase.steps)} steps")
for i, step in enumerate(phase.steps):
    print(f"Step {i}: {step.args}")
```

### Log Files

Consider redirecting output to logs:

```bash
# Start player with logging
player config.cfg > player.log 2>&1 &

# Start conductor with logging
conduct coordinator.cfg > conductor.log 2>&1
```

## Best Practices

1. **Start Small**: Test with localhost first before distributed setup
2. **Version Control**: Keep configurations in version control
3. **Naming Convention**: Use descriptive names for steps and configs
4. **Error Handling**: Add error checking to your test commands
5. **Resource Cleanup**: Always include cleanup in Reset phase
6. **Documentation**: Comment your configuration files

## Example: Multi-Node Web Test

Here's a complete example for testing a web application across multiple nodes:

**`web_test_coordinator.cfg`:**
```ini
[Test]
trials = 3

[Clients]
webserver = configs/webserver.cfg
loadgen1 = configs/loadgen1.cfg
loadgen2 = configs/loadgen2.cfg
monitor = configs/monitor.cfg
```

**Start all players:**
```bash
# On web server machine
player configs/webserver.cfg

# On load generator 1
player configs/loadgen1.cfg

# On load generator 2
player configs/loadgen2.cfg

# On monitoring machine
player configs/monitor.cfg
```

**Run the test:**
```bash
conduct web_test_coordinator.cfg
```

This will coordinate all machines to run the distributed test three times, collecting results after each run.