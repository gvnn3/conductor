# Conductor - A system for testing distributed systems across a network #

[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-BSD-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-98%25%20coverage-brightgreen.svg)](tests/)

Many test frameworks exist to test code on a single host or, across a
network, on a single server.  Conductor is a distributed system test
framework, written in Python, that can be used to coordinate a set of
tests among a set of clients.  The Conductor system allows a single
machine to control several systems, orchestrating tests that require
the cooperation of several networked devices.

## Features ##

- **Distributed Testing**: Coordinate tests across multiple networked machines
- **Phase-based Execution**: Startup → Run → Collect → Reset workflow
- **Parallel & Sequential Control**: Run steps in parallel or sequence as needed
- **Command Types**: Normal, spawn (background), and timeout commands
- **Rich CLI**: Modern command-line interface with helpful options
- **Flexible Configuration**: INI-based configuration with override options
- **Comprehensive Logging**: Verbose mode, quiet mode, and file logging
- **Test Isolation**: Each trial starts fresh with setup/teardown phases

## Requirements ##

- Python 3.8 or higher
- pip (for installation)
- Network connectivity between conductor and players

## Documentation ##

- **[Quick Start Guide](QUICK_START.md)** - Get running in 5 minutes
- **[Installation Guide](INSTALLATION_GUIDE.md)** - Detailed setup instructions
- **[CLI Reference](CLI_REFERENCE.md)** - Command-line options and examples
- **[Example Configurations](examples/)** - Real-world test examples
- **[Architecture Overview](ARCHITECTURE.md)** - System internals

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

For detailed installation instructions, see the [Installation Guide](INSTALLATION_GUIDE.md).

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

## Commentary ##

A common use for Conductor is to test network devices, such as a
router or firewall, that are connected to multiple senders and
receivers.  Each of the senders, receivers, and the device under test
(DUT) are a *Player*, and another system is designated as the *Conductor*.

The players, read commands over a network channel, execute them and
return results to the conductor.

The conductor reads test descriptions from a configuration file,
written using Python's config parser, and executes the tests on the
players.

The tests are executed in *Phases*.  A *Phase* contains a set of internal
or external (shell/program) commands that are executed in order, per
client.  The four Phases currently defined are:

  * Startup

The *Startup* phase is where commands that are required to set up each
device are execute.  Examples include setting up network interfaces,
routing tables, as well as creating directories to hold result files
on the players.

  * Run

The *Run* phase contains the commands that are the core of the test.  An
example might be starting a number of transmitting and receiving
programs to generate and sink traffic through the DUT.

  * Collect

In the *Collect* phase the Conductor sends commands to the Players to
retrieve any data that was generated during the test, and places that
data into a results directory on the Conductor, for later analysis.

  * Reset

The last phase is the *Reset* phase, where the Conductor instructs the
Players to reset any configuration that might have been set in the
Startup phase and which might influence later test runs.  It is the
goal when writing Conductor tests that all the systems used in the
test return to the state they were in prior to the Startup phase.

Each Phase has three parts.  The Conductor first downloads the Phase
to the Player, but does not tell it to execute.  Downloading the Phase
to each client allows the Conductor to start each Phase nearly
simultaneously, although the fact that the Conductor itself serializes
its communication among the clients means that there is a small amount
of skew in when each Player is told to execute its steps.  

Each phase is made up of several steps.  There are two, special,
keywords for steps executed in the Run phase.

A *spawn* keyword (spawn:echo 30) will spawn the command as a
sub-process and not wait for it to execute, nor collect the program's
return value.  The spawn keyword is best used to start several
programs simultaneously, such as multiple network streams when testing
a piece of networking equipment.

A *timeout* keyword (timeout10:sleep 30) will execute the command with
a timeout.  The timeout is the number directly after the keyword and
is expressed in seconds.  A command executed with a timeout will be
interrupted by its parent if it doesn't exit before the timeout
expires.  In the example above the sleep command will try to sleep for
30 seconds but then be interrupted after 10 seconds.  The timeout
keyword is useful for programs that want to run forever or which wait
for human input unnecessarily.

This work supported by: Rubicon Communications, LLC (Netgate)
