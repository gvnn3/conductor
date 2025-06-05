"""Test that the system works correctly after removing placeholder methods."""
import pytest
from conductor.step import Step
from conductor.phase import Phase
from conductor.retval import RetVal


class TestSystemWithoutPlaceholders:
    """Verify the system functions correctly without placeholder methods."""
    
    def test_step_functions_without_placeholders(self):
        """Test that Step works normally without ready/wait_ready/wait methods."""
        step = Step("echo hello")
        
        # Run the step - the core functionality
        result = step.run()
        assert result.code == 0
        assert "hello" in result.message
        
        # Spawn mode should work
        spawn_step = Step("sleep 0.1", spawn=True)
        spawn_result = spawn_step.run()
        assert spawn_result.code == 0
        assert spawn_result.message == "Spawned"
        
        # Timeout should work
        timeout_step = Step("echo timeout test", timeout=5)
        timeout_result = timeout_step.run()
        assert timeout_result.code == 0
        assert "timeout test" in timeout_result.message
    
    def test_phase_functions_without_load(self):
        """Test that Phase works normally without load method."""
        phase = Phase("localhost", 6970)
        
        # Core functionality: appending steps
        step1 = Step("echo step1")
        step2 = Step("echo step2")
        
        phase.append(step1)
        phase.append(step2)
        
        assert len(phase.steps) == 2
        assert phase.steps[0] == step1
        assert phase.steps[1] == step2
        
        # Results collection should work
        phase.results.append(RetVal(0, "test result"))
        assert len(phase.results) == 1
    
    def test_phase_run_and_return_results(self):
        """Test that Phase.run() and return_results() work without load()."""
        phase = Phase("localhost", 6970)
        
        # Add some steps
        phase.append(Step("echo test1"))
        phase.append(Step("echo test2"))
        
        # Run all steps
        phase.run()
        
        # Should have collected results
        assert len(phase.results) == 2
        assert phase.results[0].code == 0
        assert "test1" in phase.results[0].message
        assert phase.results[1].code == 0
        assert "test2" in phase.results[1].message
    
    def test_no_attribute_errors_after_removal(self):
        """Ensure removed methods no longer exist."""
        step = Step("echo test")
        phase = Phase("localhost", 6970)
        
        # These methods should not exist after removal
        assert not hasattr(step, 'ready'), "Step.ready() should be removed"
        assert not hasattr(step, 'wait_ready'), "Step.wait_ready() should be removed"
        assert not hasattr(step, 'wait'), "Step.wait() should be removed"
        assert not hasattr(phase, 'load'), "Phase.load() should be removed"
        
        # Attempting to call them should raise AttributeError
        with pytest.raises(AttributeError):
            step.ready()
        with pytest.raises(AttributeError):
            step.wait_ready()
        with pytest.raises(AttributeError):
            step.wait("until")
        with pytest.raises(AttributeError):
            phase.load()