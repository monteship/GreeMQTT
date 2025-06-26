"""Unit tests for GreeMQTT.mqtt_client module."""

import os
import pytest
from unittest.mock import patch, Mock
import aiomqtt

# Mock required env vars before importing
with patch.dict(os.environ, {
    "MQTT_BROKER": "test_broker",
    "MQTT_PORT": "1883",
    "MQTT_USER": "test_user",
    "MQTT_PASSWORD": "test_pass",
    "MQTT_TOPIC": "test_topic",
    "MQTT_QOS": "1",
    "MQTT_KEEP_ALIVE": "60"
}):
    from GreeMQTT.mqtt_client import create_mqtt_client


class TestMqttClient:
    """Test cases for MQTT client creation."""

    @pytest.mark.asyncio
    async def test_create_mqtt_client_returns_client(self):
        """Test that create_mqtt_client returns an aiomqtt.Client instance."""
        client = await create_mqtt_client()
        assert isinstance(client, aiomqtt.Client)

    @pytest.mark.asyncio
    async def test_create_mqtt_client_with_mock_config(self):
        """Test client creation using mocked config values."""
        with patch('GreeMQTT.mqtt_client.MQTT_BROKER', 'mocked_broker'), \
             patch('GreeMQTT.mqtt_client.MQTT_PORT', 9999), \
             patch('GreeMQTT.mqtt_client.MQTT_KEEP_ALIVE', 300), \
             patch('GreeMQTT.mqtt_client.MQTT_TOPIC', 'mocked/topic'), \
             patch('GreeMQTT.mqtt_client.MQTT_QOS', 2), \
             patch('GreeMQTT.mqtt_client.MQTT_USER', 'mocked_user'), \
             patch('GreeMQTT.mqtt_client.MQTT_PASSWORD', 'mocked_pass'):
            
            client = await create_mqtt_client()
            assert isinstance(client, aiomqtt.Client)

    @pytest.mark.asyncio 
    async def test_create_mqtt_client_will_message_configuration(self):
        """Test that will message is properly configured."""
        with patch('GreeMQTT.mqtt_client.MQTT_TOPIC', 'test/topic'), \
             patch('GreeMQTT.mqtt_client.MQTT_QOS', 1):
            
            # Mock the aiomqtt.Client to verify will configuration
            with patch('GreeMQTT.mqtt_client.aiomqtt.Client') as mock_client:
                mock_instance = Mock()
                mock_client.return_value = mock_instance
                
                await create_mqtt_client()
                
                # Verify Client was called with will parameter
                call_args = mock_client.call_args
                assert 'will' in call_args.kwargs
                will_arg = call_args.kwargs['will']
                
                # Verify will has correct attributes (it should be a Will object)
                assert hasattr(will_arg, 'topic')
                assert hasattr(will_arg, 'payload')
                assert hasattr(will_arg, 'qos')
                assert hasattr(will_arg, 'retain')

    @pytest.mark.asyncio
    async def test_create_mqtt_client_with_authentication_config(self):
        """Test client creation with authentication configuration."""
        with patch('GreeMQTT.mqtt_client.MQTT_USER', 'auth_user'), \
             patch('GreeMQTT.mqtt_client.MQTT_PASSWORD', 'auth_pass'):
            
            # Mock aiomqtt.Client to verify it's called with correct parameters
            with patch('GreeMQTT.mqtt_client.aiomqtt.Client') as mock_client:
                mock_client.return_value = Mock()
                await create_mqtt_client()
                
                # Verify Client was called with authentication
                call_args = mock_client.call_args
                assert call_args.kwargs['username'] == 'auth_user'
                assert call_args.kwargs['password'] == 'auth_pass'

    @pytest.mark.asyncio
    async def test_create_mqtt_client_without_authentication_config(self):
        """Test client creation without authentication."""
        with patch('GreeMQTT.mqtt_client.MQTT_USER', None), \
             patch('GreeMQTT.mqtt_client.MQTT_PASSWORD', None):
            
            # Mock aiomqtt.Client to verify it's called correctly
            with patch('GreeMQTT.mqtt_client.aiomqtt.Client') as mock_client:
                mock_client.return_value = Mock()
                await create_mqtt_client()
                
                # Verify Client was called without authentication
                call_args = mock_client.call_args
                assert call_args.kwargs['username'] is None
                assert call_args.kwargs['password'] is None

    @pytest.mark.asyncio
    async def test_create_mqtt_client_broker_config(self):
        """Test client creation with broker configuration."""
        with patch('GreeMQTT.mqtt_client.MQTT_BROKER', 'custom.broker.com'), \
             patch('GreeMQTT.mqtt_client.MQTT_PORT', 8883), \
             patch('GreeMQTT.mqtt_client.MQTT_KEEP_ALIVE', 120):
            
            # Mock aiomqtt.Client to verify it's called correctly
            with patch('GreeMQTT.mqtt_client.aiomqtt.Client') as mock_client:
                mock_client.return_value = Mock()
                await create_mqtt_client()
                
                # Verify Client was called with correct broker settings
                call_args = mock_client.call_args
                assert call_args.kwargs['hostname'] == 'custom.broker.com'
                assert call_args.kwargs['port'] == 8883
                assert call_args.kwargs['keepalive'] == 120