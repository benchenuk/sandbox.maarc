from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal, Container
from textual.widgets import Header, Footer, Static, RichLog
from textual.reactive import reactive
from datetime import datetime
import asyncio

class PhaseBar(Static):
    """Placeholder for the Phase Bar widget."""
    def render(self) -> str:
        return "Progress: [DONE]──[ACTIVE]──[NEXT]──[PENDING]"

class InfoRow(Static):
    """Placeholder for the Info Row widget."""
    def render(self) -> str:
        return "AGENTS: Economist [Idle] Sociologist [Idle] | ITER: 0/0"

class ConsensusApp(App):
    """Consensus AI Researcher TUI."""
    
    CSS_PATH = "styles.tcss"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("l", "clear_logs", "Clear Logs"),
    ]

    elapsed_time = reactive(0)

    def on_mount(self) -> None:
        self.start_time = datetime.now()
        self.set_interval(1, self.update_timer)
        self.log_panel = self.query_one(RichLog)
        self.log_panel.write("Initializing Consensus AI Researcher...")
        self.set_interval(2, self.add_dummy_log)

    def update_timer(self) -> None:
        elapsed = datetime.now() - self.start_time
        self.elapsed_time = int(elapsed.total_seconds())
        # Update header or a dedicated timer widget
        self.sub_title = f"Elapsed: {self.elapsed_time}s"

    def add_dummy_log(self) -> None:
        self.log_panel.write(f"[{datetime.now().strftime('%H:%M:%S')}] Diagnostic: System heartbeat...")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield PhaseBar(id="phase-bar")
        yield InfoRow(id="info-row")
        yield RichLog(id="log-panel", highlight=True, markup=True)
        yield Static("Input Area Placeholder", id="chat-box")
        yield Footer()

    def action_clear_logs(self) -> None:
        self.log_panel.clear()

if __name__ == "__main__":
    app = ConsensusApp()
    app.run()
