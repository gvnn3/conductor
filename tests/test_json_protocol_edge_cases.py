"""Hypothesis tests for JSON protocol edge cases."""

import socket
from hypothesis import given, strategies as st, settings
import pytest

from conductor.json_protocol import (
    send_message,
    receive_message,
    ProtocolError,
    MSG_PHASE,
    MSG_RESULT,
    set_max_message_size,
    get_max_message_size,
)


class TestJSONProtocolEdgeCases:
    """Edge case tests for JSON protocol."""

    @given(
        size_mb=st.sampled_from([0.1, 0.5, 1, 2, 5]),  # Test with smaller sizes
        msg_type=st.sampled_from([MSG_PHASE, MSG_RESULT]),
    )
    @settings(deadline=10000)  # 10 second deadline
    def test_near_size_limit_messages(self, size_mb, msg_type):
        """Test messages at various sizes."""
        import threading
        
        # Save original limit
        original_limit = get_max_message_size()

        try:
            # Set a 10MB limit for testing
            set_max_message_size(10 * 1024 * 1024)

            # Create data that will result in approximately the desired size
            # Account for JSON overhead (quotes, etc.)
            target_size = int(size_mb * 1024 * 1024)
            string_size = max(1, target_size - 100)  # Leave room for JSON structure

            data = {"large_field": "x" * string_size}

            server_sock, client_sock = socket.socketpair()
            # Set socket buffers to handle large messages
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 10 * 1024 * 1024)
            client_sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 10 * 1024 * 1024)

            try:
                # This should work for sizes under 10MB
                if size_mb <= 10:
                    # Use threading to avoid deadlock on large messages
                    received_data_holder = []
                    received_type_holder = []
                    exception_holder = []
                    
                    def receive_thread():
                        try:
                            msg_type, data = receive_message(server_sock)
                            received_type_holder.append(msg_type)
                            received_data_holder.append(data)
                        except Exception as e:
                            exception_holder.append(e)
                    
                    thread = threading.Thread(target=receive_thread)
                    thread.start()
                    
                    send_message(client_sock, msg_type, data)
                    
                    thread.join(timeout=5.0)
                    if thread.is_alive():
                        raise Exception("Receive thread timed out")
                    
                    if exception_holder:
                        raise exception_holder[0]
                    
                    assert received_type_holder[0] == msg_type
                    assert len(received_data_holder[0]["large_field"]) == string_size
                else:
                    # For sizes over 10MB, we expect it to fail on receive
                    send_message(client_sock, msg_type, data)
                    with pytest.raises(ProtocolError, match="Message too large"):
                        receive_message(server_sock)

            finally:
                server_sock.close()
                client_sock.close()

        finally:
            # Restore original limit
            set_max_message_size(original_limit)

    @given(
        text=st.one_of(
            st.text(alphabet="🚀💥🎯🔥⚡️🌟💫✨", min_size=1, max_size=50),  # Emoji
            st.text(
                alphabet="مرحبا世界שלום", min_size=1, max_size=50
            ),  # RTL/International
            st.text(
                alphabet="\u200b\u200c\u200d\ufeff", min_size=1, max_size=10
            ),  # Zero-width
        )
    )
    def test_unicode_and_special_characters(self, text):
        """Test handling of Unicode and special characters."""
        data = {"unicode_text": text, "mixed": f"Hello {text} World"}

        server_sock, client_sock = socket.socketpair()

        try:
            send_message(client_sock, MSG_RESULT, data)
            msg_type, received_data = receive_message(server_sock)

            assert msg_type == MSG_RESULT
            assert received_data == data
            assert received_data["unicode_text"] == text

        finally:
            server_sock.close()
            client_sock.close()

    @given(depth=st.integers(min_value=10, max_value=100))
    def test_deeply_nested_structures(self, depth):
        """Test deeply nested JSON structures."""
        # Build a deeply nested structure
        data = {"value": "bottom"}
        for _ in range(depth):
            data = {"nested": data}

        server_sock, client_sock = socket.socketpair()

        try:
            send_message(client_sock, MSG_RESULT, data)
            msg_type, received_data = receive_message(server_sock)

            assert msg_type == MSG_RESULT

            # Verify the structure is preserved
            current = received_data
            for _ in range(depth):
                assert "nested" in current
                current = current["nested"]
            assert current == {"value": "bottom"}

        finally:
            server_sock.close()
            client_sock.close()

    @given(
        num_keys=st.integers(min_value=1000, max_value=10000),
        key_size=st.integers(min_value=10, max_value=50),
    )
    @settings(deadline=5000)  # Give more time for large dictionaries
    def test_many_keys_in_dictionary(self, num_keys, key_size):
        """Test dictionaries with many keys."""
        # Create a dictionary with many keys
        data = {f"key_{i:0{key_size}d}": f"value_{i}" for i in range(num_keys)}

        server_sock, client_sock = socket.socketpair()

        try:
            send_message(client_sock, MSG_RESULT, data)
            msg_type, received_data = receive_message(server_sock)

            assert msg_type == MSG_RESULT
            assert len(received_data) == num_keys

            # Spot check a few keys
            for i in [0, num_keys // 2, num_keys - 1]:
                key = f"key_{i:0{key_size}d}"
                assert key in received_data
                assert received_data[key] == f"value_{i}"

        finally:
            server_sock.close()
            client_sock.close()

    def test_empty_data_payload(self):
        """Test sending empty data dictionary."""
        server_sock, client_sock = socket.socketpair()

        try:
            send_message(client_sock, MSG_RESULT, {})
            msg_type, received_data = receive_message(server_sock)

            assert msg_type == MSG_RESULT
            assert received_data == {}

        finally:
            server_sock.close()
            client_sock.close()

    @given(list_size=st.integers(min_value=1000, max_value=5000))
    @settings(deadline=5000)
    def test_large_lists_in_data(self, list_size):
        """Test data containing large lists."""
        data = {
            "numbers": list(range(list_size)),
            "strings": [f"item_{i}" for i in range(list_size // 10)],
        }

        server_sock, client_sock = socket.socketpair()

        try:
            send_message(client_sock, MSG_PHASE, data)
            msg_type, received_data = receive_message(server_sock)

            assert msg_type == MSG_PHASE
            assert len(received_data["numbers"]) == list_size
            assert received_data["numbers"][0] == 0
            assert received_data["numbers"][-1] == list_size - 1
            assert len(received_data["strings"]) == list_size // 10

        finally:
            server_sock.close()
            client_sock.close()
