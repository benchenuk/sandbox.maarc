import logging
import pyperclip
import re
from datetime import datetime
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
        # Dim low-level API logs
        if record.name.startswith("httpx"):
            msg = f"[dim]{msg}[/dim]"
        elif record.name == "consensus.llm":
            msg = f"[dim]{msg}[/dim]"
        # Add color based on level
        elif record.levelno >= logging.ERROR:
            msg = f"[bold red]{msg}[/bold red]"
        elif record.levelno >= logging.WARNING:
            msg = f"[orange3]{msg}[/orange3]"
        self.hub.publish("log", message=msg)


class MaarcApp(App):
    """MAARC V2 - Multi-Agent Research & Review Consensus"""
    
    CSS_PATH = "maarc.tcss"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("c", "copy_log", "Copy")
    ]

    def __init__(self):
        super().__init__()
        self.hub = EventHub()
        
        # Setup Global Logging Capture
        tui_handler = TUIHandler(self.hub)
        tui_handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
        
        for logger_name in ["consensus", "openai", "httpx"]:
            l = logging.getLogger(logger_name)
            l.setLevel(logging.INFO)
            l.addHandler(tui_handler)
            l.propagate = False
        
        self.bridge = ResearchBridge(hub=self.hub)
        self.log_history = []
        self._topic_requested = False
        self._workflow_start = None
        
        # Subscribe to Hub events
        self.hub.subscribe("log", self.handle_log)
        self.hub.subscribe("input_request", self.handle_input_request)
        self.hub.subscribe("iteration_update", self.handle_iteration_update)
        self.hub.subscribe("phase_update", self.handle_phase_update)
        self.hub.subscribe("team_update", self.handle_team_update)
        self.hub.subscribe("agent_update", self.handle_agent_update)
        self.hub.subscribe("completion", self.handle_completion)

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
        """Called when app starts - prompt for topic."""
        self.workflow_widget = self.query_one(WorkflowWidget)
        self.team_widget = self.query_one(AgentTeamWidget)
        self.log_widget = self.query_one(LogWidget)
        self.input_field = self.query_one("#input-line", Input)
        
        # Initial system message and topic prompt
        self.write_to_log("[dim]System ready[/dim]")
        self.write_to_log("")
        self.write_to_log("Enter your research topic:")
        
        self._topic_requested = True
        self.input_field.placeholder = "Type your research question..."
        self.input_field.focus()

    def update_elapsed(self):
        """Update elapsed time display."""
        if self._workflow_start:
            elapsed = int((datetime.now() - self._workflow_start).total_seconds())
            self.workflow_widget.update_elapsed(elapsed)

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

    def handle_phase_update(self, name: str) -> None:
        """Update phase widget."""
        self.call_from_thread(self.workflow_widget.update_phase, name)

    def handle_team_update(self, agents: list[dict]) -> None:
        """Update agent team list - includes orchestrator and synthesizer by default."""
        # Add system agents to the list
        all_agents = [
            {"role": "ORCHESTRATOR", "domain": "System", "status": "idle"},
            {"role": "SYNTHESIZER", "domain": "System", "status": "idle"},
        ] + agents
        self.call_from_thread(self.team_widget.update_team, all_agents)

    def handle_agent_update(self, role: str, status: str) -> None:
        """Update specific agent status."""
        def update():
            self.team_widget.update_agent_status(role, status)
        self.call_from_thread(update)

    def handle_completion(self, data: dict) -> None:
        """Handle final research completion."""
        def update():
            self.workflow_widget.update_phase("completed")
            self.write_to_log("")
            self.write_to_log("[bold green]Complete[/bold green]")
            self.write_to_log(f"[dim]{data.get('report_path')}[/dim]")
        self.call_from_thread(update)

    def handle_input_request(self, prompt: str) -> None:
        """Callback when backend needs user input."""
        def prepare_input():
            self.write_to_log(f"")
            self.write_to_log(f"[bold]{prompt}[/bold]")
            self.input_field.placeholder = prompt.strip()
            self.input_field.value = ""
            self.input_field.focus()
            
        self.call_from_thread(prepare_input)

    def action_copy_log(self) -> None:
        """Action to copy entire log to clipboard."""
        try:
            def strip_markup(text):
                return re.sub(r'\[.*?\]', '', text)
            
            full_log = "\n".join(strip_markup(m) for m in self.log_history)
            pyperclip.copy(full_log)
            self.log_widget.write("[dim]Copied to clipboard[/dim]")
        except Exception as e:
            self.log_widget.write(f"[red]Copy failed: {str(e)}[/red]")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in the input field."""
        value = event.value.strip()
        
        if not value:
            # Empty input - show error and re-prompt
            self.write_to_log("[red]Topic cannot be empty[/red]")
            self.input_field.value = ""
            self.input_field.focus()
            return
        
        if self._topic_requested:
            # First input is the topic
            self._topic_requested = False
            topic = value
            self._workflow_start = datetime.now()
            
            # Start elapsed time updater now that workflow is starting
            self.set_interval(1, self.update_elapsed)
            
            self.write_to_log(f"")
            self.write_to_log(f"[dim]Topic: {topic}[/dim]")
            self.write_to_log("")
            self.input_field.value = ""
            self.input_field.placeholder = "..."
            
            # Start the research
            self.bridge.start_research(topic=topic)
        else:
            # Subsequent inputs go to hub if waiting
            if self.hub.submit_input(value):
                self.write_to_log(f"[cyan]> {value}[/cyan]")
                self.input_field.value = ""
                self.input_field.placeholder = "..."
            else:
                self.write_to_log(f"[dim]Not accepted: {value}[/dim]")
                self.input_field.value = ""


if __name__ == "__main__":
    app = MaarcApp()
    app.run()
