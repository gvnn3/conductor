"""Tests for the reporter module."""

import json
import tempfile
import os

from conductor.reporter import JSONReporter, TextReporter, create_reporter


class TestJSONReporter:
    """Test JSON reporter functionality."""

    def test_json_reporter_basic(self):
        """Test basic JSON reporter functionality."""
        reporter = JSONReporter()

        # Start trials
        reporter.start_trials(2, 3)

        # Trial 1
        reporter.start_trial(1)

        # Startup phase
        reporter.start_phase("startup")
        reporter.start_worker("worker_0")
        reporter.add_result(0, "Startup command 1 OK")
        reporter.add_result(0, "Startup command 2 OK")
        reporter.add_result(0, "done")
        reporter.end_worker()
        reporter.end_phase()

        # Run phase
        reporter.start_phase("run")
        reporter.start_worker("worker_0")
        reporter.add_result(0, "Run command 1 OK")
        reporter.add_result(1, "Run command 2 FAILED")
        reporter.add_result(0, "done")
        reporter.end_worker()
        reporter.end_phase()

        reporter.end_trial()

        # Finalize
        reporter.finalize()

        # Verify structure
        assert reporter.results["metadata"]["total_trials"] == 2
        assert reporter.results["metadata"]["total_workers"] == 3
        assert len(reporter.results["trials"]) == 1

        trial = reporter.results["trials"][0]
        assert trial["trial_number"] == 1
        assert "startup" in trial["phases"]
        assert "run" in trial["phases"]

        # Check startup phase
        startup = trial["phases"]["startup"]
        assert "worker_0" in startup["workers"]
        assert len(startup["workers"]["worker_0"]["results"]) == 3

        # Check run phase
        run = trial["phases"]["run"]
        assert "worker_0" in run["workers"]
        assert len(run["workers"]["worker_0"]["results"]) == 3
        assert run["workers"]["worker_0"]["results"][1]["code"] == 1

    def test_json_reporter_file_output(self):
        """Test JSON reporter writing to file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            output_file = f.name

        try:
            reporter = JSONReporter(output_file)

            reporter.start_trials(1, 1)
            reporter.start_trial(1)
            reporter.start_phase("test")
            reporter.start_worker("test_worker")
            reporter.add_result(0, "Test OK")
            reporter.end_worker()
            reporter.end_phase()
            reporter.end_trial()
            reporter.finalize()

            # Read and verify the file
            with open(output_file, "r") as f:
                data = json.load(f)

            assert data["metadata"]["total_trials"] == 1
            assert data["metadata"]["total_workers"] == 1
            assert len(data["trials"]) == 1

        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)


class TestTextReporter:
    """Test text reporter functionality."""

    def test_text_reporter_basic(self, capsys):
        """Test basic text reporter functionality."""
        reporter = TextReporter()

        reporter.start_trials(1, 1)
        reporter.start_trial(1)
        reporter.start_phase("test")
        reporter.start_worker("test_worker")

        # Add results - should print immediately
        reporter.add_result(0, "Test command OK")
        reporter.add_result(1, "Test command FAILED")
        reporter.add_result(0, "done")

        reporter.end_worker()
        reporter.end_phase()
        reporter.end_trial()
        reporter.finalize()

        # Check printed output
        captured = capsys.readouterr()
        assert "0 Test command OK" in captured.out
        assert "1 Test command FAILED" in captured.out
        assert "done" in captured.out

    def test_text_reporter_file_output(self):
        """Test text reporter writing summary to file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            output_file = f.name

        try:
            reporter = TextReporter(output_file)

            reporter.start_trials(1, 2)
            reporter.start_trial(1)
            reporter.start_phase("startup")
            reporter.start_worker("worker_0")
            reporter.add_result(0, "Startup OK")
            reporter.end_worker()
            reporter.end_phase()
            reporter.end_trial()
            reporter.finalize()

            # Read and verify the file
            with open(output_file, "r") as f:
                content = f.read()

            assert "Conductor Test Results" in content
            assert "Total Trials: 1" in content
            assert "Total Workers: 2" in content
            assert "Phase: startup" in content
            assert "Worker: worker_0" in content

        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)


class TestReporterFactory:
    """Test reporter factory function."""

    def test_create_json_reporter(self):
        """Test creating JSON reporter."""
        reporter = create_reporter("json")
        assert isinstance(reporter, JSONReporter)
        assert reporter.output_file is None

        reporter = create_reporter("JSON", "output.json")
        assert isinstance(reporter, JSONReporter)
        assert reporter.output_file == "output.json"

    def test_create_text_reporter(self):
        """Test creating text reporter."""
        reporter = create_reporter("text")
        assert isinstance(reporter, TextReporter)
        assert reporter.output_file is None

        reporter = create_reporter("TEXT", "output.txt")
        assert isinstance(reporter, TextReporter)
        assert reporter.output_file == "output.txt"
