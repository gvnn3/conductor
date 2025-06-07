# JSON Protocol Implementation for Conductor (No Backward Compatibility)

## Summary

This document describes the complete replacement of Python's pickle protocol with JSON for all network communication in Conductor. No backward compatibility with pickle is maintained.

## Changes Made

### 1. New JSON Protocol Module (`conductor/json_protocol.py`)
- Simple, secure JSON-based messaging
- Length-prefixed messages (4-byte header + JSON payload)
- Message types: phase, run, config, result, done, error
- Maximum message size limit (10MB) for safety

### 2. Updated Core Components

#### `conductor/retval.py`
- Replaced pickle serialization with JSON
- `send()` method now uses `send_message()` from json_protocol

#### `conductor/client.py`
- Removed pickle imports
- `download()` method converts Phase objects to JSON format
- `doit()` sends simple JSON message for RUN command
- `results()` receives JSON messages instead of pickled objects
- Removed `len_recv()` method (now handled by json_protocol)

#### `scripts/player`
- Removed pickle imports
- Receives and parses JSON messages
- Reconstructs Phase objects from JSON data
- All message handling uses the JSON protocol

## Message Format

### Basic Structure
```json
{
    "type": "message_type",
    "data": {
        // Message-specific data
    }
}
```

### Message Types

#### Phase Message
```json
{
    "type": "phase",
    "data": {
        "resulthost": "127.0.0.1",
        "resultport": 6971,
        "steps": [
            {
                "command": "echo test",
                "spawn": false,
                "timeout": 30
            }
        ]
    }
}
```

#### Run Message
```json
{
    "type": "run",
    "data": {}
}
```

#### Result Message
```json
{
    "type": "result",
    "data": {
        "code": 0,
        "message": "Success"
    }
}
```

## Benefits of JSON Protocol

1. **Security**: No arbitrary code execution (unlike pickle)
2. **Debugging**: Human-readable messages
3. **Language Agnostic**: Can integrate with non-Python tools
4. **Simplicity**: Standard JSON parsing
5. **Safety**: Message size limits prevent DoS attacks

## Testing

The implementation has been tested with the localhost example:
- Player receives JSON messages correctly
- Phases are executed as expected
- Results are returned in JSON format
- All four phases (Startup, Run, Collect, Reset) work correctly

## Migration Impact

Since no backward compatibility is maintained:
1. All conductor and player instances must be updated simultaneously
2. Cannot mix old pickle-based and new JSON-based components
3. Clean deployment required (no rolling updates)

## Completed Enhancements

1. **JSON Protocol**: Replaced pickle with secure JSON messaging (✓)
2. **Protocol Versioning**: Added version field to all messages (✓)
3. **Message Size Limits**: Configurable size limits with 100MB default (✓)
4. **JSON Results Output**: Added -f json option for structured test results (✓)
5. **Build System Modernization**: Replaced setup.py with pyproject.toml (✓)

## Future Enhancements

1. **Message Validation**: Add JSON schema validation
2. **Compression**: Optional gzip compression for large messages
3. **Encryption**: TLS support for secure communication
4. **Authentication**: Message signing or mutual TLS
5. **Performance**: Connection pooling for better performance