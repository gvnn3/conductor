"""Test to verify that placeholder methods are not used anywhere in the codebase."""
import pytest
import subprocess
import os


class TestUnusedMethods:
    """Verify that placeholder methods are truly unused before removal."""

    def test_step_ready_method_not_used(self):
        """Verify that Step.ready() is not used anywhere in production code."""
        # Search for .ready() calls on step objects
        result = subprocess.run(
            ["grep", "-r", r"\.ready(", "conductor", "--include=*.py"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        
        # Filter out test files and the method definition itself
        lines = [
            line for line in result.stdout.splitlines()
            if "test_" not in line 
            and "__pycache__" not in line
            and "def ready(self):" not in line
        ]
        
        assert len(lines) == 0, f"Step.ready() is used in production code: {lines}"

    def test_step_wait_ready_method_not_used(self):
        """Verify that Step.wait_ready() is not used anywhere in production code."""
        result = subprocess.run(
            ["grep", "-r", r"\.wait_ready(", "conductor", "--include=*.py"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        
        lines = [
            line for line in result.stdout.splitlines()
            if "test_" not in line 
            and "__pycache__" not in line
            and "def wait_ready(self):" not in line
        ]
        
        assert len(lines) == 0, f"Step.wait_ready() is used in production code: {lines}"

    def test_step_wait_method_not_used(self):
        """Verify that Step.wait() is not used anywhere in production code."""
        result = subprocess.run(
            ["grep", "-r", r"step\.wait(", "conductor", "--include=*.py"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        
        lines = [
            line for line in result.stdout.splitlines()
            if "test_" not in line 
            and "__pycache__" not in line
            and "def wait(self" not in line
        ]
        
        assert len(lines) == 0, f"Step.wait() is used in production code: {lines}"

    def test_phase_load_method_not_used(self):
        """Verify that Phase.load() is not used anywhere in production code."""
        result = subprocess.run(
            ["grep", "-r", r"\.load(", "conductor", "--include=*.py"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        
        lines = [
            line for line in result.stdout.splitlines()
            if "test_" not in line 
            and "__pycache__" not in line
            and "def load(self):" not in line
        ]
        
        assert len(lines) == 0, f"Phase.load() is used in production code: {lines}"

    def test_can_create_step_without_placeholder_methods(self):
        """Verify Step works without placeholder methods."""
        from conductor.step import Step
        
        # Create a step and verify it works without calling placeholder methods
        step = Step("echo test")
        result = step.run()
        
        assert result.code == 0
        assert "test" in result.message
        
        # Verify the methods exist but do nothing
        assert hasattr(step, 'ready')
        assert hasattr(step, 'wait_ready')
        assert hasattr(step, 'wait')
        
        # Calling them should do nothing (return None)
        assert step.ready() is None
        assert step.wait_ready() is None
        assert step.wait("until") is None

    def test_can_create_phase_without_placeholder_method(self):
        """Verify Phase works without placeholder method."""
        from conductor.phase import Phase
        
        # Create a phase and verify it works without calling load()
        phase = Phase("localhost", 6970)
        
        # Verify the method exists but does nothing
        assert hasattr(phase, 'load')
        assert phase.load() is None
        
        # Phase should still work normally
        from conductor.step import Step
        step = Step("echo test")
        phase.append(step)
        assert len(phase.steps) == 1