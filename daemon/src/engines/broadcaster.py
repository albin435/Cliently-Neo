import logging
from typing import Callable, Awaitable, Dict, List

logger = logging.getLogger(__name__)

class Broadcaster:
    def __init__(self):
        self.listeners: List[Callable[[str, dict], Awaitable[None]]] = []

    def register(self, listener: Callable[[str, dict], Awaitable[None]]):
        self.listeners.append(listener)

    async def broadcast(self, session_id: str, data: dict):
        for listener in self.listeners:
            try:
                await listener(session_id, data)
            except Exception as e:
                logger.error(f"Broadcast error in listener {listener}: {e}")

global_broadcaster = Broadcaster()
