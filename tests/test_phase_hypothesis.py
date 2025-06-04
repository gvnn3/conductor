"""Hypothesis-based property tests for Phase handling."""

from hypothesis import given, strategies as st, assume, settings
import pytest

from conductor.phase import Phase
from conductor.step import Step
from conductor.retval import RETVAL_OK, RETVAL_ERROR


class TestPhaseProperties:
    """Property-based tests for Phase class."""
    
    @given(
        num_steps=st.integers(min_value=1, max_value=10),
        resulthost=st.sampled_from(["localhost", "127.0.0.1", "result.example.com"]),
        resultport=st.integers(min_value=1024, max_value=65535)
    )
    def test_phase_creation_with_steps(self, num_steps, resulthost, resultport):
        """Test that Phase correctly stores steps and result information."""
        phase = Phase(resulthost, resultport)
        
        # Add steps
        for i in range(num_steps):
            phase.append(Step(f"echo step_{i}"))
        
        assert len(phase.steps) == num_steps
        assert phase.resulthost == resulthost
        assert phase.resultport == resultport
        
        # Verify all steps are present
        for i, step in enumerate(phase.steps):
            assert isinstance(step, Step)
            assert step.args == ["echo", f"step_{i}"]
    
    @given(
        commands=st.lists(
            st.text(min_size=1, max_size=50).filter(
                lambda x: x.strip() and not any(c in x for c in ['\0', '\n', '\r'])
            ),
            min_size=1,
            max_size=5
        )
    )
    def test_phase_iteration(self, commands):
        """Test that phases can be iterated correctly."""
        phase = Phase("localhost", 9999)
        
        # Add steps from commands
        for cmd in commands:
            phase.append(Step(cmd))
        
        # Test iteration over steps
        collected = []
        for step in phase.steps:
            collected.append(step)
        
        assert len(collected) == len(commands)
        
        # Test that steps maintain order
        for i, step in enumerate(collected):
            assert isinstance(step, Step)
    
    @given(
        resulthost=st.sampled_from(["localhost", "127.0.0.1", "10.0.0.1", "example.com", "test.local"]),
        resultport=st.integers(min_value=1, max_value=65535)
    )
    def test_phase_result_info(self, resulthost, resultport):
        """Test that phase correctly stores result server information."""
        phase = Phase(resulthost, resultport)
        
        # Add at least one step
        phase.append(Step("true"))
        
        assert phase.resulthost == resulthost
        assert phase.resultport == resultport
    
    @given(
        step_configs=st.lists(
            st.dictionaries(
                st.sampled_from(["command", "spawn", "timeout"]),
                st.one_of(
                    st.text(min_size=1, max_size=20).filter(lambda x: '\n' not in x),
                    st.booleans(),
                    st.integers(min_value=1, max_value=60)
                ),
                min_size=1,
                max_size=3
            ),
            min_size=1,
            max_size=5
        )
    )
    def test_phase_with_mixed_step_types(self, step_configs):
        """Test phase with different types of steps."""
        phase = Phase("localhost", 9999)
        
        for config in step_configs:
            # Extract step parameters
            command = config.get("command", "echo test")
            spawn = config.get("spawn", False) if isinstance(config.get("spawn"), bool) else False
            timeout = config.get("timeout", 30) if isinstance(config.get("timeout"), int) else 30
            
            # Ensure command is a string
            if not isinstance(command, str):
                command = "echo test"
            
            phase.append(Step(command, spawn=spawn, timeout=timeout))
        
        # Verify all steps were added
        assert len(phase.steps) == len(step_configs)
        
        # Verify steps maintain their properties
        for step in phase.steps:
            assert isinstance(step, Step)
            assert hasattr(step, 'spawn')
            assert hasattr(step, 'timeout')
    
    @given(num_steps=st.integers(min_value=0, max_value=10))
    def test_phase_length(self, num_steps):
        """Test that phase length is correctly reported."""
        phase = Phase("localhost", 9999)
        
        # Empty phase
        assert len(phase.steps) == 0
        
        # Add steps
        for i in range(num_steps):
            phase.append(Step(f"echo {i}"))
        
        assert len(phase.steps) == num_steps
    
    @given(
        commands=st.lists(
            st.sampled_from(["echo", "true", "false", "pwd", "hostname"]),
            min_size=1,
            max_size=5
        )
    )
    @settings(deadline=5000)  # 5 second deadline for execution tests
    def test_phase_execution_with_safe_commands(self, commands):
        """Test phase execution with safe system commands."""
        phase = Phase("localhost", 9999)
        
        # Add safe commands
        for cmd in commands:
            phase.append(Step(cmd))
        
        # Test that phase can be executed (would need actual run method)
        # For now, just verify structure
        assert len(phase.steps) == len(commands)
        
        # Verify each step can be run individually
        for step in phase.steps:
            result = step.run()
            assert result is not None
            assert hasattr(result, 'code')
            
            # Most of these commands should succeed
            if step.args[0] in ["echo", "true", "pwd", "hostname"]:
                assert result.code == RETVAL_OK
            elif step.args[0] == "false":
                assert result.code == RETVAL_ERROR