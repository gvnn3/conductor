"""Tests for the Test class."""

import pytest
from unittest.mock import MagicMock
import pickle

from conductor.test import Test
from conductor.phase import Phase


class TestTestClass:
    """Test the Test class functionality."""
    
    def test_initialization(self):
        """Test that Test initializes with empty phases list."""
        test = Test()
        assert test.phases == []
        assert isinstance(test.phases, list)
    
    def test_append_adds_phase(self):
        """Test that append adds a phase to the phases list."""
        test = Test()
        phase = MagicMock(spec=Phase)
        
        test.append(phase)
        
        assert len(test.phases) == 1
        assert test.phases[0] is phase
    
    def test_append_multiple_phases(self):
        """Test appending multiple phases maintains order."""
        test = Test()
        phase1 = MagicMock(spec=Phase)
        phase2 = MagicMock(spec=Phase)
        phase3 = MagicMock(spec=Phase)
        
        test.append(phase1)
        test.append(phase2)
        test.append(phase3)
        
        assert len(test.phases) == 3
        assert test.phases[0] is phase1
        assert test.phases[1] is phase2
        assert test.phases[2] is phase3
    
    def test_can_be_pickled(self):
        """Test that Test can be pickled for serialization."""
        test = Test()
        phase = MagicMock(spec=Phase)
        test.append(phase)
        
        # Note: MagicMock can't be pickled, so we test with empty Test
        empty_test = Test()
        pickled = pickle.dumps(empty_test)
        unpickled = pickle.loads(pickled)
        
        assert isinstance(unpickled, Test)
        assert unpickled.phases == []