"""Tests for the JSON protocol implementation."""

import json
import socket
import struct
import pytest
from unittest.mock import Mock

from conductor.json_protocol import (
    send_message,
    receive_message,
    ProtocolError,
    MSG_PHASE,
    MSG_RUN,
    MSG_CONFIG,
    MSG_RESULT,
    MSG_DONE,
    MSG_ERROR,
)


class TestJSONProtocolMaxMessageSize:
    """Test configurable max message size in JSON protocol."""
    
    def test_send_message_with_custom_size_limit(self):
        """Test send_message respects custom size limit."""
        mock_socket = Mock()
        
        # Create a message that's about 2MB
        large_data = 'x' * (2 * 1024 * 1024)
        message = {'data': large_data}
        
        # Should fail with 1MB limit
        with pytest.raises(ProtocolError) as cm:
            send_message(mock_socket, MSG_PHASE, message, max_message_size=1*1024*1024)
        assert "exceeds maximum" in str(cm.value)
    
    def test_receive_message_with_custom_size_limit(self):
        """Test receive_message respects custom size limit."""
        # Create mock socket with 2MB message
        large_data = 'x' * (2 * 1024 * 1024)
        message = {
            'version': 1,
            'type': 'phase',
            'data': {'data': large_data}
        }
        json_data = json.dumps(message).encode('utf-8')
        length = struct.pack('>I', len(json_data))
        
        mock_socket = Mock()
        mock_socket.recv.side_effect = [length, json_data]
        
        # Should fail with 1MB limit
        with pytest.raises(ProtocolError) as cm:
            receive_message(mock_socket, max_message_size=1*1024*1024)
        assert "Message too large" in str(cm.value)
    
    def test_default_size_limit_10mb(self):
        """Test default size limit is 10MB."""
        mock_socket = Mock()
        
        # Create a message that's about 11MB (should fail with default)
        large_data = 'x' * (11 * 1024 * 1024)
        message = {'data': large_data}
        
        with pytest.raises(ProtocolError) as cm:
            send_message(mock_socket, MSG_PHASE, message)
        assert "exceeds maximum" in str(cm.value)
    
    def test_size_limit_in_megabytes(self):
        """Test that size limit accepts value in megabytes."""
        mock_socket = Mock()
        
        # 5MB message should pass with 10MB limit
        data_5mb = 'x' * (5 * 1024 * 1024)
        message = {'data': data_5mb}
        
        # This should succeed (no exception)
        send_message(mock_socket, MSG_PHASE, message, max_message_size=10*1024*1024)
        
        # But fail with 3MB limit
        with pytest.raises(ProtocolError):
            send_message(mock_socket, MSG_PHASE, message, max_message_size=3*1024*1024)


class TestJSONProtocol:
    """Test the JSON protocol functions."""

    def test_send_message(self):
        """Test sending a JSON message."""
        mock_socket = Mock()

        send_message(mock_socket, MSG_PHASE, {"test": "data"})

        # Verify sendall was called
        assert mock_socket.sendall.called
        call_data = mock_socket.sendall.call_args[0][0]

        # Check length prefix
        length = struct.unpack("!I", call_data[:4])[0]
        json_data = call_data[4:]
        assert length == len(json_data)

        # Check JSON content
        message = json.loads(json_data.decode("utf-8"))
        assert message["version"] == 1
        assert message["type"] == MSG_PHASE
        assert message["data"] == {"test": "data"}

    def test_receive_message(self):
        """Test receiving a JSON message."""
        # Prepare test message with version
        test_msg = {
            "version": 1,
            "type": MSG_RESULT,
            "data": {"code": 0, "message": "OK"},
        }
        json_bytes = json.dumps(test_msg).encode("utf-8")
        length_prefix = struct.pack("!I", len(json_bytes))

        # Mock socket that returns our data
        mock_socket = Mock()
        mock_socket.recv.side_effect = [length_prefix, json_bytes]

        msg_type, data = receive_message(mock_socket)

        assert msg_type == MSG_RESULT
        assert data == {"code": 0, "message": "OK"}

    def test_receive_empty_message(self):
        """Test receiving when connection is closed."""
        mock_socket = Mock()
        mock_socket.recv.return_value = b""

        with pytest.raises(ProtocolError, match="Connection closed"):
            receive_message(mock_socket)

    def test_receive_message_too_large(self):
        """Test receiving a message that exceeds size limit."""
        mock_socket = Mock()
        # 101MB message size (exceeds default 100MB limit)
        mock_socket.recv.return_value = struct.pack("!I", 101 * 1024 * 1024)

        with pytest.raises(ProtocolError, match="Message too large"):
            receive_message(mock_socket)

    def test_receive_invalid_json(self):
        """Test receiving invalid JSON data."""
        mock_socket = Mock()
        invalid_json = b"not valid json"
        length_prefix = struct.pack("!I", len(invalid_json))

        mock_socket.recv.side_effect = [length_prefix, invalid_json]

        with pytest.raises(ProtocolError, match="Invalid message format"):
            receive_message(mock_socket)

    def test_message_types(self):
        """Test all message type constants are defined."""
        assert MSG_PHASE == "phase"
        assert MSG_RUN == "run"
        assert MSG_CONFIG == "config"
        assert MSG_RESULT == "result"
        assert MSG_DONE == "done"
        assert MSG_ERROR == "error"

    def test_round_trip(self):
        """Test sending and receiving a message."""
        # Create a pair of connected sockets
        server_sock, client_sock = socket.socketpair()

        try:
            # Send a message
            test_data = {
                "steps": [{"command": "echo test", "spawn": False}],
                "resulthost": "localhost",
                "resultport": 9999,
            }
            send_message(client_sock, MSG_PHASE, test_data)

            # Receive it
            msg_type, received_data = receive_message(server_sock)

            assert msg_type == MSG_PHASE
            assert received_data == test_data

        finally:
            server_sock.close()
            client_sock.close()


class TestJSONProtocolIntegration:
    """Integration tests with actual conductor objects."""

    def test_retval_json_send(self):
        """Test that RetVal can be sent as JSON."""
        from conductor.retval import RetVal

        mock_socket = Mock()
        retval = RetVal(0, "Test successful")
        retval.send(mock_socket)

        # Verify JSON was sent
        assert mock_socket.sendall.called
        call_data = mock_socket.sendall.call_args[0][0]

        # Skip length prefix and parse JSON
        json_data = call_data[4:]
        message = json.loads(json_data.decode("utf-8"))

        assert message["type"] == MSG_RESULT
        assert message["data"]["code"] == 0
        assert message["data"]["message"] == "Test successful"
