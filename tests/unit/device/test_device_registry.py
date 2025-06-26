"""Unit tests for GreeMQTT.device.device_registry module."""

import os
import pytest
from unittest.mock import patch, Mock

# Mock required env vars before importing
with patch.dict(os.environ, {"MQTT_BROKER": "test_broker"}):
    from GreeMQTT.device.device_registry import DeviceRegistry


class TestDeviceRegistry:
    """Test cases for DeviceRegistry class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.registry = DeviceRegistry()

    def test_device_registry_initialization(self):
        """Test DeviceRegistry can be initialized."""
        registry = DeviceRegistry()
        assert registry is not None

    def test_register_and_get_device(self):
        """Test registering and retrieving a device."""
        # Create mock device
        mock_device = Mock()
        mock_device.device_id = "test_device_123"
        mock_device.device_ip = "192.168.1.100"
        
        # Register device
        topic = "test/topic/device123"
        self.registry.register(topic, mock_device)
        
        # Retrieve device
        retrieved_device = self.registry.get(topic)
        assert retrieved_device == mock_device
        assert retrieved_device.device_id == "test_device_123"

    def test_get_nonexistent_device(self):
        """Test retrieving non-existent device returns None."""
        result = self.registry.get("nonexistent/topic")
        assert result is None

    def test_register_multiple_devices(self):
        """Test registering multiple devices with different topics."""
        # Create mock devices
        device1 = Mock()
        device1.device_id = "device_001"
        device2 = Mock()
        device2.device_id = "device_002"
        
        # Register devices
        topic1 = "test/device1/set"
        topic2 = "test/device2/set"
        self.registry.register(topic1, device1)
        self.registry.register(topic2, device2)
        
        # Retrieve devices
        retrieved1 = self.registry.get(topic1)
        retrieved2 = self.registry.get(topic2)
        
        assert retrieved1 == device1
        assert retrieved2 == device2
        assert retrieved1.device_id == "device_001"
        assert retrieved2.device_id == "device_002"

    def test_register_overwrites_existing_device(self):
        """Test registering a new device with same topic overwrites the old one."""
        # Create mock devices
        device1 = Mock()
        device1.device_id = "device_old"
        device2 = Mock()
        device2.device_id = "device_new"
        
        # Register first device
        topic = "test/same/topic"
        self.registry.register(topic, device1)
        
        # Verify first device is registered
        assert self.registry.get(topic) == device1
        
        # Register second device with same topic
        self.registry.register(topic, device2)
        
        # Verify second device overwrote the first
        retrieved = self.registry.get(topic)
        assert retrieved == device2
        assert retrieved.device_id == "device_new"

    def test_register_with_empty_topic(self):
        """Test registering device with empty topic."""
        mock_device = Mock()
        mock_device.device_id = "test_device"
        
        # Register with empty topic
        self.registry.register("", mock_device)
        
        # Should be able to retrieve with empty topic
        retrieved = self.registry.get("")
        assert retrieved == mock_device

    def test_register_with_none_device(self):
        """Test registering None as device."""
        topic = "test/none/device"
        self.registry.register(topic, None)
        
        # Should retrieve None
        retrieved = self.registry.get(topic)
        assert retrieved is None

    def test_get_with_none_topic(self):
        """Test getting device with None topic."""
        result = self.registry.get(None)
        assert result is None

    def test_registry_independence(self):
        """Test that different registry instances are independent."""
        registry1 = DeviceRegistry()
        registry2 = DeviceRegistry()
        
        # Create mock device
        mock_device = Mock()
        mock_device.device_id = "test_device"
        
        # Register in first registry
        topic = "test/topic"
        registry1.register(topic, mock_device)
        
        # Should not be available in second registry
        assert registry1.get(topic) == mock_device
        assert registry2.get(topic) is None