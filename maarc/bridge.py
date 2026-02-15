import asyncio
import threading
from typing import Any, Optional

from engine.v2.graph import ResearchGraphV2
from engine.utils.config import load_config
from maarc.hub import EventHub

class ResearchBridge:
    """
    Adapts the CLI-based ResearchGraphV2 for use in the TUI.
    Running the graph in a separate thread and communicating via EventHub.
    """
    def __init__(self, hub: EventHub):
        self.hub = hub
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        
    def start_research(self, topic: str = "Quantum AI"):
        """Start the research graph in a background thread."""
        
        def run():
            # Create a new event loop for this thread if needed
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def run_async():
                try:
                    cfg = load_config("config.yaml")
                    
                    # Pass the hub to the graph
                    graph = ResearchGraphV2(config=cfg, hub=self.hub)
                    
                    self.hub.publish("log", message=f"[bold green]System:[/bold green] ResearchGraphV2 instantiated with EventHub.")
                    
                    # Run the full async graph
                    result = await graph.run(topic=topic)
                    
                    if result.get("status") == "completed":
                        self.hub.publish("completion", data=result)
                    else:
                        self.hub.publish("log", message=f"[bold red]Research Failed:[/bold red] {result.get('error')}")
                    
                except Exception as e:
                    import traceback
                    error_trace = traceback.format_exc()
                    self.hub.publish("log", message=f"[bold red]CRITICAL ERROR:[/bold red] {str(e)}")
                    self.hub.publish("log", message=f"[dim red]{error_trace}[/dim red]")

            loop.run_until_complete(run_async())

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()
