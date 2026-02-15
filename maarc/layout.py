from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, Label, RichLog, Input


class HeaderWidget(Static):
    """Large title header."""
    def compose(self) -> ComposeResult:
        yield Label("MAARC", classes="title-main")
        yield Label("Multi-Agent AI Research & Consensus", classes="title-sub")


class PhaseArrow(Static):
    """Individual phase arrow block."""
    def __init__(self, name: str, label: str, **kwargs):
        super().__init__(**kwargs)
        self.phase_name = name
        self.phase_label = label
        self.active = False
        self.completed = False
    
    def on_mount(self):
        self.update_content()
    
    def update_content(self):
        if self.active:
            self.update(f"[b]{self.phase_label}[/b]")
            self.add_class("active")
            self.remove_class("completed")
        elif self.completed:
            self.update(f"{self.phase_label}")
            self.add_class("completed")
            self.remove_class("active")
        else:
            self.update(f"[dim]{self.phase_label}[/dim]")
            self.remove_class("active")
            self.remove_class("completed")
    
    def set_active(self):
        self.active = True
        self.completed = False
        self.update_content()
    
    def set_completed(self):
        self.active = False
        self.completed = True
        self.update_content()


class WorkflowWidget(Static):
    """Workflow with phase arrows and status on same line."""
    
    PHASES = [
        ("planning", "PLAN"),
        ("researching", "RESEARCH"),
        ("drafting", "DRAFT"),
        ("critiquing", "CRITIQUE"),
        ("evaluating", "EVALUATE"),
        ("finalizing", "FINALIZE"),
    ]
    
    def compose(self) -> ComposeResult:
        with Horizontal(classes="workflow-row"):
            # Left side: phase arrows with directional arrows between
            with Horizontal(classes="arrows-container"):
                for i, (name, label) in enumerate(self.PHASES):
                    yield PhaseArrow(name, label, classes="phase-arrow")
                    # Add arrow separator between phases (not after last)
                    if i < len(self.PHASES) - 1:
                        yield Label(" ► ", classes="arrow-separator")
            
            # Right side: iter and time
            with Horizontal(classes="status-container"):
                yield Label("ITER ", classes="label")
                yield Label("0/0", id="iteration-count")
                yield Label(" │ ", classes="separator")
                yield Label("TIME ", classes="label")
                yield Label("00:00", id="elapsed-time")
    
    def update_iteration(self, current: int, total: int):
        self.query_one("#iteration-count", Label).update(f"[b]{current}/{total}[/b]")
    
    def update_elapsed(self, seconds: int):
        mins = seconds // 60
        secs = seconds % 60
        self.query_one("#elapsed-time", Label).update(f"[b]{mins:02d}:{secs:02d}[/b]")
    
    def update_phase(self, phase_name: str):
        """Light up phases up to and including current."""
        current_reached = False
        for arrow in self.query(PhaseArrow):
            if arrow.phase_name == phase_name.lower():
                arrow.set_active()
                current_reached = True
            elif not current_reached:
                arrow.set_completed()
            else:
                arrow.active = False
                arrow.completed = False
                arrow.update_content()


class AgentLegend(Static):
    """Minimal legend for agent status."""
    def compose(self) -> ComposeResult:
        with Horizontal(classes="legend-row"):
            yield Label("[green]●[/green] working  ", classes="legend-item")
            yield Label("[dim]○[/dim] idle", classes="legend-item")


class AgentCard(Static):
    """Agent list item with status indicator."""
    
    def __init__(self, role: str, status: str = "idle", **kwargs):
        safe_id = f"agent-{role.lower().replace(' ', '-')}"
        super().__init__(id=safe_id, classes="agent-card", **kwargs)
        self.role = role
        self.status = status
    
    def on_mount(self):
        self.update_content()
    
    def update_content(self):
        from rich.markup import escape
        role_escaped = escape(self.role)
        status_lower = self.status.lower()
        
        # Status color mapping
        status_colors = {
            "research": "cyan",
            "critique": "yellow", 
            "drafting": "blue",
            "evaluating": "magenta",
            "planning": "magenta",
            "working": "green",
        }
        status_color = status_colors.get(status_lower, "dim")
        
        if status_lower == "idle":
            self.update(f"○ {role_escaped}")
        else:
            # Dot is always green for working (per legend), name is white bold, status colored
            self.update(f"[green]●[/green] [bold]{role_escaped}[/bold]  [{status_color}]{status_lower}[/{status_color}]")
    
    def update_status(self, status: str):
        self.status = status
        self.update_content()


class AgentTeamWidget(Static):
    """Vertical list of agents with legend."""
    def compose(self) -> ComposeResult:
        yield AgentLegend()
        yield Vertical(id="agent-list")
    
    def update_team(self, agents: list[dict]):
        """Rebuild agent list."""
        container = self.query_one("#agent-list", Vertical)
        container.query("*").remove()
        for agent in agents:
            container.mount(AgentCard(
                agent["role"],
                agent.get("status", "idle")
            ))
    
    def update_agent_status(self, role: str, status: str):
        """Update specific agent status."""
        try:
            card_id = f"#agent-{role.lower().replace(' ', '-')}"
            card = self.query_one(card_id, AgentCard)
            card.update_status(status)
        except:
            pass


class LogWidget(RichLog):
    """Main log output."""
    def __init__(self, **kwargs):
        super().__init__(markup=True, auto_scroll=True, highlight=True, **kwargs)
        self.can_focus = True
    
    def on_click(self) -> None:
        self.focus()


class InputWidget(Static):
    """Input line with prompt."""
    def compose(self) -> ComposeResult:
        with Horizontal(classes="input-row"):
            yield Label("> ", classes="prompt")
            yield Input(placeholder="", id="input-line")
