# Conductor CLI Reference

## conduct - Orchestrate distributed tests

The `conduct` command is the coordinator controller that orchestrates tests across multiple player nodes.

### Synopsis

```bash
conduct [OPTIONS] CONFIG_FILE
```

### Options

| Option | Description |
|--------|-------------|
| `-h, --help` | Show help message and exit |
| `-t, --trials TRIALS` | Number of trials to run (overrides config file) |
| `-p, --phases PHASE [PHASE ...]` | Phases to execute: startup, run, collect, reset, all (default: all) |
| `-c, --clients CLIENT [CLIENT ...]` | Specific clients to use (overrides config file) |
| `-v, --verbose` | Enable verbose output with detailed logging |
| `-q, --quiet` | Suppress all output except errors |
| `--dry-run` | Show what would be executed without running |
| `--format FORMAT` | Output format: text (default) or json |
| `--output FILE` | Write results to file instead of stdout |
| `--version` | Show version information |

### Examples

#### Basic Usage
```bash
# Run test with default settings from config
conduct test_config.cfg

# Run 5 trials instead of config default
conduct -t 5 test_config.cfg

# Run with verbose logging
conduct -v test_config.cfg
```

#### Selective Execution
```bash
# Run only specific phases
conduct -p startup run test_config.cfg

# Run only reset phase
conduct -p reset test_config.cfg

# Run specific clients only
conduct -c client1 client3 test_config.cfg
```

#### Testing and Debugging
```bash
# Dry run to see what would be executed
conduct --dry-run test_config.cfg

# Quiet mode for scripts
conduct -q test_config.cfg

# Verbose mode for debugging
conduct -v test_config.cfg
```

#### Output Formatting
```bash
# Get results in JSON format
conduct --format json test_config.cfg

# Save results to file
conduct --output results.txt test_config.cfg

# JSON results to file for processing
conduct --format json --output results.json test_config.cfg

# Combine with other options
conduct -v --format json -t 5 --output test_results.json test_config.cfg
```

### Configuration File Format

The coordinator configuration file specifies test parameters and worker configurations:

```ini
[Test]
trials = 3

[Workers]
client1 = path/to/client1.cfg
client2 = path/to/client2.cfg
```

## player - Execute commands from conductor

The `player` command runs on each test node and executes commands sent by the conductor.

### Synopsis

```bash
player [OPTIONS] CONFIG_FILE
```

### Options

| Option | Description |
|--------|-------------|
| `-h, --help` | Show help message and exit |
| `-v, --verbose` | Enable verbose output |
| `-q, --quiet` | Suppress all output except errors |
| `-l, --log-file FILE` | Log output to file |
| `--version` | Show version information |

### Examples

#### Basic Usage
```bash
# Start player with config
player client_config.cfg

# Start with verbose logging
player -v client_config.cfg

# Log to file for debugging
player -l player.log client_config.cfg
```

#### Logging Options
```bash
# Verbose output to console and file
player -v -l player_debug.log client_config.cfg

# Quiet mode with file logging only
player -q -l player.log client_config.cfg
```

### Configuration File Format

The player configuration file specifies connection details and test steps:

```ini
[Coordinator]
player = 192.168.1.10      # This player's IP
conductor = 192.168.1.100  # Conductor's IP
cmdport = 6970            # Port to listen on
resultsport = 6971        # Port for results

[Startup]
step1 = echo "Starting tests"

[Run]
step1 = run_test_command
spawn1 = background_monitor
timeout30 = time_limited_test

[Collect]
step1 = gather_results

[Reset]
step1 = cleanup_command
```

## Common Workflows

### Running a Distributed Test

1. Start all players first:
```bash
# On machine A
player -v machine_a.cfg

# On machine B
player -v machine_b.cfg
```

2. Run conductor:
```bash
# On conductor machine
conduct -v -t 3 test_coordinator.cfg
```

### Debugging Connection Issues

1. Test with verbose logging:
```bash
# Player with debug output
player -v -l player_debug.log config.cfg

# Conductor with debug output
conduct -v test.cfg
```

2. Test with specific network settings:
```bash
# Force player to specific interface
player -b 10.0.0.5 -p 7000 config.cfg
```

### Running Partial Tests

```bash
# Just run startup and reset
conduct -p startup reset test.cfg

# Run only on specific clients
conduct -c webserver database test.cfg

# Combine options
conduct -v -t 1 -p run collect -c client1 test.cfg
```

## Output Formats

### Text Format (Default)

The default text format provides human-readable output:

```
Trial 1 of 3
Phase: startup
  Client: webserver
    Step 1: OK
    Step 2: OK
  Client: database
    Step 1: OK
    
Phase: run
  Client: webserver
    Step 1: OK - Server started on port 8080
  Client: database
    Step 1: OK - Database initialized
```

### JSON Format

The JSON format provides structured output for programmatic processing:

```json
{
  "trial": 1,
  "total_trials": 3,
  "phases": [
    {
      "name": "startup",
      "clients": [
        {
          "name": "webserver",
          "steps": [
            {"index": 1, "status": "OK", "output": ""},
            {"index": 2, "status": "OK", "output": ""}
          ]
        }
      ]
    }
  ]
}
```

## Exit Codes

Both `conduct` and `player` use standard exit codes:

- `0` - Success
- `1` - General error (config not found, network error, etc.)
- `2` - Command line usage error
- `130` - Interrupted (Ctrl+C)

## Environment Variables

While not required, you can set these for convenience:

```bash
# Default config locations
export CONDUCTOR_CONFIG=/path/to/configs

# Default ports (still must be in config files)
export CONDUCTOR_CMD_PORT=6970
export CONDUCTOR_RESULTS_PORT=6971
```

## Logging

### Log Levels

- **ERROR**: Critical errors only (`-q`)
- **INFO**: Normal operation (default)
- **DEBUG**: Detailed debugging (`-v`)

### Log Format

```
2024-01-15 10:30:45 - INFO - Reading configuration from: test.cfg
2024-01-15 10:30:45 - INFO - Loading 3 client(s)
2024-01-15 10:30:46 - INFO - Running 1 trial(s) with phases: startup, run, collect, reset
```

## Signal Handling

Both commands handle signals gracefully:

- **SIGINT** (Ctrl+C): Graceful shutdown
- **SIGTERM**: Graceful shutdown
- **SIGKILL**: Immediate termination (avoid if possible)

## Best Practices

1. **Always start players before conductor**
2. **Use verbose mode when debugging**
3. **Use dry-run to verify configuration**
4. **Log to files for post-mortem analysis**
5. **Use specific binding addresses in production**

## Compatibility Notes

- Python 3.8+ required
- Works on Linux, macOS, BSD, Windows (with limitations)
- JSON protocol v1 for secure communication
- Modern CLI with argparse for better user experience
- Reporter system for flexible output formats