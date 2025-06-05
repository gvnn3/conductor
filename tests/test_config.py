"""Tests for the Config class."""

import json
from conductor.config import Config


class TestConfigInitialization:
    """Test Config initialization and attributes."""

    def test_initialization_with_host_and_port(self):
        """Test Config initialization with host and port."""
        config = Config("192.168.1.100", 6970)
        assert config.host == "192.168.1.100"
        assert config.port == 6970

    def test_initialization_with_localhost(self):
        """Test Config initialization with localhost."""
        config = Config("localhost", 8080)
        assert config.host == "localhost"
        assert config.port == 8080

    def test_initialization_with_different_types(self):
        """Test Config handles different port types."""
        # String port should work
        config = Config("127.0.0.1", "6970")
        assert config.host == "127.0.0.1"
        assert config.port == "6970"

        # Integer port
        config2 = Config("127.0.0.1", 6970)
        assert config2.host == "127.0.0.1"
        assert config2.port == 6970


class TestConfigSerialization:
    """Test Config can be represented for JSON protocol."""

    def test_config_json_representation(self):
        """Test that Config can be represented for JSON serialization."""
        config = Config("test.example.com", 9999)

        # Create JSON representation
        config_data = {
            "host": config.host,
            "port": config.port
        }

        # Serialize to JSON
        json_str = json.dumps(config_data)
        loaded = json.loads(json_str)

        # Verify data is preserved
        assert loaded["host"] == "test.example.com"
        assert loaded["port"] == 9999
        
    def test_config_to_string(self):
        """Test Config string representation."""
        config = Config("myhost", 1234)
        
        # The protocol converts Config to string using str()
        config_str = str(config)
        
        # Verify it has a string representation
        assert isinstance(config_str, str)
        assert len(config_str) > 0
