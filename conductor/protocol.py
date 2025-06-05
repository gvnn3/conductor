"""JSON-based protocol for conductor communication.

This module provides secure JSON-based network communication
between conductor and players.
"""

import json
import struct
import socket
from enum import Enum
from typing import Dict, Any


class MessageType(Enum):
    """Types of messages in the conductor protocol."""

    PHASE = "phase"
    RUN = "run"
    CONFIG = "config"
    RESULT = "result"
    ERROR = "error"


class ProtocolError(Exception):
    """Raised when protocol errors occur."""

    pass


class Message:
    """Base message class for conductor protocol."""

    def __init__(
        self, msg_type: MessageType, payload: Dict[str, Any], version: int = 1
    ):
        self.type = msg_type
        self.payload = payload
        self.version = version

    def to_json(self) -> str:
        """Serialize message to JSON string."""
        return json.dumps(
            {"version": self.version, "type": self.type.value, "payload": self.payload},
            separators=(",", ":"),
        )  # Compact JSON

    @classmethod
    def from_json(cls, data: str) -> "Message":
        """Deserialize message from JSON string."""
        try:
            obj = json.loads(data)
            if "version" not in obj or "type" not in obj or "payload" not in obj:
                raise ProtocolError("Invalid message format")
            return cls(MessageType(obj["type"]), obj["payload"], obj["version"])
        except (json.JSONDecodeError, ValueError) as e:
            raise ProtocolError(f"Failed to parse message: {e}")


def send_json_message(sock: socket.socket, message: Message) -> None:
    """Send a JSON message with length prefix."""
    data = message.to_json().encode("utf-8")
    length = struct.pack("!I", len(data))
    sock.sendall(length + data)


def receive_json_message(sock: socket.socket) -> Message:
    """Receive a JSON message with length prefix."""
    # Read length header
    length_data = _recv_exactly(sock, 4)
    if len(length_data) < 4:
        raise ProtocolError("Connection closed while reading length")

    length = struct.unpack("!I", length_data)[0]

    # Sanity check length
    if length > 10 * 1024 * 1024:  # 10MB max
        raise ProtocolError(f"Message too large: {length} bytes")

    # Read message data
    data = _recv_exactly(sock, length)
    if len(data) < length:
        raise ProtocolError("Connection closed while reading message")

    return Message.from_json(data.decode("utf-8"))


def _recv_exactly(sock: socket.socket, length: int) -> bytes:
    """Receive exactly length bytes from socket."""
    data = b""
    while len(data) < length:
        chunk = sock.recv(min(4096, length - len(data)))
        if not chunk:
            break
        data += chunk
    return data


# Converter functions for existing objects


def phase_to_dict(phase) -> Dict[str, Any]:
    """Convert a Phase object to a dictionary."""
    return {
        "steps": [step_to_dict(step) for step in phase.steps],
        "resulthost": phase.resulthost,
        "resultport": phase.resultport,
        "results": [result_to_dict(r) for r in phase.results],
    }


def step_to_dict(step) -> Dict[str, Any]:
    """Convert a Step object to a dictionary."""
    return {"args": step.args, "spawn": step.spawn, "timeout": step.timeout}


def result_to_dict(result) -> Dict[str, Any]:
    """Convert a result (RetVal) to a dictionary."""
    return {"code": result.code, "message": result.message}


def retval_from_dict(data: Dict[str, Any]):
    """Create a RetVal object from a dictionary."""
    from conductor.retval import RetVal

    return RetVal(data.get("code", 0), data.get("message", ""))


def step_from_dict(data: Dict[str, Any]):
    """Create a Step object from a dictionary."""
    from conductor.step import Step

    # Reconstruct command string from args list
    import shlex

    command = (
        shlex.join(data["args"]) if isinstance(data["args"], list) else data["args"]
    )
    return Step(
        command, spawn=data.get("spawn", False), timeout=data.get("timeout", None)
    )


def phase_from_dict(data: Dict[str, Any]):
    """Create a Phase object from a dictionary."""
    from conductor.phase import Phase

    phase = Phase(data["resulthost"], data["resultport"])
    for step_data in data.get("steps", []):
        phase.append(step_from_dict(step_data))
    # Note: results are not deserialized as they're typically only sent back
    return phase


# JSON-only protocol handler


class ProtocolHandler:
    """Handles JSON protocol for conductor communication."""

    def __init__(self, protocol: str = "json"):
        self.protocol = protocol
        if protocol != "json":
            raise ValueError(f"Only JSON protocol is supported, got: {protocol}")

    def send(self, sock: socket.socket, obj: Any) -> None:
        """Send an object using JSON protocol."""
        # Convert object to JSON message
        if hasattr(obj, "__class__"):
            class_name = obj.__class__.__name__
            if class_name == "Phase":
                msg = Message(MessageType.PHASE, phase_to_dict(obj))
            elif class_name == "Run":
                msg = Message(MessageType.RUN, {})
            elif class_name == "Config":
                msg = Message(MessageType.CONFIG, {"data": str(obj)})
            elif class_name == "RetVal":
                msg = Message(MessageType.RESULT, result_to_dict(obj))
            else:
                raise ProtocolError(f"Unknown object type: {class_name}")
            send_json_message(sock, msg)
        else:
            raise ProtocolError("Cannot serialize object")

    def receive(self, sock: socket.socket) -> Any:
        """Receive an object using JSON protocol."""
        msg = receive_json_message(sock)
        # Convert JSON message to object
        if msg.type == MessageType.PHASE:
            return phase_from_dict(msg.payload)
        elif msg.type == MessageType.RUN:
            from conductor.run import Run

            return Run()
        elif msg.type == MessageType.CONFIG:
            from conductor.config import Config

            return Config()  # Would need proper deserialization
        elif msg.type == MessageType.RESULT:
            return retval_from_dict(msg.payload)
        else:
            raise ProtocolError(f"Unknown message type: {msg.type}")
