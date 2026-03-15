import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional

from GreeMQTT.logger import log


class EventPriority(Enum):
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass(order=True)
class Event:
    priority: int = field(compare=True)
    timestamp: float = field(compare=True)
    event_type: str = field(compare=False, default="")
    device_id: Optional[str] = field(compare=False, default=None)
    data: Any = field(compare=False, default=None)
    callback: Optional[Callable] = field(compare=False, default=None)


class InternalEventQueue:
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.queue = asyncio.PriorityQueue()
        self.workers: list[asyncio.Task] = []
        self.stop_event = asyncio.Event()
        self.stats = {
            "processed": 0,
            "errors": 0,
            "processing_times": [],
        }
        self._lock = asyncio.Lock()

    async def start(self):
        log.info("Starting internal event queue", workers=self.max_workers)

        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(i))
            self.workers.append(worker)

        log.info("Event queue workers started", count=len(self.workers))

    async def stop(self):
        log.info("Stopping internal event queue")
        self.stop_event.set()

        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)

        log.info("Event queue stopped", stats=self.get_stats())

    async def enqueue(
            self,
            event_type: str,
            device_id: Optional[str] = None,
            data: Any = None,
            callback: Optional[Callable] = None,
            priority: EventPriority = EventPriority.NORMAL,
    ):
        event = Event(
            priority=priority.value,
            timestamp=time.time(),
            event_type=event_type,
            device_id=device_id,
            data=data,
            callback=callback,
        )

        await self.queue.put(event)

        log.debug(
            "Event enqueued",
            event_type=event_type,
            device_id=device_id,
            priority=priority.name,
            queue_size=self.queue.qsize(),
        )

    async def _worker(self, worker_id: int):
        log.info("Event queue worker started", worker_id=worker_id)

        while not self.stop_event.is_set():
            try:
                event = await asyncio.wait_for(self.queue.get(), timeout=1.0)

                start_time = time.time()

                try:
                    if event.callback:
                        if asyncio.iscoroutinefunction(event.callback):
                            await event.callback(event.data)
                        else:
                            event.callback(event.data)

                    processing_time = time.time() - start_time

                    async with self._lock:
                        self.stats["processed"] += 1
                        self.stats["processing_times"].append(processing_time)

                        if len(self.stats["processing_times"]) > 1000:
                            self.stats["processing_times"] = self.stats["processing_times"][-1000:]

                    log.debug(
                        "Event processed",
                        worker_id=worker_id,
                        event_type=event.event_type,
                        device_id=event.device_id,
                        processing_time_ms=round(processing_time * 1000, 2),
                    )

                except Exception as e:
                    async with self._lock:
                        self.stats["errors"] += 1

                    log.error(
                        "Error processing event",
                        worker_id=worker_id,
                        event_type=event.event_type,
                        device_id=event.device_id,
                        error=str(e),
                    )

                finally:
                    self.queue.task_done()

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                log.error("Worker error", worker_id=worker_id, error=str(e))

        log.info("Event queue worker stopped", worker_id=worker_id)

    def get_stats(self) -> Dict[str, Any]:
        stats = self.stats.copy()
        if stats["processing_times"]:
            avg_time = sum(stats["processing_times"]) / len(stats["processing_times"])
            stats["avg_processing_time_ms"] = round(avg_time * 1000, 2)
        else:
            stats["avg_processing_time_ms"] = 0.0

        stats["queue_size"] = self.queue.qsize()
        stats["active_workers"] = len([w for w in self.workers if not w.done()])

        del stats["processing_times"]

        return stats

    async def wait_empty(self):
        await self.queue.join()


_queue_instance: Optional[InternalEventQueue] = None


def get_event_queue(max_workers: int = 5) -> InternalEventQueue:
    global _queue_instance

    if _queue_instance is None:
        _queue_instance = InternalEventQueue(max_workers=max_workers)

    return _queue_instance
