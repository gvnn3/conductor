"""Tests for JSON protocol versioning and configuration."""

import json
import struct
import pytest
from unittest.mock import Mock

from conductor.json_protocol import (
    send_message,
    receive_message,
    ProtocolError,
    MSG_PHASE,
    MSG_RESULT,
    set_max_message_size,
    get_max_message_size,
)


class TestProtocolVersion:
    """Test protocol versioning."""

    def test_message_includes_version(self):
        """Test that sent messages include a version field."""
        mock_socket = Mock()

        send_message(mock_socket, MSG_PHASE, {"test": "data"})

        # Get the sent data
        call_data = mock_socket.sendall.call_args[0][0]
        json_data = call_data[4:]  # Skip length header
        message = json.loads(json_data.decode("utf-8"))

        # Check version field exists
        assert "version" in message
        assert message["version"] == 1  # Default version

    def test_receive_message_with_version(self):
        """Test receiving messages with version field."""
        # Create a versioned message
        test_msg = {
            "version": 1,
            "type": MSG_RESULT,
            "data": {"code": 0, "message": "OK"},
        }
        json_bytes = json.dumps(test_msg).encode("utf-8")
        length_prefix = struct.pack("!I", len(json_bytes))

        # Mock socket
        mock_socket = Mock()
        mock_socket.recv.side_effect = [length_prefix, json_bytes]

        msg_type, data = receive_message(mock_socket)

        assert msg_type == MSG_RESULT
        assert data == {"code": 0, "message": "OK"}

    def test_receive_message_without_version_fails(self):
        """Test that messages without version field are rejected."""
        # Create message without version
        test_msg = {"type": MSG_RESULT, "data": {"code": 0, "message": "OK"}}
        json_bytes = json.dumps(test_msg).encode("utf-8")
        length_prefix = struct.pack("!I", len(json_bytes))

        # Mock socket
        mock_socket = Mock()
        mock_socket.recv.side_effect = [length_prefix, json_bytes]

        with pytest.raises(ProtocolError, match="Missing version field"):
            receive_message(mock_socket)

    def test_incompatible_version_rejected(self):
        """Test that incompatible versions are rejected."""
        # Create message with future version
        test_msg = {
            "version": 999,
            "type": MSG_RESULT,
            "data": {"code": 0, "message": "OK"},
        }
        json_bytes = json.dumps(test_msg).encode("utf-8")
        length_prefix = struct.pack("!I", len(json_bytes))

        # Mock socket
        mock_socket = Mock()
        mock_socket.recv.side_effect = [length_prefix, json_bytes]

        with pytest.raises(ProtocolError, match="Unsupported protocol version"):
            receive_message(mock_socket)


class TestMessageSizeLimit:
    """Test configurable message size limits."""

    def test_default_size_limit(self):
        """Test default size limit is 100MB."""
        assert get_max_message_size() == 100 * 1024 * 1024

    def test_set_size_limit(self):
        """Test setting custom size limit."""
        original = get_max_message_size()
        try:
            # Set to 50MB
            set_max_message_size(50 * 1024 * 1024)
            assert get_max_message_size() == 50 * 1024 * 1024
        finally:
            # Restore original
            set_max_message_size(original)

    def test_receive_message_with_custom_limit(self):
        """Test that custom size limit is enforced."""
        original = get_max_message_size()
        try:
            # Set to 1KB for testing
            set_max_message_size(1024)

            mock_socket = Mock()
            # Try to receive 2KB message
            mock_socket.recv.return_value = struct.pack("!I", 2048)

            with pytest.raises(ProtocolError, match="Message too large"):
                receive_message(mock_socket)
        finally:
            set_max_message_size(original)

    def test_size_limit_validation(self):
        """Test that invalid size limits are rejected."""
        with pytest.raises(ValueError, match="Message size limit must be positive"):
            set_max_message_size(0)

        with pytest.raises(ValueError, match="Message size limit must be positive"):
            set_max_message_size(-1)
