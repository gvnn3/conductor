"""JSON-based protocol for conductor communication.

This module replaces pickle with a secure JSON protocol.
No backward compatibility with pickle is maintained.
"""

import json
import struct
import socket
from typing import Dict, Any, Tuple


# Protocol version
PROTOCOL_VERSION = 1

# Maximum message size (default 10MB)
_max_message_size = 10 * 1024 * 1024


class ProtocolError(Exception):
    """Raised when protocol errors occur."""

    pass


def get_max_message_size() -> int:
    """Get the current maximum message size limit."""
    return _max_message_size


def set_max_message_size(size: int) -> None:
    """Set the maximum message size limit."""
    global _max_message_size
    if size <= 0:
        raise ValueError("Message size limit must be positive")
    _max_message_size = size


def send_message(sock: socket.socket, msg_type: str, data: Dict[str, Any], max_message_size: int = None) -> None:
    """Send a JSON message with type and data."""
    if max_message_size is None:
        max_message_size = _max_message_size
        
    message = {"version": PROTOCOL_VERSION, "type": msg_type, "data": data}
    json_bytes = json.dumps(message).encode("utf-8")
    
    # Check message size
    if len(json_bytes) > max_message_size:
        raise ProtocolError(f"Message size ({len(json_bytes)} bytes) exceeds maximum ({max_message_size} bytes)")

    # Send 4-byte length header followed by JSON data
    length = struct.pack("!I", len(json_bytes))
    sock.sendall(length + json_bytes)


def receive_message(sock: socket.socket, max_message_size: int = None) -> Tuple[str, Dict[str, Any]]:
    """Receive a JSON message and return (type, data)."""
    if max_message_size is None:
        max_message_size = _max_message_size
        
    # Read 4-byte length header
    length_bytes = _recv_exactly(sock, 4)
    if not length_bytes:
        raise ProtocolError("Connection closed")

    if len(length_bytes) != 4:
        raise ProtocolError("Incomplete length header")

    length = struct.unpack("!I", length_bytes)[0]

    # Check against configured size limit
    if length > max_message_size:
        raise ProtocolError(
            f"Message too large: {length} bytes (max: {max_message_size})"
        )

    # Read JSON data
    json_bytes = _recv_exactly(sock, length)
    if len(json_bytes) != length:
        raise ProtocolError("Incomplete message received")

    # Parse JSON
    try:
        message = json.loads(json_bytes.decode("utf-8"))

        # Ensure message is a dictionary
        if not isinstance(message, dict):
            raise ProtocolError(
                f"Message must be a JSON object, not {type(message).__name__}"
            )

        # Check version
        if "version" not in message:
            raise ProtocolError("Missing version field")

        if message["version"] != PROTOCOL_VERSION:
            raise ProtocolError(f"Unsupported protocol version: {message['version']}")

        return message["type"], message["data"]
    except (json.JSONDecodeError, KeyError) as e:
        raise ProtocolError(f"Invalid message format: {e}")


def _recv_exactly(sock: socket.socket, length: int) -> bytes:
    """Receive exactly length bytes from socket."""
    data = b""
    while len(data) < length:
        chunk = sock.recv(min(4096, length - len(data)))
        if not chunk:
            break
        data += chunk
    return data


# Message type constants
MSG_PHASE = "phase"
MSG_RUN = "run"
MSG_CONFIG = "config"
MSG_RESULT = "result"
MSG_DONE = "done"
MSG_ERROR = "error"
