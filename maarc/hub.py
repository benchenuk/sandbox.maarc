import asyncio
from typing import Callable, Any, Dict, Optional

class EventHub:
    """
    Mediates communication between the async research engine and the Textual UI.
    Provides a way to publish logs/events and request blocking user input.
    """
    def __init__(self):
        self.event_callbacks: Dict[str, list[Callable]] = {}
        # Stores (loop, future) tuples
        self._input_futures: Dict[str, tuple[asyncio.AbstractEventLoop, asyncio.Future]] = {}

    def subscribe(self, event_type: str, callback: Callable):
        if event_type not in self.event_callbacks:
            self.event_callbacks[event_type] = []
        self.event_callbacks[event_type].append(callback)

    def publish(self, event_type: str, **data):
        """Publish an event to all subscribers."""
        if event_type in self.event_callbacks:
            for cb in self.event_callbacks[event_type]:
                cb(**data)

    async def request_input(self, prompt: str) -> str:
        """
        Request input from the UI and wait for the response.
        This is called by the research engine (background thread).
        """
        self.publish("input_request", prompt=prompt)
        
        # Capture the loop that is currently running the background task
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._input_futures["current"] = (loop, future)
        
        try:
            # Wait for result to be set via submit_input (from UI thread)
            result = await future
            return result
        finally:
            self._input_futures.pop("current", None)

    def submit_input(self, value: str):
        """Called by the UI (main thread) when user submits input."""
        item = self._input_futures.get("current")
        if item:
            loop, future = item
            if not future.done():
                # Correctly set result on the background loop from the UI thread
                loop.call_soon_threadsafe(future.set_result, value)
                return True
        return False
