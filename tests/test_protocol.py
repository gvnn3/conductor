"""Tests for the JSON protocol implementation."""

import json
import struct
import pytest
from unittest.mock import Mock, patch

from conductor.protocol import (
    Message,
    MessageType,
    ProtocolError,
    send_json_message,
    receive_json_message,
    phase_to_dict,
    step_to_dict,
    result_to_dict,
    phase_from_dict,
    step_from_dict,
    retval_from_dict,
    ProtocolHandler,
)
from conductor.phase import Phase
from conductor.step import Step
from conductor.retval import RetVal


class TestMessage:
    """Test Message class."""

    def test_message_creation(self):
        """Test creating a message."""
        msg = Message(MessageType.PHASE, {"test": "data"})
        assert msg.type == MessageType.PHASE
        assert msg.payload == {"test": "data"}
        assert msg.version == 1

    def test_message_to_json(self):
        """Test serializing message to JSON."""
        msg = Message(MessageType.RUN, {"command": "execute"})
        json_str = msg.to_json()
        data = json.loads(json_str)

        assert data["version"] == 1
        assert data["type"] == "run"
        assert data["payload"] == {"command": "execute"}

    def test_message_from_json(self):
        """Test deserializing message from JSON."""
        json_str = (
            '{"version": 1, "type": "result", "payload": {"code": 0, "message": "OK"}}'
        )
        msg = Message.from_json(json_str)

        assert msg.version == 1
        assert msg.type == MessageType.RESULT
        assert msg.payload == {"code": 0, "message": "OK"}

    def test_message_from_invalid_json(self):
        """Test deserializing invalid JSON raises error."""
        with pytest.raises(ProtocolError):
            Message.from_json("not json")

        with pytest.raises(ProtocolError):
            Message.from_json('{"type": "phase"}')  # Missing fields


class TestNetworkFunctions:
    """Test network send/receive functions."""

    def test_send_json_message(self):
        """Test sending a JSON message."""
        mock_socket = Mock()
        msg = Message(MessageType.CONFIG, {"setting": "value"})

        send_json_message(mock_socket, msg)

        # Check that sendall was called with length prefix + data
        call_args = mock_socket.sendall.call_args[0][0]
        length = struct.unpack("!I", call_args[:4])[0]
        data = call_args[4:]

        assert length == len(data)
        parsed = json.loads(data.decode("utf-8"))
        assert parsed["type"] == "config"
        assert parsed["payload"] == {"setting": "value"}

    def test_receive_json_message(self):
        """Test receiving a JSON message."""
        # Prepare test data
        msg = Message(MessageType.ERROR, {"error": "test error"})
        json_data = msg.to_json().encode("utf-8")
        length_prefix = struct.pack("!I", len(json_data))

        # Mock socket that returns our data
        mock_socket = Mock()
        mock_socket.recv.side_effect = [
            length_prefix,  # First call returns length
            json_data,  # Second call returns message
        ]

        received = receive_json_message(mock_socket)

        assert received.type == MessageType.ERROR
        assert received.payload == {"error": "test error"}

    def test_receive_message_too_large(self):
        """Test receiving a message that's too large."""
        mock_socket = Mock()
        # Send a length that's too large (11MB)
        mock_socket.recv.return_value = struct.pack("!I", 11 * 1024 * 1024)

        with pytest.raises(ProtocolError, match="Message too large"):
            receive_json_message(mock_socket)


class TestConverters:
    """Test object to/from dict converters."""

    def test_step_conversion(self):
        """Test converting Step objects."""
        step = Step("echo test", spawn=True, timeout=30)

        # To dict
        d = step_to_dict(step)
        assert d["args"] == "echo test"
        assert d["spawn"] is True
        assert d["timeout"] == 30

        # From dict
        step2 = step_from_dict(d)
        assert step2.args == "echo test"
        assert step2.spawn is True
        assert step2.timeout == 30

    def test_retval_conversion(self):
        """Test converting RetVal objects."""
        retval = RetVal(0, "Success")

        # To dict
        d = result_to_dict(retval)
        assert d["code"] == 0
        assert d["message"] == "Success"

        # From dict
        retval2 = retval_from_dict(d)
        assert retval2.code == 0
        assert retval2.message == "Success"

    def test_phase_conversion(self):
        """Test converting Phase objects."""
        phase = Phase("localhost", 6971)
        phase.append(Step("command1"))
        phase.append(Step("command2", spawn=True))

        # To dict
        d = phase_to_dict(phase)
        assert d["resulthost"] == "localhost"
        assert d["resultport"] == 6971
        assert len(d["steps"]) == 2
        assert d["steps"][0]["args"] == "command1"
        assert d["steps"][1]["spawn"] is True

        # From dict
        phase2 = phase_from_dict(d)
        assert phase2.resulthost == "localhost"
        assert phase2.resultport == 6971
        assert len(phase2.steps) == 2


class TestProtocolHandler:
    """Test the protocol handler for backward compatibility."""

    def test_json_protocol_send_phase(self):
        """Test sending a Phase with JSON protocol."""
        handler = ProtocolHandler("json")
        mock_socket = Mock()

        phase = Phase("127.0.0.1", 8080)
        phase.append(Step("test command"))

        handler.send(mock_socket, phase)

        # Verify JSON message was sent
        call_args = mock_socket.sendall.call_args[0][0]
        length = struct.unpack("!I", call_args[:4])[0]
        data = json.loads(call_args[4:].decode("utf-8"))

        assert data["type"] == "phase"
        assert data["payload"]["resulthost"] == "127.0.0.1"
        assert data["payload"]["resultport"] == 8080

    def test_json_protocol_send_retval(self):
        """Test sending a RetVal with JSON protocol."""
        handler = ProtocolHandler("json")
        mock_socket = Mock()

        retval = RetVal(0, "All good")
        handler.send(mock_socket, retval)

        # Verify JSON message was sent
        call_args = mock_socket.sendall.call_args[0][0]
        data = json.loads(call_args[4:].decode("utf-8"))

        assert data["type"] == "result"
        assert data["payload"]["code"] == 0
        assert data["payload"]["message"] == "All good"

    @patch("conductor.protocol.pickle")
    def test_pickle_protocol_fallback(self, mock_pickle):
        """Test pickle protocol for backward compatibility."""
        handler = ProtocolHandler("pickle")
        mock_socket = Mock()

        phase = Phase("localhost", 9999)
        mock_pickle.dumps.return_value = b"pickled_data"

        handler.send(mock_socket, phase)

        # Verify pickle was used
        mock_pickle.dumps.assert_called_once()
        mock_socket.sendall.assert_called_with(b"pickled_data")

    def test_invalid_protocol(self):
        """Test invalid protocol raises error."""
        with pytest.raises(ValueError):
            ProtocolHandler("xml")


class TestProtocolSecurity:
    """Test security aspects of the protocol."""

    def test_no_code_execution(self):
        """Test that JSON protocol cannot execute code."""
        # Create a malicious payload that would execute code in pickle
        malicious_json = json.dumps(
            {
                "version": 1,
                "type": "phase",
                "payload": {"__reduce__": ["os.system", ["echo hacked"]], "steps": []},
            }
        )

        # This should safely parse without executing anything
        msg = Message.from_json(malicious_json)
        assert "__reduce__" in msg.payload  # It's just data

        # Converting to phase should ignore the malicious field
        phase = phase_from_dict(msg.payload)
        assert len(phase.steps) == 0
