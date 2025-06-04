# Conductor Architecture Documentation

## Overview

Conductor is a distributed testing framework designed to orchestrate tests across multiple networked systems. It follows a coordinator-worker pattern where a central conductor controls multiple players executing commands.

## System Components

### 1. Conductor (Coordinator)
- Central orchestration node
- Reads test configurations
- Manages test phases
- Collects results from players
- Controls test flow and synchronization

### 2. Player (Worker)
- Executes commands on remote systems
- Listens for instructions from conductor
- Returns execution results
- Maintains persistent connection for multiple test runs

## Architecture Diagrams

### System Overview
```
┌─────────────────────────────────────────────────────────────────┐
│                        Test Environment                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐                                          │
│  │   Conductor     │                                          │
│  │(Coordinator Node)│                                          │
│  │                 │                                          │
│  │ ┌─────────────┐ │                                          │
│  │ │  test.cfg   │ │                                          │
│  │ └─────────────┘ │                                          │
│  └────────┬────────┘                                          │
│           │                                                    │
│           │ TCP Sockets (Pickle Protocol)                     │
│           │                                                    │
│    ┌──────┴──────┬──────────┬──────────┐                    │
│    │             │          │          │                     │
│ ┌──▼───────┐ ┌──▼───────┐ ┌▼────────┐ ┌▼────────┐         │
│ │ Player 1 │ │ Player 2 │ │Player 3 │ │Player N │         │
│ │          │ │          │ │         │ │         │         │
│ │ ┌──────┐ │ │ ┌──────┐ │ │┌──────┐│ │┌──────┐│         │
│ │ │ DUT  │ │ │ │Server│ │ ││Client││ ││ Load ││         │
│ │ │ .cfg │ │ │ │ .cfg │ │ ││ .cfg ││ ││ Gen  ││         │
│ │ └──────┘ │ │ └──────┘ │ │└──────┘│ │└──────┘│         │
│ └──────────┘ └──────────┘ └─────────┘ └─────────┘         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Communication Flow
```
Conductor                          Player
    │                                │
    ├──────── 1. Connect ──────────►│
    │         (Port 6970)            │
    │                                │
    ├──────── 2. Send Config ──────►│
    │◄─────── 3. ACK (OK) ──────────┤
    │                                │
    ├──────── 4. Send Phase ───────►│
    │◄─────── 5. ACK (OK) ──────────┤
    │                                │
    ├──────── 6. Send Run Cmd ─────►│
    │                                ├─── 7. Execute Steps
    │                                │    ├── Step 1
    │                                │    ├── Step 2
    │                                │    └── Step N
    │                                │
    │◄─────── 8. Send Results ──────┤
    │         (Port 6971)            │
    │                                │
    └────────────────────────────────┘
```

### Class Hierarchy
```
conductor/
    │
    ├── client.Client ──────────┬──► phase.Phase ────┬──► step.Step
    │   ├── config             │    ├── steps[]     │    ├── cmd
    │   ├── phases[]           │    ├── run()       │    ├── spawn
    │   ├── startup()          │    └── results[]   │    ├── timeout
    │   ├── run()              │                     │    └── run()
    │   ├── collect()          │                     │
    │   └── reset()            │                     │
    │                          │                     │
    ├── config.Config ─────────┘                     │
    │   ├── host                                     │
    │   └── port                                     │
    │                                                │
    └── retval.RetVal ◄──────────────────────────────┘
        ├── code (OK/ERROR/BAD_CMD/DONE)
        └── message
```

## Core Classes

### Client (`client.py`)
- Represents a player from conductor's perspective
- Manages socket connection to a player
- Sends phases and receives results
- Handles configuration for each player

### Phase (`phase.py`)
- Container for multiple steps
- Four types: Startup, Run, Collect, Reset
- Executes steps sequentially (except Run phase)
- Returns aggregated results to conductor

### Step (`step.py`)
- Individual command execution unit
- Supports different execution modes:
  - **Normal**: Wait for completion
  - **Spawn**: Fire and forget
  - **Timeout**: Execute with time limit
- Uses subprocess for command execution

### RetVal (`retval.py`)
- Communication protocol for results
- Standardized return codes:
  - `RETVAL_OK` (0): Success
  - `RETVAL_ERROR` (1): Error
  - `RETVAL_BAD_CMD` (2): Unknown command
  - `RETVAL_DONE` (65535): Completion signal

## Communication Protocol

### Data Flow Diagram
```
┌────────────────────────────────────────────────────────────────┐
│                         Conductor                              │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐ │
│  │  Config     │───►│   Client     │───►│  Socket Handler  │ │
│  │  Parser     │    │   Manager    │    │                  │ │
│  └─────────────┘    └──────────────┘    └────────┬─────────┘ │
│                                                   │           │
└───────────────────────────────────────────────────┼───────────┘
                                                    │
                              Network               │
                         ═══════════════════════════╪═══════════
                                                    │
