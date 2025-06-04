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


class TestPhaseExecution:
    """Test Phase execution functionality."""
    
    def test_run_executes_all_steps_in_order(self):
        """Test that run executes all steps and collects results."""
        phase = Phase("localhost", 6971)
        
        # Create mock steps
        step1 = MagicMock()
        step1.run.return_value = RetVal(0, "Step 1 done")
        
        step2 = MagicMock()
        step2.run.return_value = RetVal(0, "Step 2 done")
        
        step3 = MagicMock()
        step3.run.return_value = RetVal(1, "Step 3 failed")
        
        phase.append(step1)
        phase.append(step2)
        phase.append(step3)
        
        # Run the phase
        phase.run()
        
        # Verify all steps were executed
        step1.run.assert_called_once()
        step2.run.assert_called_once()
        step3.run.assert_called_once()
        
        # Verify results were collected
        assert len(phase.results) == 3
        assert phase.results[0].code == 0
        assert phase.results[0].message == "Step 1 done"
        assert phase.results[1].code == 0
        assert phase.results[1].message == "Step 2 done"
        assert phase.results[2].code == 1
        assert phase.results[2].message == "Step 3 failed"
    
    def test_run_with_no_steps(self):
        """Test that run handles empty step list gracefully."""
        phase = Phase("localhost", 6971)
        
        # Run with no steps
        phase.run()
        
        # Should complete without error and have no results
        assert len(phase.results) == 0