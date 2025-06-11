"""Hypothesis-based property tests for JSON protocol."""

import socket
from hypothesis import given, strategies as st

from conductor.json_protocol import (
    send_message,
    receive_message,
    MSG_PHASE,
    MSG_RUN,
    MSG_RESULT,
    MSG_CONFIG,
    MSG_DONE,
    MSG_ERROR,
)


class TestJSONProtocolProperties:
    """Property-based tests for JSON protocol."""

    @given(
        msg_type=st.sampled_from(
            [MSG_PHASE, MSG_RUN, MSG_RESULT, MSG_CONFIG, MSG_DONE, MSG_ERROR]
        ),
        data=st.dictionaries(
            st.text(min_size=1, max_size=50),
            st.one_of(
                st.text(max_size=100),
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False),
                st.booleans(),
                st.none(),
            ),
            max_size=10,
        ),
    )
    def test_send_receive_roundtrip(self, msg_type, data):
        """Test that any valid message can be sent and received correctly."""
        # Create a socket pair for testing
        server_sock, client_sock = socket.socketpair()

        try:
            # Send message
            send_message(client_sock, msg_type, data)

            # Receive message
            received_type, received_data = receive_message(server_sock)

            # Verify
            assert received_type == msg_type
            assert received_data == data

        finally:
            server_sock.close()
            client_sock.close()

    @given(data=st.dictionaries(st.text(min_size=1), st.text(), min_size=1))
    def test_empty_strings_in_data(self, data):
        """Test that empty strings in data are handled correctly."""
        server_sock, client_sock = socket.socketpair()

        try:
            # Add empty string to data
            data["empty"] = ""

            send_message(client_sock, MSG_RESULT, data)
            msg_type, received_data = receive_message(server_sock)

            assert msg_type == MSG_RESULT
            assert received_data == data
            assert received_data["empty"] == ""

        finally:
            server_sock.close()
            client_sock.close()

    @given(
        msg_type=st.sampled_from([MSG_PHASE, MSG_RUN, MSG_RESULT]),
        nested_data=st.recursive(
            st.one_of(
                st.none(),
                st.booleans(),
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False),
                st.text(max_size=50),
            ),
            lambda children: st.one_of(
                st.lists(children, max_size=3),
                st.dictionaries(st.text(min_size=1, max_size=10), children, max_size=3),
            ),
            max_leaves=20,
        ),
    )
    def test_nested_data_structures(self, msg_type, nested_data):
        """Test that nested data structures are preserved correctly."""
        server_sock, client_sock = socket.socketpair()

        try:
            # Wrap in a dict if not already
            if not isinstance(nested_data, dict):
                data = {"nested": nested_data}
            else:
                data = nested_data

            send_message(client_sock, msg_type, data)
            received_type, received_data = receive_message(server_sock)

            assert received_type == msg_type
            assert received_data == data

        finally:
            server_sock.close()
            client_sock.close()
