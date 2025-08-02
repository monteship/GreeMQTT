import asyncio
import time
from typing import Dict, Optional
from enum import Enum

from GreeMQTT.config import UPDATE_INTERVAL
from GreeMQTT.logger import log


class PollingMode(Enum):
    """Different polling modes for enhanced responsiveness."""
    NORMAL = "normal"
    FAST = "fast"
    ULTRA_FAST = "ultra_fast"
    IMMEDIATE = "immediate"


class AdaptivePollingManager:
    """
    Enhanced adaptive polling manager with multi-tier responsiveness.

    When a device receives an MQTT command, it transitions through different
    polling modes for optimal responsiveness while avoiding excessive load.
    """

    def __init__(self, duration_seconds: int, fast_interval: int):
        self.duration_seconds = duration_seconds
        self.fast_interval = fast_interval
        self.ultra_fast_interval = 0.3  # Ultra-fast polling for immediate response
        self.immediate_interval = 0.1   # Immediate polling for first few seconds

        # Device state tracking
        self._device_states: Dict[str, float] = {}
        self._device_modes: Dict[str, PollingMode] = {}
        self._command_counts: Dict[str, int] = {}  # Track command frequency
        self._lock = asyncio.Lock()

    async def trigger_adaptive_polling(self, device_id: str) -> None:
        """
        Trigger adaptive polling for a device with immediate responsiveness.

        Args:
            device_id: The unique identifier of the device
        """
        async with self._lock:
            current_time = time.time()
            self._device_states[device_id] = current_time

            # Track command frequency for smart mode selection
            self._command_counts[device_id] = self._command_counts.get(device_id, 0) + 1

            # Start with immediate mode for fastest response
            self._device_modes[device_id] = PollingMode.IMMEDIATE

            log.debug(
                "Adaptive polling triggered",
                device_id=device_id,
                mode=PollingMode.IMMEDIATE.value,
                command_count=self._command_counts[device_id],
            )

    async def get_polling_interval(self, device_id: str) -> float:
        """
        Get the current polling interval for a device with multi-tier responsiveness.

        Args:
            device_id: The unique identifier of the device

        Returns:
            The polling interval in seconds
        """
        async with self._lock:
            if device_id not in self._device_states:
                return UPDATE_INTERVAL

            trigger_time = self._device_states[device_id]
            current_time = time.time()
            time_since_trigger = current_time - trigger_time

            if time_since_trigger >= self.duration_seconds:
                # Adaptive period expired, return to normal
                self._cleanup_device_state(device_id)
                return UPDATE_INTERVAL

            # Multi-tier responsiveness based on time since trigger
            if time_since_trigger < 3:  # First 3 seconds - immediate response
                self._device_modes[device_id] = PollingMode.IMMEDIATE
                return self.immediate_interval
            elif time_since_trigger < 15:  # Next 12 seconds - ultra-fast
                self._device_modes[device_id] = PollingMode.ULTRA_FAST
                return self.ultra_fast_interval
            else:  # Remaining time - fast mode
                self._device_modes[device_id] = PollingMode.FAST
                # Gradually increase interval as time passes
                progress = (time_since_trigger - 15) / (self.duration_seconds - 15)
                gradual_interval = self.fast_interval + (UPDATE_INTERVAL - self.fast_interval) * progress
                return min(gradual_interval, UPDATE_INTERVAL)

    async def get_polling_mode(self, device_id: str) -> PollingMode:
        """
        Get the current polling mode for a device.

        Args:
            device_id: The unique identifier of the device

        Returns:
            The current polling mode
        """
        async with self._lock:
            return self._device_modes.get(device_id, PollingMode.NORMAL)

    async def is_adaptive_polling_active(self, device_id: str) -> bool:
        """
        Check if adaptive polling is currently active for a device.

        Args:
            device_id: The unique identifier of the device

        Returns:
            True if adaptive polling is active, False otherwise
        """
        async with self._lock:
            if device_id not in self._device_states:
                return False

            trigger_time = self._device_states[device_id]
            current_time = time.time()
            return (current_time - trigger_time) < self.duration_seconds

    async def get_time_since_trigger(self, device_id: str) -> Optional[float]:
        """
        Get time elapsed since adaptive polling was triggered.

        Args:
            device_id: The unique identifier of the device

        Returns:
            Time in seconds since trigger, or None if not active
        """
        async with self._lock:
            if device_id not in self._device_states:
                return None

            trigger_time = self._device_states[device_id]
            return time.time() - trigger_time

    async def get_command_frequency(self, device_id: str) -> int:
        """
        Get the command frequency for a device.

        Args:
            device_id: The unique identifier of the device

        Returns:
            Number of commands received
        """
        async with self._lock:
            return self._command_counts.get(device_id, 0)

    def _cleanup_device_state(self, device_id: str) -> None:
        """Clean up state for a single device."""
        if device_id in self._device_states:
            del self._device_states[device_id]
        if device_id in self._device_modes:
            del self._device_modes[device_id]

        # Reset command count periodically to prevent unlimited growth
        if device_id in self._command_counts and self._command_counts[device_id] > 100:
            self._command_counts[device_id] = 10  # Keep some history

        log.debug(
            "Cleaned up device state",
            device_id=device_id,
            returning_to_normal=True,
        )

    async def cleanup_expired_states(self) -> None:
        """
        Clean up expired adaptive polling states.
        This method can be called periodically to prevent memory leaks.
        """
        async with self._lock:
            current_time = time.time()
            expired_devices = []

            for device_id, trigger_time in self._device_states.items():
                if current_time - trigger_time >= self.duration_seconds:
                    expired_devices.append(device_id)

            for device_id in expired_devices:
                self._cleanup_device_state(device_id)

    async def force_immediate_polling(self, device_id: str, duration: float = 5.0) -> None:
        """
        Force immediate polling for a device for a specified duration.

        Args:
            device_id: The unique identifier of the device
            duration: Duration in seconds to maintain immediate polling
        """
        async with self._lock:
            current_time = time.time()
            # Set trigger time to ensure immediate polling for the specified duration
            self._device_states[device_id] = current_time
            self._device_modes[device_id] = PollingMode.IMMEDIATE

            log.debug(
                "Forced immediate polling",
                device_id=device_id,
                duration=duration,
            )

    async def get_statistics(self) -> Dict[str, any]:
        """
        Get statistics about adaptive polling usage.

        Returns:
            Dictionary with statistics
        """
        async with self._lock:
            active_devices = len(self._device_states)
            mode_counts = {}
            for mode in self._device_modes.values():
                mode_counts[mode.value] = mode_counts.get(mode.value, 0) + 1

            total_commands = sum(self._command_counts.values())

            return {
                "active_adaptive_devices": active_devices,
                "mode_distribution": mode_counts,
                "total_commands_processed": total_commands,
                "devices_with_commands": len(self._command_counts),
            }
