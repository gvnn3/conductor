"""Tests for the RetVal class."""

from unittest.mock import MagicMock
import json
import struct
import socket

from conductor.retval import (
    RetVal,
    RETVAL_OK,
    RETVAL_ERROR,
    RETVAL_BAD_CMD,
    RETVAL_DONE,
)


class TestRetValInitialization:
    """Test RetVal initialization and attributes."""

    def test_default_initialization(self):
        """Test default values when creating RetVal."""
        retval = RetVal()
        assert retval.code == 0
        assert retval.message == ""

    def test_initialization_with_values(self):
        """Test initialization with specific values."""
        retval = RetVal(code=1, message="Error occurred")
        assert retval.code == 1
        assert retval.message == "Error occurred"

    def test_constants_are_correct(self):
        """Test that constants have correct values."""
        assert RETVAL_OK == 0
        assert RETVAL_ERROR == 1
        assert RETVAL_BAD_CMD == 2
        assert RETVAL_DONE == 65535


class TestRetValSerialization:
    """Test RetVal serialization and network sending."""

    def test_can_be_json_serialized(self):
        """Test that RetVal can be converted to and from JSON."""
        original = RetVal(code=42, message="Test message")
        
        # Simulate what happens in send()
        data = {
            "code": original.code,
            "message": original.message
        }
        json_str = json.dumps({"type": "result", "data": data})
        
        # Parse it back
        parsed = json.loads(json_str)
        assert parsed["type"] == "result"
        assert parsed["data"]["code"] == 42
        assert parsed["data"]["message"] == "Test message"

    def test_send_formats_message_correctly(self):
        """Test that send() formats the message with length prefix."""
        retval = RetVal(code=0, message="Success")
        mock_socket = MagicMock()

        retval.send(mock_socket)

        # Verify sendall was called once
        mock_socket.sendall.assert_called_once()

        # Get the data that was sent
        sent_data = mock_socket.sendall.call_args[0][0]

        # First 4 bytes should be the length
        length_bytes = sent_data[:4]
        length = struct.unpack("!I", length_bytes)[0]

        # Rest should be the JSON data
        json_data = sent_data[4:]
        assert len(json_data) == length

        # Verify we can parse the JSON
        message = json.loads(json_data.decode('utf-8'))
        assert message["type"] == "result"
        assert message["data"]["code"] == 0
        assert message["data"]["message"] == "Success"

    def test_send_with_different_return_codes(self):
        """Test sending with different standard return codes."""
        test_cases = [
            (RETVAL_OK, "OK"),
            (RETVAL_ERROR, "Error"),
            (RETVAL_BAD_CMD, "Bad command"),
            (RETVAL_DONE, "Done"),
        ]

        for code, message in test_cases:
            retval = RetVal(code=code, message=message)
            mock_socket = MagicMock()

            retval.send(mock_socket)

            # Verify data was sent
            mock_socket.sendall.assert_called_once()
            sent_data = mock_socket.sendall.call_args[0][0]

            # Verify we can recover the original data
            length_bytes = sent_data[:4]
            length = struct.unpack("!I", length_bytes)[0]
            json_data = sent_data[4:]
            
            # Parse JSON
            message_obj = json.loads(json_data.decode('utf-8'))
            assert message_obj["type"] == "result"
            assert message_obj["data"]["code"] == code
            assert message_obj["data"]["message"] == message
