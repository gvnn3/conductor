"""Extended hypothesis tests for JSON protocol edge cases."""

import json
import struct
import socket
from hypothesis import given, strategies as st, assume
import pytest

from conductor.json_protocol import (
    send_message,
    receive_message,
    ProtocolError,
    MSG_RESULT,
    set_max_message_size,
    get_max_message_size,
    _recv_exactly,
)


class TestJSONProtocolExtendedEdgeCases:
    """Extended edge case tests for JSON protocol."""

    @given(size=st.integers(min_value=-1000, max_value=0))
    def test_set_max_message_size_negative_or_zero(self, size):
        """Test that setting negative or zero message size raises ValueError."""
        with pytest.raises(ValueError, match="Message size limit must be positive"):
            set_max_message_size(size)

    @given(size=st.integers(min_value=1, max_value=1000000000))
    def test_set_and_get_max_message_size(self, size):
        """Test that message size limit can be set and retrieved correctly."""
        original = get_max_message_size()
        try:
            set_max_message_size(size)
            assert get_max_message_size() == size
        finally:
            # Restore original
            set_max_message_size(original)

    def test_receive_empty_connection(self):
        """Test receiving from a socket that returns empty data."""
        # Create a mock socket that returns empty data
        server_sock, client_sock = socket.socketpair()

        try:
            # Close client side to simulate connection closed
            client_sock.close()

            with pytest.raises(ProtocolError, match="Connection closed"):
                receive_message(server_sock)

        finally:
            server_sock.close()

    @given(partial_length=st.integers(min_value=1, max_value=3))
    def test_receive_partial_length_header(self, partial_length):
        """Test receiving when length header is incomplete."""
        server_sock, client_sock = socket.socketpair()

        try:
            # Send partial length header
            partial_data = b"\x00" * partial_length
            client_sock.send(partial_data)
            client_sock.close()

            with pytest.raises(
                ProtocolError, match="Incomplete length header|Connection closed"
            ):
                receive_message(server_sock)

        finally:
            server_sock.close()

    @given(
        msg_type=st.text(min_size=0, max_size=100),
        data=st.dictionaries(
            st.text(min_size=0, max_size=50),
            st.text(min_size=0, max_size=50),
            max_size=10,
        ),
    )
    def test_empty_message_type_and_keys(self, msg_type, data):
        """Test edge cases with empty strings in message types and keys."""
        server_sock, client_sock = socket.socketpair()

        try:
            send_message(client_sock, msg_type, data)
            received_type, received_data = receive_message(server_sock)

            assert received_type == msg_type
            assert received_data == data

        finally:
            server_sock.close()
            client_sock.close()

    def test_receive_message_exactly_at_size_limit(self):
        """Test receiving a message exactly at the size limit."""
        original_limit = get_max_message_size()

        try:
            # Set a small limit for testing
            set_max_message_size(1024)

            # Create data that will result in a message just under the limit
            # Account for JSON overhead
            test_data = {"data": "x" * 900}  # Leave room for protocol overhead

            server_sock, client_sock = socket.socketpair()

            try:
                send_message(client_sock, MSG_RESULT, test_data)
                msg_type, received_data = receive_message(server_sock)

                assert msg_type == MSG_RESULT
                assert received_data == test_data

            finally:
                server_sock.close()
                client_sock.close()

        finally:
            set_max_message_size(original_limit)

    def test_receive_message_one_byte_over_limit(self):
        """Test receiving a message one byte over the size limit."""
        server_sock, client_sock = socket.socketpair()

        try:
            # Manually craft a message with size just over limit
            original_limit = get_max_message_size()

            # Create length header for message 1 byte over limit
            over_limit_size = original_limit + 1
            length_header = struct.pack("!I", over_limit_size)

            # Send just the header
            client_sock.send(length_header)

            with pytest.raises(ProtocolError, match="Message too large"):
                receive_message(server_sock)

        finally:
            server_sock.close()
            client_sock.close()

    @given(json_str=st.text(min_size=1).filter(lambda x: not x.strip().startswith("{")))
    def test_receive_invalid_json_format(self, json_str):
        """Test receiving data that's not valid JSON."""
        assume(json_str)  # Skip empty strings

        server_sock, client_sock = socket.socketpair()

        try:
            # Send valid length header with invalid JSON
            json_bytes = json_str.encode("utf-8")
            length_header = struct.pack("!I", len(json_bytes))

            client_sock.send(length_header + json_bytes)

            with pytest.raises(
                ProtocolError,
                match="Invalid message format|Message must be a JSON object",
            ):
                receive_message(server_sock)

        finally:
            server_sock.close()
            client_sock.close()

    def test_receive_json_missing_version_field(self):
        """Test receiving JSON that's missing the version field."""
        server_sock, client_sock = socket.socketpair()

        try:
            # Create message without version field
            message = {"type": MSG_RESULT, "data": {"test": "data"}}
            json_bytes = json.dumps(message).encode("utf-8")
            length_header = struct.pack("!I", len(json_bytes))

            client_sock.send(length_header + json_bytes)

            with pytest.raises(ProtocolError, match="Missing version field"):
                receive_message(server_sock)

        finally:
            server_sock.close()
            client_sock.close()

    @given(version=st.integers(min_value=0, max_value=100).filter(lambda x: x != 1))
    def test_receive_unsupported_protocol_version(self, version):
        """Test receiving message with unsupported protocol version."""
        server_sock, client_sock = socket.socketpair()

        try:
            # Create message with different version
            message = {"version": version, "type": MSG_RESULT, "data": {"test": "data"}}
            json_bytes = json.dumps(message).encode("utf-8")
            length_header = struct.pack("!I", len(json_bytes))

            client_sock.send(length_header + json_bytes)

            with pytest.raises(
                ProtocolError, match=f"Unsupported protocol version: {version}"
            ):
                receive_message(server_sock)

        finally:
            server_sock.close()
            client_sock.close()

    def test_receive_json_missing_type_field(self):
        """Test receiving JSON that's missing the type field."""
        server_sock, client_sock = socket.socketpair()

        try:
            # Create message without type field
            message = {"version": 1, "data": {"test": "data"}}
            json_bytes = json.dumps(message).encode("utf-8")
            length_header = struct.pack("!I", len(json_bytes))

            client_sock.send(length_header + json_bytes)

            with pytest.raises(ProtocolError, match="Invalid message format"):
                receive_message(server_sock)

        finally:
            server_sock.close()
            client_sock.close()

    def test_recv_exactly_partial_data(self):
        """Test _recv_exactly when socket returns partial data."""
        server_sock, client_sock = socket.socketpair()

        try:
            # Send data in small chunks
            test_data = b"Hello, World!"
            client_sock.send(test_data)

            # Receive exact amount
            received = _recv_exactly(server_sock, len(test_data))
            assert received == test_data

            # Try to receive more than available
            client_sock.close()
            partial = _recv_exactly(server_sock, 100)
            assert len(partial) < 100

        finally:
            server_sock.close()

    @given(
        special_chars=st.sampled_from(
            [
                "\x00",  # Null byte
                "\r\n",  # Carriage return + newline
                "\t",  # Tab
                "\x1b",  # Escape
                "\x7f",  # DEL
            ]
        )
    )
    def test_special_characters_in_message_data(self, special_chars):
        """Test that special characters are handled correctly in messages."""
        data = {"special": special_chars, "combined": f"text{special_chars}more"}

        server_sock, client_sock = socket.socketpair()

        try:
            send_message(client_sock, MSG_RESULT, data)
            msg_type, received_data = receive_message(server_sock)

            assert msg_type == MSG_RESULT
            assert received_data == data
            assert received_data["special"] == special_chars

        finally:
            server_sock.close()
            client_sock.close()
