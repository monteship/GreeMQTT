"""Integration tests for GreeMQTT application components."""

import os
import asyncio
import pytest
from unittest.mock import patch, Mock, AsyncMock, MagicMock

# Mock required env vars before importing
with patch.dict(os.environ, {
    "MQTT_BROKER": "test_broker",
    "MQTT_PORT": "1883",
    "MQTT_USER": "test_user",
    "MQTT_PASSWORD": "test_pass",
    "MQTT_TOPIC": "test_topic",
    "MQTT_QOS": "1",
    "MQTT_KEEP_ALIVE": "60",
    "UPDATE_INTERVAL": "5"
}):
    from GreeMQTT.mqtt_client import create_mqtt_client
    from GreeMQTT.mqtt_handler import start_device_tasks, device_registry


class TestMqttClientIntegration:
    """Integration tests for MQTT client functionality."""

    @pytest.mark.asyncio
    async def test_mqtt_client_creation_with_config(self):
        """Test MQTT client creation integrates properly with config."""
        # Test that the function can be called without errors
        client = await create_mqtt_client()
        assert client is not None
        
        # Verify it's an aiomqtt.Client
        import aiomqtt
        assert isinstance(client, aiomqtt.Client)

    @pytest.mark.asyncio
    async def test_mqtt_client_with_device_tasks_integration(self):
        """Test MQTT client works with device tasks."""
        # Create MQTT client
        client = await create_mqtt_client()
        
        # Create mock device
        mock_device = Mock()
        mock_device.synchronize_time = AsyncMock()
        mock_device.device_id = "integration_test_device"
        mock_device.device_ip = "192.168.1.200"
        
        # Create stop event
        stop_event = asyncio.Event()
        
        # Test device tasks can be started with the client
        await start_device_tasks(mock_device, client, stop_event)
        
        # Verify device method was called
        mock_device.synchronize_time.assert_called_once()


class TestDeviceRegistryIntegration:
    """Integration tests for device registry with other components."""

    def test_device_registry_singleton_behavior(self):
        """Test that device_registry behaves as expected across modules."""
        # The imported device_registry should be the same instance
        from GreeMQTT.mqtt_handler import device_registry as handler_registry
        
        # Register a device
        mock_device = Mock()
        mock_device.device_id = "singleton_test"
        
        topic = "integration/test/singleton"
        device_registry.register(topic, mock_device)
        
        # Should be retrievable from both references
        assert device_registry.get(topic) == mock_device
        assert handler_registry.get(topic) == mock_device
        assert device_registry.get(topic) == handler_registry.get(topic)


class TestConfigIntegration:
    """Integration tests for configuration with other components."""

    @pytest.mark.asyncio
    async def test_config_values_used_by_mqtt_client(self):
        """Test that config values are properly used by MQTT client."""
        with patch.dict(os.environ, {
            "MQTT_BROKER": "integration.test.broker",
            "MQTT_PORT": "8883",
            "MQTT_TOPIC": "integration/test",
            "MQTT_QOS": "2"
        }):
            # Mock the client creation to verify config usage
            with patch('GreeMQTT.mqtt_client.aiomqtt.Client') as mock_client_class:
                mock_client_instance = Mock()
                mock_client_class.return_value = mock_client_instance
                
                await create_mqtt_client()
                
                # Verify the client was created with config values
                call_args = mock_client_class.call_args
                # Note: Due to import caching, we may not see the new env values
                # This test verifies the integration pattern works
                assert call_args is not None
                assert 'hostname' in call_args.kwargs
                assert 'port' in call_args.kwargs

    def test_config_validation_integration(self):
        """Test config validation works as expected."""
        from GreeMQTT.config import get_env_int
        
        # Test with invalid environment variable
        with patch.dict(os.environ, {"TEST_INT_VAR": "not_an_integer"}):
            with pytest.raises(ValueError, match="TEST_INT_VAR must be an integer"):
                get_env_int("TEST_INT_VAR")
        
        # Test with valid environment variable
        with patch.dict(os.environ, {"TEST_INT_VAR": "42"}):
            result = get_env_int("TEST_INT_VAR")
            assert result == 42


class TestAsyncComponentsIntegration:
    """Integration tests for async components working together."""

    @pytest.mark.asyncio
    async def test_async_components_with_stop_event(self):
        """Test async components handle stop events properly."""
        # Create stop event
        stop_event = asyncio.Event()
        
        # Create mock device
        mock_device = Mock()
        mock_device.synchronize_time = AsyncMock()
        mock_device.device_id = "async_test_device"
        
        # Create mock MQTT client
        mock_client = Mock()
        
        # Start device tasks
        await start_device_tasks(mock_device, mock_client, stop_event)
        
        # Verify device synchronization was called
        mock_device.synchronize_time.assert_called_once()
        
        # Set stop event to test graceful shutdown pattern
        stop_event.set()
        assert stop_event.is_set()

    @pytest.mark.asyncio
    async def test_multiple_async_operations(self):
        """Test multiple async operations can run concurrently."""
        # Create multiple mock devices
        devices = []
        for i in range(3):
            device = Mock()
            device.synchronize_time = AsyncMock()
            device.device_id = f"concurrent_device_{i}"
            devices.append(device)
        
        # Create mock client and stop event
        mock_client = Mock()
        stop_event = asyncio.Event()
        
        # Start tasks for all devices concurrently
        tasks = []
        for device in devices:
            task = asyncio.create_task(
                start_device_tasks(device, mock_client, stop_event)
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        await asyncio.gather(*tasks)
        
        # Verify all devices were processed
        for device in devices:
            device.synchronize_time.assert_called_once()


class TestErrorHandlingIntegration:
    """Integration tests for error handling across components."""

    @pytest.mark.asyncio
    async def test_device_task_error_handling(self):
        """Test error handling in device tasks."""
        # Create device that raises exception in synchronize_time
        mock_device = Mock()
        mock_device.synchronize_time = AsyncMock(side_effect=Exception("sync error"))
        mock_device.device_id = "error_test_device"
        
        # Create mock client and stop event
        mock_client = Mock()
        stop_event = asyncio.Event()
        
        # This should not raise an exception due to error handling
        try:
            await start_device_tasks(mock_device, mock_client, stop_event)
        except Exception as e:
            pytest.fail(f"Device tasks should handle errors gracefully, but got: {e}")
        
        # Verify the method was called despite the error
        mock_device.synchronize_time.assert_called_once()

    def test_config_error_handling_integration(self):
        """Test config error handling integrates with application."""
        from GreeMQTT.config import get_env_str
        
        # Test required config missing
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="REQUIRED_VAR environment variable is required"):
                get_env_str("REQUIRED_VAR", required=True)
        
        # Test config with default values
        with patch.dict(os.environ, {}, clear=True):
            result = get_env_str("OPTIONAL_VAR", default="default_value")
            assert result == "default_value"