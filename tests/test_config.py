"""Tests for the Config class."""

import pickle
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
    """Test Config can be pickled for network transmission."""

    def test_can_be_pickled_and_unpickled(self):
        """Test that Config can be pickled and unpickled."""
        original = Config("test.example.com", 9999)

        # Pickle it
        pickled = pickle.dumps(original)

        # Unpickle it
        unpickled = pickle.loads(pickled)

        # Verify attributes are preserved
        assert unpickled.host == original.host
        assert unpickled.port == original.port
        assert unpickled.host == "test.example.com"
        assert unpickled.port == 9999
