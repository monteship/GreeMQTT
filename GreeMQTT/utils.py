class DeviceRegistry:
    """
    Manages device topic-to-instance mapping.

    This class provides methods to register, retrieve, and unregister devices based on their MQTT topics.
    It acts as a central registry for devices, allowing other components to interact with devices
    by their associated topics.

    Usage:
        - Use `register(topic, device)` to add a device to the registry.
        - Use `get(topic)` to retrieve a device by its topic.
        - Use `unregister(topic)` to remove a device from the registry.

    Concurrency Considerations:
        - This class is not thread-safe. If accessed from multiple coroutines, external synchronization
          (e.g., using asyncio locks) is required to ensure thread safety.

    Device Lifecycle:
        - Devices should be registered when they are initialized and ready to handle MQTT messages.
        - Devices should be unregistered when they are no longer active or when the application shuts down.
    """

    def __init__(self):
        self._devices = {}

    def register(self, topic: str, device: "Device"):  # noqa: F821
        self._devices[topic] = device

    def get(self, topic: str):
        return self._devices.get(topic)

    def unregister(self, topic: str):
        if topic in self._devices:
            del self._devices[topic]
