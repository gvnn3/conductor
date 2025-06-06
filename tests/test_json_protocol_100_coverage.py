"""Tests to achieve 100% coverage for json_protocol.py."""
import pytest
from unittest.mock import Mock
import struct
import json

from conductor.json_protocol import (
    set_max_message_size,
    get_max_message_size,
    receive_message,
    ProtocolError,
    _recv_exactly,
    MSG_RESULT,
)


class TestJSONProtocolFullCoverage:
    """Test remaining edge cases for 100% coverage."""
    
    def test_set_max_message_size_zero(self):
        """Test setting message size to zero (line 34-35)."""
        with pytest.raises(ValueError, match="Message size limit must be positive"):
            set_max_message_size(0)
    
    def test_set_max_message_size_negative(self):
        """Test setting message size to negative value (line 34-35)."""
        with pytest.raises(ValueError, match="Message size limit must be positive"):
            set_max_message_size(-100)
    
    def test_set_and_get_max_message_size(self):
        """Test setting and getting valid message size (lines 28, 36)."""
        original = get_max_message_size()
        try:
            # Set new size
            set_max_message_size(50 * 1024 * 1024)  # 50MB
            assert get_max_message_size() == 50 * 1024 * 1024
            
            # Set another size
            set_max_message_size(200 * 1024 * 1024)  # 200MB
            assert get_max_message_size() == 200 * 1024 * 1024
        finally:
            # Restore original
            set_max_message_size(original)
    
    def test_receive_incomplete_length_header(self):
        """Test receiving incomplete length header (line 57)."""
        mock_socket = Mock()
        # _recv_exactly returns less than 4 bytes
        mock_socket.recv.side_effect = [b"\x00\x00", b""]  # Only 2 bytes, then EOF
        
        with pytest.raises(ProtocolError, match="Incomplete length header"):
            receive_message(mock_socket)
    
    def test_receive_incomplete_message_data(self):
        """Test receiving incomplete message data (line 70)."""
        mock_socket = Mock()
        # First recv returns 4-byte header for 100 byte message
        # Second recv returns only 50 bytes instead of 100
        mock_socket.recv.side_effect = [
            struct.pack("!I", 100),  # Length header
            b"x" * 50,  # Only half the data
            b""  # EOF
        ]
        
        with pytest.raises(ProtocolError, match="Incomplete message received"):
            receive_message(mock_socket)
    
    def test_receive_non_dict_json(self):
        """Test receiving JSON that's not a dictionary (line 78)."""
        mock_socket = Mock()
        # Create a JSON array instead of object
        json_data = json.dumps([1, 2, 3]).encode('utf-8')
        length_header = struct.pack("!I", len(json_data))
        
        mock_socket.recv.side_effect = [length_header, json_data]
        
        with pytest.raises(ProtocolError, match="Message must be a JSON object, not list"):
            receive_message(mock_socket)
    
    def test_receive_json_missing_version(self):
        """Test receiving JSON without version field (line 84)."""
        mock_socket = Mock()
        # Create JSON without version field
        json_data = json.dumps({"type": "test", "data": {}}).encode('utf-8')
        length_header = struct.pack("!I", len(json_data))
        
        mock_socket.recv.side_effect = [length_header, json_data]
        
        with pytest.raises(ProtocolError, match="Missing version field"):
            receive_message(mock_socket)
    
    def test_receive_wrong_protocol_version(self):
        """Test receiving JSON with wrong protocol version (line 87)."""
        mock_socket = Mock()
        # Create JSON with wrong version
        json_data = json.dumps({
            "version": 2,  # Wrong version (should be 1)
            "type": "test",
            "data": {}
        }).encode('utf-8')
        length_header = struct.pack("!I", len(json_data))
        
        mock_socket.recv.side_effect = [length_header, json_data]
        
        with pytest.raises(ProtocolError, match="Unsupported protocol version: 2"):
            receive_message(mock_socket)
    
    def test_recv_exactly_with_empty_socket(self):
        """Test _recv_exactly when socket returns empty immediately."""
        mock_socket = Mock()
        mock_socket.recv.return_value = b""
        
        result = _recv_exactly(mock_socket, 10)
        assert result == b""
        mock_socket.recv.assert_called_once_with(10)