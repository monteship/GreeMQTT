"""Pytest configuration and shared fixtures for GreeMQTT tests."""

import os
import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def mock_required_env_vars():
    """Automatically mock required environment variables for all tests."""
    with patch.dict(os.environ, {
        "MQTT_BROKER": "test_broker",
        "MQTT_PORT": "1883",
        "MQTT_USER": "test_user",  
        "MQTT_PASSWORD": "test_pass",
        "MQTT_TOPIC": "test_topic",
        "MQTT_QOS": "1",
        "MQTT_KEEP_ALIVE": "60",
        "UPDATE_INTERVAL": "5"
    }, clear=False):
        yield


@pytest.fixture
def sample_device_data():
    """Provide sample device data for testing."""
    return {
        "device_id": "test_device_123",
        "device_ip": "192.168.1.100",
        "name": "Test AC Unit",
        "key": "test_encryption_key",
        "is_GCM": False
    }


@pytest.fixture
def sample_mqtt_message():
    """Provide sample MQTT message data for testing."""
    return {
        "topic": "test_topic/device123/set",
        "payload": '{"Pow": 1, "SetTem": 24}',
        "qos": 1,
        "retain": False
    }