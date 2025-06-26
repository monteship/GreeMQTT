#!/usr/bin/env python3
"""
Docker health check script for GreeMQTT application.

This script verifies that the GreeMQTT application is running properly by checking:
1. Application process is running and responsive
2. Required environment variables are configured
3. Basic connectivity checks (optional)

Returns exit code 0 for healthy, 1 for unhealthy.
"""

import os
import sys
import socket


def check_required_env_vars() -> bool:
    """Check if required environment variables are set."""
    required_vars = ["MQTT_BROKER"]

    for var in required_vars:
        if not os.getenv(var):
            print(f"ERROR: Required environment variable {var} is not set")
            return False

    return True


def check_mqtt_broker_connectivity() -> bool:
    """Check if MQTT broker is reachable."""
    broker = os.getenv("MQTT_BROKER")
    port = int(os.getenv("MQTT_PORT", "1883"))

    try:
        # Create a socket and attempt to connect
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)  # 5 second timeout
        result = sock.connect_ex((broker, port))
        sock.close()

        if result == 0:
            return True
        else:
            print(
                f"WARNING: Cannot connect to MQTT broker {broker}:{port} (connection refused)"
            )
            # For Docker health checks, we might want to be more lenient during startup
            # Return True if this is just a connection issue but the broker config looks valid
            return False

    except socket.gaierror as e:
        print(f"ERROR: Failed to resolve MQTT broker hostname {broker}: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Failed to check MQTT broker connectivity: {e}")
        return False


def check_application_health() -> bool:
    """
    Check if the application appears to be healthy.
    This could be expanded to check application-specific health indicators.
    """
    # For now, just check if we can import the main module
    try:
        import GreeMQTT  # noqa: F401

        return True
    except ImportError as e:
        print(f"ERROR: Cannot import GreeMQTT module: {e}")
        return False


def main() -> int:
    """Main health check function."""
    print("Running GreeMQTT health check...")

    # Check required environment variables
    if not check_required_env_vars():
        return 1

    # Check application health
    if not check_application_health():
        return 1

    # Check MQTT broker connectivity
    if not check_mqtt_broker_connectivity():
        return 1

    print("Health check passed - application is healthy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
