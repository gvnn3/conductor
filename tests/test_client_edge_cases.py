"""Extended edge case tests for Client using hypothesis."""

import configparser
from hypothesis import given, strategies as st, assume
import pytest
from unittest.mock import MagicMock

from conductor.client import Client


class TestClientExtendedEdgeCases:
    """Extended edge case tests for Client class."""

    @given(
        host=st.text(min_size=1, max_size=255).filter(
            lambda x: x.strip() and "%" not in x
        ),
        cmd_port=st.integers(min_value=1, max_value=65535),
        results_port=st.integers(min_value=1, max_value=65535),
    )
    def test_client_with_various_hosts_and_ports(self, host, cmd_port, results_port):
        """Test client initialization with various host/port combinations."""
        # Ensure ports are different
        assume(cmd_port != results_port)

        # Use RawConfigParser to avoid interpolation issues
        config = configparser.RawConfigParser()
        config["Coordinator"] = {
            "conductor": "conductor.local",
            "player": host,
            "cmdport": str(cmd_port),
            "resultsport": str(results_port),
        }
        config["Startup"] = {}
        config["Run"] = {}
        config["Collect"] = {}
        config["Reset"] = {}

        client = Client(config)

        # Verify parsing
        assert client.config["Coordinator"]["player"] == host
        assert client.config["Coordinator"]["cmdport"] == str(cmd_port)
        assert client.config["Coordinator"]["resultsport"] == str(results_port)

    @given(
        phase_names=st.lists(
            st.sampled_from(["Startup", "Run", "Collect", "Reset"]),
            min_size=1,
            max_size=4,
            unique=True,
        )
    )
    def test_client_with_missing_phases(self, phase_names):
        """Test client behavior when some phases are missing from config."""
        config = configparser.RawConfigParser()
        config["Coordinator"] = {
            "conductor": "localhost",
            "player": "localhost",
            "cmdport": "6970",
            "resultsport": "6971",
        }

        # Add only the specified phases
        for phase in phase_names:
            config[phase] = {}

        # Should handle missing phases gracefully
        if set(phase_names) == {"Startup", "Run", "Collect", "Reset"}:
            # All phases present
            client = Client(config)
            assert hasattr(client, "startup_phase")
            assert hasattr(client, "run_phase")
            assert hasattr(client, "collect_phase")
            assert hasattr(client, "reset_phase")
        else:
            # Missing phases should raise error or create empty phases
            try:
                client = Client(config)
                # If it succeeds, phases should exist
                assert hasattr(client, "startup_phase")
            except (KeyError, AttributeError):
                # Expected if required phases are missing
                pass

    @given(
        step_commands=st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.text(min_size=1, max_size=200),
            min_size=0,
            max_size=10,
        )
    )
    def test_client_phase_with_many_steps(self, step_commands):
        """Test client with phases containing many steps."""
        config = configparser.RawConfigParser()
        config["Coordinator"] = {
            "conductor": "localhost",
            "player": "localhost",
            "cmdport": "6970",
            "resultsport": "6971",
        }

        # Add steps to Run phase
        config["Run"] = step_commands
        config["Startup"] = {}
        config["Collect"] = {}
        config["Reset"] = {}

        client = Client(config)

        # Verify steps were parsed
        assert len(client.run_phase.steps) == len(step_commands)

    @given(
        invalid_port=st.one_of(
            st.text(min_size=1, max_size=10).filter(lambda x: not x.isdigit()),
            st.integers(min_value=-1000, max_value=0),
            st.integers(min_value=65536, max_value=100000),
        )
    )
    def test_client_with_invalid_ports(self, invalid_port):
        """Test client initialization with invalid port values."""
        config = configparser.RawConfigParser()
        config["Coordinator"] = {
            "conductor": "localhost",
            "player": "localhost",
            "cmdport": str(invalid_port),
            "resultsport": "6971",
        }
        config["Startup"] = {}
        config["Run"] = {}
        config["Collect"] = {}
        config["Reset"] = {}

        # Should raise ValueError for invalid ports
        with pytest.raises(ValueError, match="Invalid command port"):
            Client(config)

    @given(
        special_commands=st.lists(
            st.sampled_from(
                [
                    "spawn:sleep 10",
                    "timeout5:python script.py",
                    "echo 'test'",
                    "ls -la /tmp",
                    "true && false",
                    "cat /dev/null",
                ]
            ),
            min_size=1,
            max_size=5,
        )
    )
    def test_client_special_command_parsing(self, special_commands):
        """Test client parsing of special command prefixes."""
        config = configparser.RawConfigParser()
        config["Coordinator"] = {
            "conductor": "localhost",
            "player": "localhost",
            "cmdport": "6970",
            "resultsport": "6971",
        }
        config["Startup"] = {}
        config["Collect"] = {}
        config["Reset"] = {}

        # Add commands to Run phase
        config["Run"] = {f"step{i}": cmd for i, cmd in enumerate(special_commands)}

        client = Client(config)

        # Verify special commands were parsed
        for i, cmd in enumerate(special_commands):
            step = client.run_phase.steps[i]
            if cmd.startswith("spawn:"):
                assert step.spawn is True
                assert step.timeout == 30  # default
            elif cmd.startswith("timeout"):
                assert step.spawn is False
                # Extract timeout value
                timeout_str = cmd.split(":")[0].replace("timeout", "")
                if timeout_str.isdigit():
                    assert step.timeout == int(timeout_str)
            else:
                assert step.spawn is False
                assert step.timeout == 30  # default


    @given(
        config_sections=st.dictionaries(
            st.text(min_size=1, max_size=50).filter(lambda x: "%" not in x),
            st.dictionaries(
                st.text(min_size=1, max_size=50).filter(lambda x: "%" not in x),
                st.text(min_size=0, max_size=200).filter(lambda x: "%" not in x),
                min_size=0,
                max_size=5,
            ),
            min_size=5,
            max_size=10,
        )
    )
    def test_client_with_extra_config_sections(self, config_sections):
        """Test client handles configs with extra sections gracefully."""
        config = configparser.RawConfigParser()

        # Ensure required sections exist
        if "Coordinator" not in config_sections:
            config_sections["Coordinator"] = {}

        # Ensure Coordinator has required fields
        if "conductor" not in config_sections["Coordinator"]:
            config_sections["Coordinator"]["conductor"] = "localhost"
        if "player" not in config_sections["Coordinator"]:
            config_sections["Coordinator"]["player"] = "localhost"
        if "cmdport" not in config_sections["Coordinator"]:
            config_sections["Coordinator"]["cmdport"] = "6970"
        if "resultsport" not in config_sections["Coordinator"]:
            config_sections["Coordinator"]["resultsport"] = "6971"

        # Add all provided sections, handling case-insensitive duplicates
        for section, options in config_sections.items():
            # Filter out case-insensitive duplicates in options
            filtered_options = {}
            seen_keys = set()
            for key, value in options.items():
                key_lower = key.lower()
                if key_lower not in seen_keys:
                    filtered_options[key] = value
                    seen_keys.add(key_lower)
            config[section] = filtered_options

        for phase in ["Startup", "Run", "Collect", "Reset"]:
            if phase not in config:
                config[phase] = {}

        # Client should ignore extra sections
        client = Client(config)
        assert client.config == config

    def create_minimal_client(self):
        """Create a minimal client for testing."""
        config = configparser.RawConfigParser()
        config["Coordinator"] = {
            "conductor": "localhost",
            "player": "localhost",
            "cmdport": "6970",
            "resultsport": "6971",
        }
        config["Startup"] = {}
        config["Run"] = {}
        config["Collect"] = {}
        config["Reset"] = {}
        return Client(config)
