# Contributing to Conductor

Welcome to the Conductor distributed testing framework! This guide will help you get started with contributing to the project.

## Table of Contents

- [Development Setup](#development-setup)
- [Testing Guide](#testing-guide)
- [Code Quality](#code-quality)
- [Contribution Workflow](#contribution-workflow)
- [Architecture Overview](#architecture-overview)
- [Common Tasks](#common-tasks)

## Development Setup

### Prerequisites

- Python 3.8 or higher
- Git
- Virtual environment support

### Quick Setup

```bash
# Clone the repository
git clone https://github.com/benroeder/conductor.git
cd conductor

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with all dependencies
pip install -e ".[dev]"

# Verify installation
conduct --help
player --help
```

### Development Dependencies

The project includes these development tools:
- **pytest**: Test runner with coverage reporting
- **pytest-cov**: Coverage plugin for pytest
- **pytest-mock**: Mocking support for tests
- **hypothesis**: Property-based testing framework
- **ruff**: Fast Python linter and formatter

## Testing Guide

### Test Structure

The test suite is organized into several categories:

```
tests/
├── test_*.py              # Unit tests for core modules
├── test_*_edge_cases.py   # Edge case tests using Hypothesis
├── test_*_integration.py  # Integration tests
├── localhost/             # Local integration test configs
├── timeout/               # Timeout test configs
└── multi_player/          # Multi-player end-to-end tests
```

### Running Tests

#### Basic Test Commands

```bash
# Run all tests
python -m pytest

# Run tests with coverage
python -m pytest --cov=conductor --cov-report=term-missing

# Run specific test categories
python -m pytest -m unit          # Unit tests only
python -m pytest -m integration   # Integration tests only
python -m pytest -m slow          # Slow-running tests

# Run specific test files
python -m pytest tests/test_json_protocol.py
python -m pytest tests/test_client.py

# Run with verbose output
python -m pytest -v

# Run tests matching a pattern
python -m pytest -k "test_max_message_size"
```

#### Integration Testing

```bash
# Run the full integration test script
./test_conductor.sh

# Manual integration testing
cd tests/localhost

# Terminal 1: Start player
../../venv/bin/player dut.cfg

# Terminal 2: Run conductor
../../venv/bin/conduct conductor.cfg

# Test with different options
../../venv/bin/conduct --format json conductor.cfg
../../venv/bin/conduct --dry-run conductor.cfg
../../venv/bin/conduct --max-message-size 20 conductor.cfg
```

#### Multi-Player Testing

```bash
# Run comprehensive multi-player tests
cd tests/multi_player
python test_multi_player.py

# This tests 2-10 concurrent players automatically
```

#### Property-Based Testing

The project uses Hypothesis for property-based testing:

```bash
# Run hypothesis tests specifically
python -m pytest tests/test_*_hypothesis.py

# Run with more examples for thorough testing
python -m pytest tests/test_json_protocol_hypothesis.py --hypothesis-show-statistics
```

### Test Coverage Requirements

- **Minimum Coverage**: 80% overall
- **Core Modules**: 90%+ coverage required for:
  - `json_protocol.py`
  - `client.py`
  - `phase.py`
  - `step.py`
  - `retval.py`

Check current coverage:
```bash
python -m pytest --cov=conductor --cov-report=html
# Open htmlcov/index.html to view detailed coverage report
```

### Writing Tests

#### Unit Test Example

```python
import pytest
from conductor.step import Step

class TestStep:
    def test_step_creation(self):
        """Test basic step creation."""
        step = Step("echo hello")
        assert step.cmd == "echo hello"
        assert step.spawn is False
        assert step.timeout is None
    
    def test_step_execution(self):
        """Test step execution."""
        step = Step("echo hello")
        result = step.run()
        assert result.code == 0
        assert "hello" in result.message
```

#### Integration Test Example

```python
import tempfile
import configparser
from conductor.client import Client

def test_client_with_config():
    """Test client creation with real config."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cfg', delete=False) as f:
        f.write("""
[Coordinator]
player = 127.0.0.1
conductor = 127.0.0.1
cmdport = 6970
resultsport = 6971

[Startup]
step1 = echo "test"
""")
        f.flush()
        
        config = configparser.ConfigParser()
        config.read(f.name)
        
        client = Client(config)
        assert client.host == "127.0.0.1"
        assert client.cmd_port == 6970
```

#### Property-Based Test Example

```python
from hypothesis import given, strategies as st
from conductor.json_protocol import encode_message

@given(st.text(), st.dictionaries(st.text(), st.text()))
def test_encode_message_properties(msg_type, data):
    """Test that encode_message always produces valid output."""
    result = encode_message(msg_type, data)
    
    # Should always be bytes
    assert isinstance(result, bytes)
    
    # Should have length header
    assert len(result) >= 4
    
    # Length header should match payload
    expected_length = len(result) - 4
    actual_length = int.from_bytes(result[:4], byteorder='big')
    assert actual_length == expected_length
```

## Code Quality

### Code Formatting

The project uses **ruff** for linting and formatting:

```bash
# Check code style
ruff check .

# Fix auto-fixable issues
ruff check --fix .

# Format code
ruff format .
```

### Code Style Guidelines

1. **Follow PEP 8** with these exceptions:
   - Line length: 88 characters (Black compatible)
   - Use double quotes for strings

2. **Documentation**:
   - All public functions need docstrings
   - Use Google-style docstrings
   - Include type hints where helpful

3. **Error Handling**:
   - Always handle expected exceptions
   - Use specific exception types
   - Include helpful error messages

4. **Testing**:
   - Write tests for all new features
   - Include edge cases
   - Test error conditions

### Example Function Documentation

```python
def send_message(sock: socket.socket, msg_type: str, data: Dict[str, Any], 
                max_message_size: int = None) -> None:
    """Send a JSON message over a socket.
    
    Args:
        sock: The socket to send the message on
        msg_type: Type of message (e.g., 'config', 'phase', 'retval')
        data: Message payload data
        max_message_size: Maximum allowed message size in bytes
        
    Raises:
        ProtocolError: If message exceeds size limit
        OSError: If socket operation fails
        
    Example:
        >>> send_message(sock, 'config', {'host': '127.0.0.1'})
    """
```

## Contribution Workflow

### 1. Before Starting

- Check existing issues for similar work
- Create an issue to discuss major changes
- Fork the repository if you're an external contributor

### 2. Development Process

```bash
# Create a feature branch
git checkout -b feature/your-feature-name

# Make your changes
# ... edit code ...

# Run tests frequently
python -m pytest tests/test_relevant_module.py

# Run full test suite before committing
python -m pytest

# Check code quality
ruff check .
ruff format .
```

### 3. Testing Your Changes

```bash
# Run comprehensive testing
make test  # If Makefile exists, otherwise:

# Unit tests
python -m pytest -m unit

# Integration tests
python -m pytest -m integration
./test_conductor.sh

# Multi-player tests
cd tests/multi_player && python test_multi_player.py

# Edge case testing
python -m pytest tests/test_*_edge_cases.py

# Manual testing
cd tests/localhost
../../venv/bin/player dut.cfg &
../../venv/bin/conduct conductor.cfg
```

### 4. Commit Guidelines

- Use clear, descriptive commit messages
- Follow conventional commit format when possible:
  ```
  feat: add max message size configuration
  fix: handle binary output in step execution
  docs: update contributing guide
  test: add edge cases for JSON protocol
  ```

- Keep commits focused and atomic
- Include tests with feature commits

### 5. Pull Request Process

1. **Ensure all tests pass**
2. **Update documentation** if needed
3. **Add changelog entry** if appropriate
4. **Create pull request** with:
   - Clear description of changes
   - Link to related issues
   - Test results summary

## Architecture Overview

Understanding the architecture helps with contributions:

### Core Components

- **Conductor**: Orchestrates tests across multiple nodes
- **Player**: Executes commands on individual nodes
- **JSON Protocol**: Secure communication between conductor/players
- **Reporter**: Handles output formatting (text/JSON)

### Key Classes

- `Client`: Manages player connections from conductor
- `Phase`: Container for test steps (startup/run/collect/reset)
- `Step`: Individual command execution unit
- `RetVal`: Standardized return values
- `Config`: Configuration file parser

### Communication Flow

```
Conductor → JSON Protocol → Player
    ↓            ↓             ↓
  Client → TCP Socket → Command Executor
    ↓            ↓             ↓
 Reporter ← JSON Results ← Step Results
```

## Common Tasks

### Adding a New CLI Option

1. **Update argument parser** in `scripts/conduct.py` or `scripts/player.py`
2. **Add validation function** if needed
3. **Update main() function** to handle the option
4. **Write tests** in `tests/test_conduct_cli.py` or `tests/test_player_cli.py`
5. **Update documentation** in `docs/CLI_REFERENCE.md`

### Adding a New Protocol Message

1. **Define message structure** in `json_protocol.py`
2. **Add encoding/decoding functions**
3. **Update protocol version** if breaking change
4. **Write comprehensive tests** including edge cases
5. **Update documentation** in `docs/ARCHITECTURE.md`

### Adding a New Output Format

1. **Extend Reporter class** in `reporter.py`
2. **Implement format-specific methods**
3. **Add CLI option** for the new format
4. **Write tests** for the new reporter
5. **Update documentation** and examples

### Debugging Integration Issues

1. **Use verbose logging**:
   ```bash
   conduct -v test.cfg
   player -v config.cfg
   ```

2. **Check network connectivity**:
   ```bash
   netstat -an | grep 6970  # Check if ports are open
   telnet conductor_ip 6970  # Test connectivity
   ```

3. **Use dry-run mode**:
   ```bash
   conduct --dry-run test.cfg
   ```

4. **Examine test configurations**:
   ```bash
   # Use simple configs from tests/localhost/
   cp tests/localhost/conductor.cfg my_test.cfg
   ```

## Getting Help

- **Documentation**: Check `docs/` directory
- **Examples**: Look in `tests/localhost/` and `examples/`
- **Issues**: Create a GitHub issue for bugs or questions
- **Architecture**: See `docs/ARCHITECTURE.md` for detailed internals

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (BSD 3-Clause).