import logging
import pyperclip
import re
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Footer, Input

from maarc.layout import HeaderWidget, WorkflowWidget, AgentTeamWidget, LogWidget, InputWidget
from maarc.bridge import ResearchBridge
from maarc.hub import EventHub

class TUIHandler(logging.Handler):
    """Bridge standard logging to the EventHub."""
    def __init__(self, hub: EventHub):
        super().__init__()
        self.hub = hub
    
    def emit(self, record):
        msg = self.format(record)
        # Add color based on level
        if record.levelno >= logging.ERROR:
            msg = f"[bold red]{msg}[/bold red]"
        elif record.levelno >= logging.WARNING:
            msg = f"[orange3]{msg}[/orange3]"
        self.hub.publish("log", message=msg)

class MaarcApp(App):
    """MAARC V2 - Multi-Agent Research & Review Consensus"""
    
    CSS_PATH = "maarc.tcss"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("c", "copy_log", "Copy Log")
    ]

    def __init__(self):
        super().__init__()
        # Initialize Hub and Bridge
        self.hub = EventHub()
        
        # Setup Global Logging Capture
        tui_handler = TUIHandler(self.hub)
        tui_handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
        
        for logger_name in ["consensus", "openai", "httpx"]:
            l = logging.getLogger(logger_name)
            l.setLevel(logging.INFO)
            l.addHandler(tui_handler)
            l.propagate = False # Prevent double-logging to terminal
        
        self.bridge = ResearchBridge(hub=self.hub)
        self.log_history = []
        
        # Subscribe to Hub events
        self.hub.subscribe("log", self.handle_log)
        self.hub.subscribe("input_request", self.handle_input_request)
        self.hub.subscribe("iteration_update", self.handle_iteration_update)
        self.hub.subscribe("phase_update", self.handle_phase_update)
        self.hub.subscribe("team_update", self.handle_team_update)
        self.hub.subscribe("agent_update", self.handle_agent_update)
        self.hub.subscribe("completion", self.handle_completion)
        self.hub.subscribe("consensus_update", self.handle_consensus_update)

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield HeaderWidget()
        with Container(classes="main-container"):
            yield WorkflowWidget()
            yield AgentTeamWidget()
            yield LogWidget(id="log-view")
            yield InputWidget()
        yield Footer()

    def on_mount(self) -> None:
        """Called when app starts."""
        self.workflow_widget = self.query_one(WorkflowWidget)
        self.team_widget = self.query_one(AgentTeamWidget)
        self.log_widget = self.query_one(LogWidget)
        self.input_field = self.query_one("#input-line", Input)
        
        self.write_to_log("[dim]UI initialized. EventHub active.[/dim]")
        self.write_to_log("[dim italic]Tip: Hold 'Option' and drag to select text, or press 'C' to copy the entire log.[/dim italic]")
        
        # Start the real backend bridge
        self.bridge.start_research(topic="Quantum AI")

    def write_to_log(self, message: str) -> None:
        """Centralized log writer to track history for copying."""
        self.log_history.append(message)
        self.log_widget.write(message)

    def handle_log(self, message: str) -> None:
        """Callback for log events."""
        self.call_from_thread(self.write_to_log, message)

    def handle_iteration_update(self, current: int, total: int) -> None:
        """Update iteration widget."""
        self.call_from_thread(self.workflow_widget.update_iteration, current, total)

    def handle_phase_update(self, name: str, progress: float) -> None:
        """Update phase widget."""
        self.call_from_thread(self.workflow_widget.update_phase, name, progress)

    def handle_team_update(self, agents: list[dict]) -> None:
        """Update lead team widget."""
        # Include ORCHESTRATOR by default as it's always there but not in team_manifest usually
        all_agents = [{"role": "ORCHESTRATOR", "domain": "System", "status": "Idle"}] + agents
        self.call_from_thread(self.team_widget.update_team, all_agents)

    def handle_agent_update(self, role: str, status: str) -> None:
        """Update specific agent status."""
        def update():
            try:
                # Find the agent card by ID (calculated from role)
                card_id = f"#agent-{role.lower().replace(' ', '-')}"
                card = self.team_widget.query_one(card_id)
                card.update_status(status)
            except:
                pass # Agent might not be in the list yet
        self.call_from_thread(update)

    def handle_completion(self, data: dict) -> None:
        """Handle final research completion."""
        def update():
            self.workflow_widget.update_phase("COMPLETED", 100)
            self.workflow_widget.update_consensus("REACHED")
            self.write_to_log(f"\n[bold green]RESEARCH COMPLETE![/bold green]")
            self.write_to_log(f"[bold green]Report saved to:[/bold green] [cyan]{data.get('report_path')}[/cyan]")
            self.write_to_log(f"[dim]Topic: {data.get('topic')}[/dim]")
        self.call_from_thread(update)

    def handle_consensus_update(self, status: str) -> None:
        """Update consensus label."""
        self.call_from_thread(self.workflow_widget.update_consensus, status)

    def handle_input_request(self, prompt: str) -> None:
        """Callback when backend needs user input."""
        def prepare_input():
            self.write_to_log(f"[bold yellow]Input Required:[/bold yellow] {prompt}")
            self.input_field.placeholder = prompt.strip()
            self.input_field.value = ""
            self.input_field.focus()
            
        self.call_from_thread(prepare_input)

    def action_copy_log(self) -> None:
        """Action to copy entire log to clipboard."""
        try:
            # Strip Rich markup before copying for a cleaner clipboard
            import re
            def strip_markup(text):
                return re.sub(r'\[.*?\]', '', text)
            
            full_log = "\n".join(strip_markup(m) for m in self.log_history)
            pyperclip.copy(full_log)
            self.log_widget.write("[bold green]Success:[/bold green] Entire log copied to clipboard!")
        except Exception as e:
            self.log_widget.write(f"[bold red]Copy failed:[/bold red] {str(e)}")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in the input field."""
        value = event.value.strip()
        if value:
            # Try to submit to hub (if backend is waiting)
            if self.hub.submit_input(value):
                self.write_to_log(f"[cyan]> {value}[/cyan]")
                self.input_field.value = ""
                self.input_field.placeholder = "> Enter commands here..."
            else:
                # If nothing is waiting, maybe treat as a command or just ignore
                self.write_to_log(f"[dim]No input requested. Dropped: {value}[/dim]")
                self.input_field.value = ""

if __name__ == "__main__":
    app = MaarcApp()
    app.run()