┌───────────────────────────────────────────────────┼───────────┐
│                         Player                    │           │
│  ┌──────────────────┐    ┌──────────────┐    ┌──▼─────────┐ │
│  │  Command         │◄───│   Phase      │◄───│  Socket    │ │
│  │  Executor        │    │   Handler    │    │  Listener  │ │
│  └────────┬─────────┘    └──────────────┘    └────────────┘ │
│           │                                                   │
│           ▼                                                   │
│  ┌──────────────────┐    ┌──────────────┐                   │
│  │   Subprocess     │───►│   Result     │                   │
│  │     Runner       │    │   Sender     │                   │
│  └──────────────────┘    └──────────────┘                   │
└───────────────────────────────────────────────────────────────┘
```

### Message Protocol Detail
```
┌─────────────────────────────────────────┐
│           Message Structure             │
├─────────────────────────────────────────┤
│  Bytes 0-3:  Message Length (uint32)   │
│  ┌───┬───┬───┬───┐                     │
│  │ L │ E │ N │   │  (Big Endian)       │
│  └───┴───┴───┴───┘                     │
├─────────────────────────────────────────┤
│  Bytes 4-N:  Pickled Python Object     │
│  ┌─────────────────────────────────┐   │
│  │                                 │   │
│  │    Serialized Object Data       │   │
│  │    (Config/Phase/Run/RetVal)    │   │
│  │                                 │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### Sequence Diagram
```
Conductor          Player 1         Player 2         Player N
    │                 │                │                │
    │═══ Connect ════►│                │                │
    │◄══ Accept ═════│                │                │
    │                 │                │                │
    │══ Connect ═════════════════════►│                │
    │◄═ Accept ══════════════════════│                │
    │                 │                │                │
    │══ Config ═════►│                │                │
    │◄═ ACK ═════════│                │                │
    │                 │                │                │
    │══ Config ══════════════════════►│                │
    │◄═ ACK ══════════════════════════│                │
    │                 │                │                │
    │══ Phase(Startup)►│               │                │
    │◄═ ACK ═════════│                │                │
    │                 │                │                │
    │══ Phase(Startup)═══════════════►│                │
    │◄═ ACK ══════════════════════════│                │
    │                 │                │                │
    │══ Run ════════►│                │                │
    │                 │──Execute──┐    │                │
    │                 │◄─────────┘    │                │
    │                 │                │                │
    │══ Run ═════════════════════════►│                │
    │                 │                │──Execute──┐    │
    │                 │                │◄─────────┘    │
    │                 │                │                │
    │◄═ Results ═════│                │                │
    │◄═ Results ══════════════════════│                │
    │                 │                │                │
    └─────────────────┴────────────────┴────────────────┘
```

### Ports
- **Command Port**: Receives instructions (default: 6970)
- **Results Port**: Sends execution results (default: 6971)

## Test Execution Flow

### State Machine
```
┌─────────┐     ┌──────────┐     ┌─────────┐     ┌─────────┐
│ STARTUP ├────►│   RUN    ├────►│ COLLECT ├────►│  RESET  │
└─────────┘     └──────────┘     └─────────┘     └─────────┘
     │               │                 │               │
     ▼               ▼                 ▼               ▼
  Sequential      Parallel         Sequential     Sequential
  Execution       Execution        Execution      Execution
```

### Detailed Flow
```
┌─────────────────────────────────────────────────────────┐
│                    Conductor Start                      │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              1. Initialization Phase                    │
│  ┌──────────────────────────────────────────────────┐  │
│  │ • Read test.cfg                                  │  │
│  │ • Parse [Test] section for trials count         │  │
│  │ • Parse [Clients] section for player configs    │  │
│  │ • Load each player's configuration file         │  │
│  └──────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              2. Player Connection Phase                 │
│  ┌──────────────────────────────────────────────────┐  │
│  │ For each player:                                 │  │
│  │   1. Create socket to player:cmdport             │  │
│  │   2. Send Config object                          │  │
│  │   3. Receive ACK                                 │  │
│  │   4. Store connection reference                  │  │
│  └──────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              3. Test Execution Loop                     │
│  ┌──────────────────────────────────────────────────┐  │
│  │ For trial in range(trials):                      │  │
│  │   For phase in [Startup, Run, Collect, Reset]:  │  │
│  │     a. Send phase to all players                │  │
│  │     b. Send run command to all players          │  │
│  │     c. Collect results from all players         │  │
│  └──────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│                  4. Cleanup Phase                       │
│  ┌──────────────────────────────────────────────────┐  │
│  │ • Close all socket connections                   │  │
│  │ • Aggregate test results                         │  │
│  │ • Generate reports (if configured)               │  │
│  │ • Exit with appropriate code                     │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Configuration Structure

### Test Configuration (`test.cfg`)
```ini
[Test]
trials: 1              # Number of test iterations

