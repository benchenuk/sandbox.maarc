from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, ProgressBar, Label, RichLog, Input

class HeaderWidget(Static):
    """App Header"""
    def compose(self) -> ComposeResult:
        yield Label("MAARC V2 - Multi-Agent Research & Review Consensus")

class WorkflowWidget(Static):
    """Workflow Status Panel"""
    def compose(self) -> ComposeResult:
        with Vertical():
            with Horizontal(classes="workflow-row"):
                yield Label("ITERATION: ", classes="label")
                yield Label("0 / 0", id="iteration-count")
                yield Label("  PHASE: ", classes="label")
                yield Label("INITIALIZING", id="phase-name")
                yield Label("  CONSENSUS: ", classes="label")
                yield Label("WAITING", id="consensus-score")
                
            yield ProgressBar(total=100, show_eta=False, classes="phase-bar", id="phase-progress")
    
    def update_iteration(self, current: int, total: int):
        self.query_one("#iteration-count", Label).update(f"[bold cyan]{current} / {total}[/bold cyan]")

    def update_phase(self, name: str, progress: float):
        self.query_one("#phase-name", Label).update(f"[bold yellow]{name.upper()}[/bold yellow]")
        self.query_one("#phase-progress", ProgressBar).update(progress=progress)

    def update_consensus(self, status: str):
        """Update the consensus status label."""
        color = "green" if "REACHED" in status.upper() else "orange3"
        self.query_one("#consensus-score", Label).update(f"[bold {color}]{status}[/bold {color}]")

class AgentCard(Static):
    """Individual Agent Status Badge"""
    def __init__(self, role: str, status: str = "Idle", classes: str = ""):
        # Create a safe ID from role
        safe_id = f"agent-{role.lower().replace(' ', '-')}"
        super().__init__(id=safe_id, classes=classes)
        self.role = role
        self.status = status

    def on_mount(self):
        self.update_content()

    def update_content(self):
        indicator = "*" if self.status.lower() == "working" else "-"
        self.update(f"{indicator} [b]{self.role}[/b]\n[dim]{self.status}[/dim]")

    def update_status(self, status: str):
        self.status = status
        self.update_content()
        if status.lower() == "working":
            self.add_class("working")
        else:
            self.remove_class("working")

class AgentTeamWidget(Static):
    """Agent Team List"""
    def compose(self) -> ComposeResult:
        yield Horizontal(id="agent-list")

    def update_team(self, agents: list[dict]):
        """Clear and rebuild the agent list."""
        container = self.query_one("#agent-list", Horizontal)
        container.query("*").remove()
        for agent in agents:
            container.mount(AgentCard(agent["role"], agent.get("status", "Idle")))

class LogWidget(RichLog):
    """Scrolling Log Window with text selection support."""
    def __init__(self, **kwargs):
        # highlight=True enables internal selection/interaction in some Textual versions
        super().__init__(markup=True, auto_scroll=True, highlight=True, **kwargs)
        self.can_focus = True

    def on_click(self) -> None:
        """Focus on click to support text selection."""
        self.focus()

class InputWidget(Static):
    """Bottom Input Bar"""
    def compose(self) -> ComposeResult:
        yield Input(placeholder="> Enter commands here...", id="input-line")
