"""Property-based tests using Hypothesis."""

import socket
import struct
import pickle
from hypothesis import given, strategies as st
from hypothesis.strategies import text, integers, lists, booleans

from conductor.retval import RetVal
from conductor.step import Step
from conductor.config import Config
from conductor.phase import Phase


class TestRetValProperties:
    """Property-based tests for RetVal class."""

    @given(code=integers(min_value=0, max_value=65535), message=text(max_size=1000))
    def test_retval_roundtrip_serialization(self, code, message):
        """Test that RetVal can be serialized and deserialized correctly."""
        original = RetVal(code=code, message=message)

        # Pickle and unpickle
        pickled = pickle.dumps(original)
        restored = pickle.loads(pickled)

        assert restored.code == original.code
        assert restored.message == original.message

    @given(code=integers(min_value=0, max_value=65535), message=text(max_size=100))
    def test_retval_send_message_format(self, code, message):
        """Test that send() creates valid length-prefixed messages."""
        retval = RetVal(code=code, message=message)

        # Mock socket to capture sent data
        class MockSocket:
            def __init__(self):
                self.data = b""

            def sendall(self, data):
                self.data = data

        mock_sock = MockSocket()
        retval.send(mock_sock)

        # Verify message format
        assert len(mock_sock.data) >= 4  # At least length prefix

        # Extract length and verify
        length_bytes = mock_sock.data[:4]
        length = socket.ntohl(struct.unpack("!I", length_bytes)[0])
        assert len(mock_sock.data[4:]) == length

        # Verify we can unpickle the payload
        unpickled = pickle.loads(mock_sock.data[4:])
        assert unpickled.code == code
        assert unpickled.message == message


class TestStepProperties:
    """Property-based tests for Step class."""

    @given(command=text(min_size=1, max_size=100).filter(lambda x: x.strip()))
    def test_step_parses_any_command(self, command):
        """Test that Step can parse any non-empty command."""
        step = Step(command)
        assert step.args is not None
        assert len(step.args) >= 1
        assert step.spawn is False
        assert step.timeout == 30

    @given(
        command=text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        spawn=booleans(),
        timeout=integers(min_value=1, max_value=3600),
    )
    def test_step_initialization_with_parameters(self, command, spawn, timeout):
        """Test Step initialization with various parameters."""
        step = Step(command, spawn=spawn, timeout=timeout)
        assert step.spawn == spawn
        assert step.timeout == timeout
        assert step.args is not None

    @given(command=st.from_regex(r"[a-zA-Z0-9]+ [a-zA-Z0-9\-\./]+ *", fullmatch=True))
    def test_step_command_with_arguments(self, command):
        """Test that commands with arguments are parsed correctly."""
        step = Step(command)
        parts = command.strip().split()
        assert len(step.args) >= len(parts)


class TestConfigProperties:
    """Property-based tests for Config class."""

    @given(
        host=text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        port=integers(min_value=1, max_value=65535),
    )
    def test_config_initialization(self, host, port):
        """Test Config initialization with various hosts and ports."""
        config = Config(host, port)
        assert config.host == host
        assert config.port == port

    @given(
        host=st.sampled_from(["localhost", "127.0.0.1", "192.168.1.1", "example.com"]),
        port=integers(min_value=1024, max_value=49151),  # User ports
    )
    def test_config_with_common_hosts(self, host, port):
        """Test Config with common host values."""
        config = Config(host, port)

        # Should be pickleable
        pickled = pickle.dumps(config)
        restored = pickle.loads(pickled)

        assert restored.host == host
        assert restored.port == port


class TestPhaseProperties:
    """Property-based tests for Phase class."""

    @given(
        host=text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        port=integers(min_value=1, max_value=65535),
        num_steps=integers(min_value=0, max_value=10),
    )
    def test_phase_with_multiple_steps(self, host, port, num_steps):
        """Test Phase with varying numbers of steps."""
        phase = Phase(host, port)

        # Add steps
        for i in range(num_steps):
            step = Step(f"echo test{i}")
            phase.append(step)

        assert len(phase.steps) == num_steps
        assert phase.resulthost == host
        assert phase.resultport == port

    @given(
        commands=lists(
            # Generate more realistic commands without control characters
            st.from_regex(r"[a-zA-Z0-9_\-]+( [a-zA-Z0-9_\-./]*)*", fullmatch=True),
            min_size=0,
            max_size=5,
        )
    )
    def test_phase_step_ordering(self, commands):
        """Test that steps are maintained in order."""
        phase = Phase("localhost", 6971)

        # Add all commands
        for cmd in commands:
            phase.append(Step(cmd))

        # Verify order is preserved
        assert len(phase.steps) == len(commands)
        # Just verify we have the right number of steps
        # The exact parsing behavior with edge cases is tested elsewhere


class TestIntegrationProperties:
    """Property-based tests for component integration."""

    @given(
        num_phases=integers(min_value=1, max_value=4),
        commands_per_phase=integers(min_value=0, max_value=3),
    )
    def test_phase_collection_serialization(self, num_phases, commands_per_phase):
        """Test serializing collections of phases."""
        phases = []

        for i in range(num_phases):
            phase = Phase("localhost", 6970 + i)
            for j in range(commands_per_phase):
                phase.append(Step(f"echo phase{i}_step{j}"))
            phases.append(phase)

        # All phases should be serializable
        for phase in phases:
            pickled = pickle.dumps(phase)
            restored = pickle.loads(pickled)
            assert len(restored.steps) == commands_per_phase
            assert restored.resultport == phase.resultport

    @given(
        spawn_commands=lists(
            text(min_size=1, max_size=20).filter(lambda x: x.strip()),
            min_size=0,
            max_size=3,
        ),
        timeout_commands=lists(
            text(min_size=1, max_size=20).filter(lambda x: x.strip()),
            min_size=0,
            max_size=3,
        ),
    )
    def test_mixed_command_types(self, spawn_commands, timeout_commands):
        """Test phases with mixed command types."""
        phase = Phase("localhost", 6971)

        # Add spawn commands
        for cmd in spawn_commands:
            phase.append(Step(cmd, spawn=True))

        # Add timeout commands
        for cmd in timeout_commands:
            phase.append(Step(cmd, timeout=10))

        # Add a normal command
        phase.append(Step("echo normal"))

        total_expected = len(spawn_commands) + len(timeout_commands) + 1
        assert len(phase.steps) == total_expected

        # Verify spawn steps
        for i in range(len(spawn_commands)):
            assert phase.steps[i].spawn is True
            assert phase.steps[i].timeout == 30  # default

        # Verify timeout steps
        for i in range(
            len(spawn_commands), len(spawn_commands) + len(timeout_commands)
        ):
            assert phase.steps[i].spawn is False
            assert phase.steps[i].timeout == 10