[Clients]
client1: dut.cfg       # Player configuration files
client2: server.cfg
```

### Player Configuration (`player.cfg`)
```ini
[Master]
player: 192.168.1.10   # Player's IP address
conductor: 192.168.1.1 # Conductor's IP address
cmdport: 6970          # Command port
resultsport: 6971      # Results port

[Startup]
step1: mkdir -p /tmp/test

[Run]
step1: spawn:iperf -s
step2: timeout30:ping -c 100 target

[Collect]
step1: tar -czf results.tgz /tmp/test

[Reset]
step1: rm -rf /tmp/test
```

## Execution Modes

### Phase Execution Patterns
```
STARTUP Phase (Sequential)          RUN Phase (Parallel)
─────────────────────────          ─────────────────────
                                   
Step 1 ──────►│                    Step 1 ────┐
              ▼                                │
Step 2 ──────►│                    Step 2 ────┼────► All
              ▼                                │      Start
Step 3 ──────►│                    Step 3 ────┤      Together
              ▼                                │
            Done                   Step N ────┘

COLLECT Phase (Sequential)          RESET Phase (Sequential)
──────────────────────────         ───────────────────────

Step 1 ──────►│                    Step 1 ──────►│
              ▼                                  ▼
Step 2 ──────►│                    Step 2 ──────►│
              ▼                                  ▼
            Done                               Done
```

### Command Execution Types
```
┌─────────────────────────────────────────────────────────────┐
│                    Step Execution Modes                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Normal Execution (Default)                              │
│     ┌──────────┐                                          │
│     │ Command  │──► Wait for ──► Get Exit ──► Continue    │
│     └──────────┘    Completion     Code                    │
│                                                             │
│  2. Spawn Execution (spawn: prefix)                        │
│     ┌──────────┐                                          │
│     │ Command  │──► Start ──► Continue                    │
│     └──────────┘    Process    (Don't Wait)               │
│                                                             │
│  3. Timeout Execution (timeout<N>: prefix)                 │
│     ┌──────────┐                                          │
│     │ Command  │──► Start ──► Wait Max ──► Kill if        │
│     └──────────┘             N seconds     Still Running   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Example Step Configurations
```ini
[Startup]
# Normal execution - waits for completion
step1: mkdir -p /tmp/test
step2: cp config.txt /tmp/test/

[Run]
# Spawn execution - fire and forget
step1: spawn:iperf3 -s -D
step2: spawn:tcpdump -i eth0 -w capture.pcap

# Timeout execution - max 30 seconds
step3: timeout30:wget http://example.com/large_file.zip

[Collect]
# Normal execution again
step1: tar -czf results.tgz /tmp/test
step2: scp results.tgz conductor:/results/

[Reset]
# Cleanup
step1: killall iperf3
step2: rm -rf /tmp/test
```

## Error Handling

### Network Failures
- Socket exceptions caught and logged
- Player connection failures reported
- Conductor continues with remaining players

### Command Failures
- Non-zero exit codes captured
- Stderr output included in results
- Failures don't stop phase execution

### Timeout Handling
- Processes killed after timeout
- Timeout status returned in results
- Cleanup of zombie processes

## Scalability Considerations

### Current Limitations
- Synchronous communication with players
- Sequential player setup
- Single-threaded conductor

### Potential Improvements
- Asynchronous player communication
- Parallel phase distribution
- Result streaming vs batch collection
- Player health monitoring

## Security Notes

### Current State
- No authentication between conductor/player
- Plaintext communication
- Arbitrary command execution
- Trust-based model

### Recommendations
- Add TLS encryption
- Implement authentication tokens
- Command whitelisting option
- Audit logging

## Extension Points

### Custom Phases
- Extend Phase class
- Add new phase types beyond four defaults
- Custom execution strategies

### Result Processing
- Extend RetVal for richer data
- Add result aggregation plugins
- Real-time result streaming

### Player Capabilities
- Platform-specific command adapters
- Resource monitoring integration
- Custom step executors