import asyncio
import time
from typing import Dict

from GreeMQTT.config import UPDATE_INTERVAL
from GreeMQTT.logger import log


class AdaptivePollingManager:
    def __init__(self, duration_seconds: int, fast_interval: float):
        self.duration_seconds = duration_seconds
        self.fast_interval = fast_interval
        self._device_states: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def trigger_adaptive_polling(self, device_id: str) -> None:
        async with self._lock:
            current_time = time.time()
            self._device_states[device_id] = current_time
            log.debug(
                "Adaptive polling triggered",
                device_id=device_id,
                duration_seconds=self.duration_seconds,
                fast_interval=self.fast_interval,
            )

    async def get_polling_interval(self, device_id: str) -> float:
        async with self._lock:
            if device_id not in self._device_states:
                return UPDATE_INTERVAL

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
                    normal_interval=UPDATE_INTERVAL,
                )
                return UPDATE_INTERVAL

    async def is_adaptive_polling_active(self, device_id: str) -> bool:
        interval = await self.get_polling_interval(device_id)
        return interval == self.fast_interval

    async def cleanup_expired_states(self) -> None:
        async with self._lock:
            current_time = time.time()
            expired_devices = []

            for device_id, trigger_time in self._device_states.items():
                if current_time - trigger_time >= self.duration_seconds:
                    expired_devices.append(device_id)

            for device_id in expired_devices:
                del self._device_states[device_id]
                log.debug("Cleaned up expired adaptive polling state", device_id=device_id)

    async def force_immediate_polling(self, device_id: str, duration: float = 5.0) -> None:
        async with self._lock:
            current_time = time.time()
            self._device_states[device_id] = current_time

            log.debug(
                "Forced immediate polling",
                device_id=device_id,
                duration=duration,
            )
