"""Tests for the Phase class."""

import pytest
from unittest.mock import MagicMock, patch, call
import socket

from conductor.phase import Phase
from conductor.step import Step
from conductor.retval import RetVal, RETVAL_DONE


class TestPhaseInitialization:
    """Test Phase initialization."""
    
    def test_initialization_with_host_and_port(self):
        """Test Phase initialization with result host and port."""
        phase = Phase("192.168.1.100", 6971)
        assert phase.resulthost == "192.168.1.100"
        assert phase.resultport == 6971
        assert phase.steps == []
        assert phase.results == []


class TestPhaseStepManagement:
    """Test Phase step management functionality."""
    
    def test_append_adds_step_to_list(self):
        """Test that append adds a step to the steps list."""
        phase = Phase("localhost", 6971)
        step = Step("echo hello")
        
        phase.append(step)
        
        assert len(phase.steps) == 1
        assert phase.steps[0] is step
    
    def test_append_multiple_steps(self):
        """Test appending multiple steps maintains order."""
        phase = Phase("localhost", 6971)
        step1 = Step("echo first")
        step2 = Step("echo second")
        step3 = Step("echo third")
        
        phase.append(step1)
        phase.append(step2)
        phase.append(step3)
        
        assert len(phase.steps) == 3
        assert phase.steps[0] is step1
        assert phase.steps[1] is step2
        assert phase.steps[2] is step3