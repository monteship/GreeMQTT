"""Unit tests for GreeMQTT.mqtt_handler module."""

import os
import asyncio
import json
import pytest
from unittest.mock import patch, Mock, AsyncMock, MagicMock
from aiomqtt import Client

# Mock required env vars before importing
with patch.dict(os.environ, {
    "MQTT_BROKER": "test_broker",
    "MQTT_QOS": "1",
    "MQTT_RETAIN": "false",
    "UPDATE_INTERVAL": "5"
}):
    from GreeMQTT.mqtt_handler import (
        with_retries, 
        start_device_tasks,
        device_registry
    )


class TestWithRetries:
    """Test cases for with_retries decorator."""

    @pytest.mark.asyncio
    async def test_with_retries_successful_execution(self):
        """Test decorator with successful function execution."""
        @with_retries(retries=3)
        async def test_func():
            return "success"
        
        result = await test_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_with_retries_with_eventual_success(self):
        """Test decorator retries until success."""
        call_count = 0
        
        @with_retries(retries=3, delay=0.01)
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("temporary error")
            return "success"
        
        result = await test_func()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_with_retries_exhausts_retries(self):
        """Test decorator raises exception after exhausting retries."""
        call_count = 0
        
        @with_retries(retries=2, delay=0.01)
        async def test_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("persistent error")
        
        with pytest.raises(ValueError, match="persistent error"):
            await test_func()
        
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_with_retries_backoff_behavior(self):
        """Test decorator applies exponential backoff."""
        call_times = []
        
        @with_retries(retries=3, delay=0.01, backoff=2.0)
        async def test_func():
            call_times.append(asyncio.get_event_loop().time())
            raise ValueError("test error")
        
        with pytest.raises(ValueError):
            await test_func()
        
        # Should have been called 3 times
        assert len(call_times) == 3
        
        # Verify exponential backoff timing (approximately)
        if len(call_times) >= 3:
            time_diff_1 = call_times[1] - call_times[0]
            time_diff_2 = call_times[2] - call_times[1]
            # Second delay should be approximately twice the first
            assert time_diff_2 > time_diff_1

    @pytest.mark.asyncio
    async def test_with_retries_custom_parameters(self):
        """Test decorator with custom retry parameters."""
        call_count = 0
        
        @with_retries(retries=5, delay=0.005, backoff=1.5)
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise ValueError("test error")
            return "success"
        
        result = await test_func()
        assert result == "success"
        assert call_count == 4

    @pytest.mark.asyncio
    async def test_with_retries_preserves_function_metadata(self):
        """Test that decorator preserves function metadata."""
        @with_retries(retries=3)
        async def test_func():
            """Test function docstring."""
            pass
        
        assert test_func.__name__ == "test_func"
        assert "Test function docstring." in test_func.__doc__


class TestStartDeviceTasks:
    """Test cases for start_device_tasks function."""

    @pytest.mark.asyncio
    async def test_start_device_tasks_creates_tasks(self):
        """Test that start_device_tasks creates expected async tasks."""
        # Mock device
        mock_device = Mock()
        mock_device.synchronize_time = AsyncMock()
        
        # Mock MQTT client
        mock_mqtt_client = Mock()
        
        # Mock stop event
        stop_event = asyncio.Event()
        
        # Mock asyncio.create_task to track task creation
        with patch('GreeMQTT.mqtt_handler.asyncio.create_task') as mock_create_task:
            with patch('GreeMQTT.mqtt_handler.get_params') as mock_get_params:
                with patch('GreeMQTT.mqtt_handler.subscribe') as mock_subscribe:
                    await start_device_tasks(mock_device, mock_mqtt_client, stop_event)
                    
                    # Verify that create_task was called 3 times
                    assert mock_create_task.call_count == 3
                    
                    # Verify device.synchronize_time was called
                    mock_device.synchronize_time.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_device_tasks_with_real_device_mock(self):
        """Test start_device_tasks with more realistic device mock."""
        # Create a mock device with required attributes
        mock_device = Mock()
        mock_device.synchronize_time = AsyncMock(return_value=None)
        mock_device.device_id = "test_device_123"
        mock_device.device_ip = "192.168.1.100"
        
        # Mock MQTT client
        mock_mqtt_client = Mock(spec=Client)
        
        # Create stop event
        stop_event = asyncio.Event()
        
        # Test the function
        await start_device_tasks(mock_device, mock_mqtt_client, stop_event)
        
        # Verify synchronize_time was called
        mock_device.synchronize_time.assert_called_once()


class TestDeviceRegistry:
    """Test cases for device registry functionality."""

    def test_device_registry_exists(self):
        """Test that device_registry is available."""
        assert device_registry is not None

    def test_device_registry_has_required_methods(self):
        """Test that device_registry has required methods."""
        assert hasattr(device_registry, 'register')
        assert hasattr(device_registry, 'get')

    def test_device_registry_register_and_get(self):
        """Test device registry register and get functionality."""
        # Create a mock device
        mock_device = Mock()
        mock_device.device_id = "test_device"
        
        # Register device
        test_topic = "test/topic/register"
        device_registry.register(test_topic, mock_device)
        
        # Retrieve device
        retrieved_device = device_registry.get(test_topic)
        assert retrieved_device == mock_device

    def test_device_registry_get_nonexistent(self):
        """Test getting non-existent device returns None."""
        result = device_registry.get("nonexistent/topic")
        assert result is None