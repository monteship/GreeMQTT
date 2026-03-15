class DeviceRegistry:

    def __init__(self):
        self._devices = {}

    def register(self, topic: str, device: "Device"):
        self._devices[topic] = device

    def get(self, topic: str):
        return self._devices.get(topic)

    def unregister(self, topic: str):
        if topic in self._devices:
            del self._devices[topic]
