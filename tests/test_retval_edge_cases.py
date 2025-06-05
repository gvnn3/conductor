"""Extended edge case tests for RetVal using hypothesis."""

import socket
from hypothesis import given, strategies as st, assume, settings
import pytest
from unittest.mock import MagicMock, patch

from conductor.retval import RetVal, RETVAL_OK, RETVAL_ERROR, RETVAL_BAD_CMD, RETVAL_DONE


class TestRetValExtendedEdgeCases:
    """Extended edge case tests for RetVal class."""
    
    @given(
        code=st.one_of(
            st.integers(),
            st.floats(),
            st.none(),
            st.text(),
            st.booleans(),
            st.lists(st.integers()),
            st.dictionaries(st.text(), st.integers())
        ),
        message=st.one_of(
            st.text(max_size=10000),
            st.none(),
            st.integers(),
            st.floats(),
            st.booleans(),
            st.lists(st.text()),
            st.dictionaries(st.text(), st.text()),
            st.binary()
        )
    )
    def test_retval_accepts_any_types(self, code, message):
        """Test that RetVal accepts any types without validation."""
        retval = RetVal(code, message)
        
        # Values should be stored as-is
        # Handle NaN special case (NaN != NaN)
        import math
        if isinstance(code, float) and math.isnan(code):
            assert isinstance(retval.code, float) and math.isnan(retval.code)
        else:
            assert retval.code == code
            
        if isinstance(message, float) and math.isnan(message):
            assert isinstance(retval.message, float) and math.isnan(retval.message)
        else:
            assert retval.message == message
    
    @given(
        code=st.integers(min_value=-1000000, max_value=1000000),
        message=st.text(min_size=0, max_size=10000)
    )
    def test_retval_with_various_codes_and_messages(self, code, message):
        """Test RetVal with various integer codes and string messages."""
        retval = RetVal(code, message)
        
        assert retval.code == code
        assert retval.message == message
    
    def test_retval_constants(self):
        """Test that RetVal constants have expected values."""
        assert RETVAL_OK == 0
        assert RETVAL_ERROR == 1
        assert RETVAL_BAD_CMD == 2
        assert RETVAL_DONE == 65535
        
        # Test using constants
        retvals = [
            RetVal(RETVAL_OK, "Success"),
            RetVal(RETVAL_ERROR, "Failed"),
            RetVal(RETVAL_BAD_CMD, "Invalid command"),
            RetVal(RETVAL_DONE, "Complete")
        ]
        
        assert retvals[0].code == 0
        assert retvals[1].code == 1
        assert retvals[2].code == 2
        assert retvals[3].code == 65535
    
    @given(
        special_message=st.sampled_from([
            "",  # Empty string
            " " * 1000,  # Spaces
            "\n" * 100,  # Newlines
            "\t" * 100,  # Tabs
            "\r\n" * 50,  # Windows newlines
            "\x00" * 10,  # Null bytes
            "🎉" * 100,  # Emojis
            "你好世界" * 100,  # Unicode
            "<script>alert('xss')</script>",  # HTML/JS
            "'; DROP TABLE users; --",  # SQL injection
            "../../../etc/passwd",  # Path traversal
            "\\x00\\x01\\x02\\xff",  # Escape sequences
        ])
    )
    def test_retval_with_special_messages(self, special_message):
        """Test RetVal with special characters in messages."""
        retval = RetVal(0, special_message)
        assert retval.message == special_message
    
    def test_retval_default_values(self):
        """Test RetVal default values."""
        retval = RetVal()
        assert retval.code == 0
        assert retval.message == ""
        
        # Test with only code
        retval2 = RetVal(42)
        assert retval2.code == 42
        assert retval2.message == ""
    
    @patch('conductor.retval.send_message')
    def test_retval_send_method(self, mock_send_message):
        """Test RetVal.send method."""
        retval = RetVal(123, "test message")
        mock_socket = MagicMock()
        
        retval.send(mock_socket)
        
        # Verify send_message was called correctly
        mock_send_message.assert_called_once_with(
            mock_socket,
            "result",
            {
                "code": 123,
                "message": "test message"
            }
        )
    
    @given(
        large_message=st.text(min_size=1000, max_size=5000)
    )
    @patch('conductor.retval.send_message')
    def test_retval_send_with_large_messages(self, mock_send_message, large_message):
        """Test sending RetVal with very large messages."""
        retval = RetVal(0, large_message)
        mock_socket = MagicMock()
        
        retval.send(mock_socket)
        
        # Verify the large message was passed
        call_args = mock_send_message.call_args[0]
        assert call_args[2]["message"] == large_message
        assert len(call_args[2]["message"]) == len(large_message)
    
    def test_retval_mutability(self):
        """Test if RetVal values can be modified after creation."""
        retval = RetVal(10, "initial")
        
        # Modify values
        retval.code = 20
        retval.message = "modified"
        
        assert retval.code == 20
        assert retval.message == "modified"
    
    def test_retval_comparison(self):
        """Test if RetVal objects can be compared."""
        retval1 = RetVal(10, "test")
        retval2 = RetVal(10, "test")
        retval3 = RetVal(20, "test")
        
        # Test equality (likely not implemented)
        assert retval1 != retval2  # Different objects
        assert retval1 != retval3  # Different values
    
    @given(
        attr_name=st.text(min_size=1, max_size=50).filter(
            lambda x: x.isidentifier() and x not in ['code', 'message', 'send']
        )
    )
    def test_retval_dynamic_attributes(self, attr_name):
        """Test if RetVal allows dynamic attribute assignment."""
        retval = RetVal(0, "test")
        
        # Add new attribute
        setattr(retval, attr_name, "dynamic_value")
        assert hasattr(retval, attr_name)
        assert getattr(retval, attr_name) == "dynamic_value"
    
    def test_retval_string_representation(self):
        """Test if RetVal has useful string representations."""
        retval = RetVal(42, "error occurred")
        
        str_repr = str(retval)
        repr_repr = repr(retval)
        
        # Default object representation (no __str__ or __repr__ implemented)
        assert "RetVal object at" in str_repr or "42" in str_repr
        assert "RetVal object at" in repr_repr or "42" in repr_repr
    
    @patch('conductor.retval.send_message')
    def test_retval_send_with_non_serializable(self, mock_send_message):
        """Test sending RetVal with non-JSON-serializable values."""
        # Create RetVal with non-serializable values
        retval = RetVal(lambda x: x, object())
        mock_socket = MagicMock()
        
        # With our fix, this should convert to string representations
        retval.send(mock_socket)
        
        # Verify it was called with stringified values
        mock_send_message.assert_called_once()
        call_args = mock_send_message.call_args[0][2]
        assert isinstance(call_args["code"], str)
        assert isinstance(call_args["message"], str)
    
    def test_retval_with_circular_references(self):
        """Test RetVal with circular references."""
        retval = RetVal(0, "test")
        
        # Create circular reference
        circular_list = []
        circular_list.append(circular_list)
        
        retval.message = circular_list
        assert retval.message is circular_list
        
        # With our fix, sending should handle circular references
        mock_socket = MagicMock()
        with patch('conductor.retval.send_message') as mock_send:
            retval.send(mock_socket)
            # Should convert message to string representation
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0][2]
            assert call_args["code"] == 0
            assert isinstance(call_args["message"], str)