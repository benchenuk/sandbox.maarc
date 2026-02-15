"""
ResearchBridge - Runs engine in a daemon thread.
Daemon threads don't block app exit - they're killed when main process exits.
"""

import asyncio
import threading
from typing import Any, Optional

from engine.v2.graph import ResearchGraphV2
from engine.utils.config import load_config
from maarc.hub import EventHub


class ResearchBridge:
    """
    Adapts the engine for use in the TUI.
    Uses a daemon thread that won't block app exit.
    """
    def __init__(self, hub: EventHub):
        self.hub = hub
        self._thread: Optional[threading.Thread] = None
        
    def start_research(self, topic: str):
        """
        Start the research in a daemon thread.
        Daemon threads are killed when the main process exits.
        """
        def run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def run_async():
                try:
                    cfg = load_config("config.yaml")
                    graph = ResearchGraphV2(config=cfg, hub=self.hub)
                    
                    result = await graph.run(topic=topic)
                    
                    if result.get("status") == "completed":
                        self.hub.publish("completion", data=result)
                        
                except Exception as e:
                    self.hub.publish("log", message=f"[red]Error: {str(e)}[/red]")

            try:
                loop.run_until_complete(run_async())
            finally:
                loop.close()

        # daemon=True means thread won't block process exit
        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
    
    def stop(self):
        """No-op - daemon thread will be killed on app exit."""
        pass
