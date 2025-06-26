"""Unit tests for GreeMQTT.logger module."""

import os
import logging
from unittest.mock import patch
import structlog

# Mock required env vars before importing
with patch.dict(os.environ, {"MQTT_BROKER": "test_broker"}):
    from GreeMQTT.logger import log


class TestLogger:
    """Test cases for logger configuration."""

    def test_logger_instance_is_structlog_bound_logger(self):
        """Test that log is an instance of structlog bound logger."""
        # Check if it's a structlog logger by checking its type or available methods
        assert hasattr(log, "_context")  # structlog bound loggers have _context
        assert hasattr(log, "bind")  # structlog bound loggers have bind method

    def test_logger_has_required_methods(self):
        """Test that logger has all required logging methods."""
        assert hasattr(log, "debug")
        assert hasattr(log, "info")
        assert hasattr(log, "warning")
        assert hasattr(log, "error")
        assert hasattr(log, "critical")
        assert hasattr(log, "exception")

    def test_logger_debug_method_callable(self):
        """Test that debug method is callable without errors."""
        try:
            log.debug("Test debug message")
        except Exception as e:
            pytest.fail(f"Logger debug method raised an exception: {e}")

    def test_logger_info_method_callable(self):
        """Test that info method is callable without errors."""
        try:
            log.info("Test info message")
        except Exception as e:
            pytest.fail(f"Logger info method raised an exception: {e}")

    def test_logger_warning_method_callable(self):
        """Test that warning method is callable without errors."""
        try:
            log.warning("Test warning message")
        except Exception as e:
            pytest.fail(f"Logger warning method raised an exception: {e}")

    def test_logger_error_method_callable(self):
        """Test that error method is callable without errors."""
        try:
            log.error("Test error message")
        except Exception as e:
            pytest.fail(f"Logger error method raised an exception: {e}")

    def test_logger_with_context(self):
        """Test that logger can handle context parameters."""
        try:
            log.info("Test message with context", device_id="test_device", status="active")
        except Exception as e:
            pytest.fail(f"Logger with context raised an exception: {e}")

    def test_structlog_configuration_processors(self):
        """Test that structlog is configured with expected processors."""
        config = structlog.get_config()
        processor_names = [proc.__name__ if hasattr(proc, '__name__') else str(proc) for proc in config['processors']]
        
        # Check for key processors (names might vary)
        assert any('merge_contextvars' in name for name in processor_names)
        assert any('add_log_level' in name for name in processor_names)
        assert any('TimeStamper' in name for name in processor_names)

    def test_structlog_configuration_wrapper_class(self):
        """Test that structlog is configured with filtering bound logger."""
        config = structlog.get_config()
        wrapper_class = config['wrapper_class']
        
        # Check that it's a filtering bound logger
        assert 'filtering' in str(wrapper_class).lower() or 'bound' in str(wrapper_class).lower()

    def test_structlog_configuration_logger_factory(self):
        """Test that structlog is configured with PrintLoggerFactory."""
        config = structlog.get_config()
        logger_factory = config['logger_factory']
        
        assert isinstance(logger_factory, structlog.PrintLoggerFactory)

    def test_logger_exception_method_callable(self):
        """Test that exception method is callable without errors."""
        try:
            log.exception("Test exception message")
        except Exception as e:
            pytest.fail(f"Logger exception method raised an exception: {e}")