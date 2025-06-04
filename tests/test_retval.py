"""Tests for the RetVal class."""

import pytest
from unittest.mock import MagicMock, patch
import pickle
import struct
import socket

from conductor.retval import RetVal, RETVAL_OK, RETVAL_ERROR, RETVAL_BAD_CMD, RETVAL_DONE


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
    
    def test_can_be_pickled(self):
        """Test that RetVal can be pickled and unpickled."""
        original = RetVal(code=42, message="Test message")
        pickled = pickle.dumps(original)
        unpickled = pickle.loads(pickled)
        
        assert unpickled.code == original.code
        assert unpickled.message == original.message
    
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
        length = socket.ntohl(struct.unpack('!I', length_bytes)[0])
        
        # Rest should be the pickled object
        pickled_data = sent_data[4:]
        assert len(pickled_data) == length
        
        # Verify we can unpickle it
        unpickled = pickle.loads(pickled_data)
        assert unpickled.code == 0
        assert unpickled.message == "Success"
    
    def test_send_with_different_return_codes(self):
        """Test sending with different standard return codes."""
        test_cases = [
            (RETVAL_OK, "OK"),
            (RETVAL_ERROR, "Error"),
            (RETVAL_BAD_CMD, "Bad command"),
            (RETVAL_DONE, "Done")
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
            length = socket.ntohl(struct.unpack('!I', length_bytes)[0])
            pickled_data = sent_data[4:]
            
            unpickled = pickle.loads(pickled_data)
            assert unpickled.code == code
            assert unpickled.message == message