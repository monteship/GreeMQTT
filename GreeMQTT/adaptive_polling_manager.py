import threading
import time

from GreeMQTT.config import settings
from GreeMQTT.logger import log


class AdaptivePollingManager:
    def __init__(self, duration_seconds: int, fast_interval: float):
        if duration_seconds <= 0:
            raise ValueError("duration_seconds must be positive")
        if fast_interval <= 0:
            raise ValueError("fast_interval must be positive")
        self.duration_seconds = duration_seconds
        self.fast_interval = fast_interval
        self._device_states: dict[str, float] = {}
        self._immediate_until: dict[str, float] = {}
        self._lock = threading.Lock()

    def trigger_adaptive_polling(self, device_id: str) -> None:
        with self._lock:
            current_time = time.time()
            self._device_states[device_id] = current_time
            log.debug(
                "Adaptive polling triggered",
                device_id=device_id,
                duration_seconds=self.duration_seconds,
                fast_interval=self.fast_interval,
            )

    def get_polling_interval(self, device_id: str) -> float:
        with self._lock:
            # Check immediate (ultra-fast) polling first
            immediate_until = self._immediate_until.get(device_id, 0)
            if time.time() < immediate_until:
                return 0.1

            if device_id not in self._device_states:
                return settings.update_interval

            trigger_time = self._device_states[device_id]
            current_time = time.time()
            time_since_trigger = current_time - trigger_time

            if time_since_trigger < self.duration_seconds:
                return self.fast_interval
            else:
                del self._device_states[device_id]
                log.debug(
                    "Adaptive polling expired, returning to normal",
                    device_id=device_id,
                    normal_interval=settings.update_interval,
                )
                return settings.update_interval

    def is_adaptive_polling_active(self, device_id: str) -> bool:
        interval = self.get_polling_interval(device_id)
        return interval == self.fast_interval

    def cleanup_expired_states(self) -> None:
        with self._lock:
            current_time = time.time()
            expired_devices = []

            for device_id, trigger_time in self._device_states.items():
                if current_time - trigger_time >= self.duration_seconds:
                    expired_devices.append(device_id)

            for device_id in expired_devices:
                del self._device_states[device_id]
                log.debug("Cleaned up expired adaptive polling state", device_id=device_id)

    def force_immediate_polling(self, device_id: str, duration: float = 5.0) -> None:
        with self._lock:
            self._immediate_until[device_id] = time.time() + duration
            log.debug(
                "Forced immediate polling",
                device_id=device_id,
                duration=duration,
            )
