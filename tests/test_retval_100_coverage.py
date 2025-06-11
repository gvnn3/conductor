"""Tests for improved retval.py validation."""
import pytest
from unittest.mock import Mock, patch
from conductor.retval import RetVal, RETVAL_ERROR, MSG_RESULT


class TestRetValValidation:
    """Test that RetVal properly validates inputs."""
    
    def test_code_must_be_integer(self):
        """Test that non-integer codes are rejected."""
        with pytest.raises(TypeError, match="RetVal code must be an integer"):
            RetVal(code="not-a-number", message="test")
        
        with pytest.raises(TypeError, match="RetVal code must be an integer"):
            RetVal(code=None, message="test")
        
        with pytest.raises(TypeError, match="RetVal code must be an integer"):
            RetVal(code=3.14, message="test")
    
    def test_message_must_be_string(self):
        """Test that non-string messages are rejected."""
        with pytest.raises(TypeError, match="RetVal message must be a string"):
            RetVal(code=0, message=123)
        
        with pytest.raises(TypeError, match="RetVal message must be a string"):
            RetVal(code=0, message=None)
        
        with pytest.raises(TypeError, match="RetVal message must be a string"):
            RetVal(code=0, message=['list', 'message'])
    
    def test_valid_retval_creation(self):
        """Test that valid RetVals work correctly."""
        # Default values
        rv1 = RetVal()
        assert rv1.code == 0
        assert rv1.message == ""
        
        # Explicit values
        rv2 = RetVal(code=42, message="Success")
        assert rv2.code == 42
        assert rv2.message == "Success"
        
        # Using constants
        rv3 = RetVal(RETVAL_ERROR, "An error occurred")
        assert rv3.code == RETVAL_ERROR
        assert rv3.message == "An error occurred"
    
    def test_send_simple_and_clean(self):
        """Test that send() is now simple and clean."""
        mock_socket = Mock()
        rv = RetVal(code=0, message="test")
        
        with patch('conductor.retval.send_message') as mock_send:
            rv.send(mock_socket)
            
            # Should be called exactly once with correct data
            mock_send.assert_called_once_with(
                mock_socket,
                MSG_RESULT,
                {"code": 0, "message": "test"}
            )