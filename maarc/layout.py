from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button
from textual.widgets import Static, Label, RichLog, TextArea


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
    """Agent list item with status indicator with animated blinking."""
    
    # Statuses that indicate "working" and should have blinking indicator
    WORKING_STATUSES = {"researching", "critiquing", "drafting", "evaluating", "planning", "synthesizing"}
    # Blink interval in seconds
    BLINK_INTERVAL = 0.5
    
    def __init__(self, role: str, status: str = "idle", **kwargs):
        safe_id = f"agent-{role.lower().replace(' ', '-')}"
        super().__init__(id=safe_id, classes="agent-card", **kwargs)
        self.role = role
        self.status = status
        self._blink_visible = True
        self._blink_timer = None
    
    def on_mount(self):
        self.update_content()
        self._start_blinking()
    
    def on_unmount(self):
        self._stop_blinking()
    
    def _start_blinking(self):
        """Start the blink timer if agent is in a working status."""
        if self.status.lower() in self.WORKING_STATUSES and self._blink_timer is None:
            self._blink_timer = self.set_interval(self.BLINK_INTERVAL, self._toggle_blink)
    
    def _stop_blinking(self):
        """Stop the blink timer."""
        if self._blink_timer is not None:
            self._blink_timer.stop()
            self._blink_timer = None
        self._blink_visible = True
    
    def _toggle_blink(self):
        """Toggle the blink state and refresh the display."""
        self._blink_visible = not self._blink_visible
        self.update_content()
    
    def update_content(self):
        from rich.markup import escape
        role_escaped = escape(self.role)
        status_lower = self.status.lower()
        
        # Status color mapping
        status_colors = {
            "researching": "cyan",
            "critiquing": "yellow", 
            "drafting": "blue",
            "evaluating": "magenta",
            "planning": "magenta",
            "synthesizing": "green",
        }
        status_color = status_colors.get(status_lower, "dim")
        
        if status_lower == "idle":
            self.update(f"○ {role_escaped}")
        else:
            # Show dot based on blink state
            if self._blink_visible:
                dot = f"[green]●[/green]"
            else:
                dot = "[dim]○[/dim]"
            self.update(f"{dot} [bold]{role_escaped}[/bold]  [{status_color}]{status_lower}[/{status_color}]")
    
    def update_status(self, status: str):
        old_status = self.status.lower()
        new_status = status.lower()
        self.status = status
        
        # Manage blink timer based on status change
        was_working = old_status in self.WORKING_STATUSES
        is_working = new_status in self.WORKING_STATUSES
        
        if is_working and not was_working:
            # Started working - start blinking
            self._blink_visible = True
            self._start_blinking()
        elif not is_working and was_working:
            # Stopped working - stop blinking
            self._stop_blinking()
        
        self.update_content()


class AgentTeamWidget(Static):
    """Vertical list of agents with legend."""
    def compose(self) -> ComposeResult:
        yield AgentLegend()
        yield Vertical(id="agent-list")
    
    def update_team(self, agents: list[dict]):
        """Synchronize agent list widgets with new data."""
        container = self.query_one("#agent-list", Vertical)
        
        # 1. Get current children mapped by their role-based ID
        current_cards = {card.id: card for card in container.query(AgentCard)}
        new_agent_ids = []
        
        # 2. Add or update agents
        for agent_data in agents:
            role = agent_data.get("role", "Expert")
            status = agent_data.get("status", "idle")
            safe_id = f"agent-{role.lower().replace(' ', '-')}"
            new_agent_ids.append(safe_id)
            
            if safe_id in current_cards:
                # Update existing card
                current_cards[safe_id].update_status(status)
            else:
                # Mount new card
                container.mount(AgentCard(role=role, status=status))
        
        # 3. Remove agents that are no longer in the team
        for card_id, card in current_cards.items():
            if card_id not in new_agent_ids:
                card.remove()
    
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
        super().__init__(markup=True, auto_scroll=True, highlight=True, wrap=True, **kwargs)
        self.can_focus = True
    
    def on_click(self) -> None:
        self.focus()


class InputWidget(Static):
    """Expandable multi-line input with toggle button."""
    
    EXPANDED_HEIGHT = 10
    
    def compose(self) -> ComposeResult:
        with Horizontal(classes="input-row"):
            yield Label("> ", classes="prompt")
            yield TextArea(id="input-area", show_line_numbers=False)
            yield Button("^", id="expand-btn", variant="default")
    
    def on_mount(self):
        """Set initial state - expanded by default for multi-line topics."""
        self.expanded = True
        self.textarea = self.query_one("#input-area", TextArea)
        self.button = self.query_one("#expand-btn", Button)
        # Set initial height via styles
        self.textarea.styles.height = self.EXPANDED_HEIGHT
        self.button.label = "v"
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Toggle expand/collapse when button is pressed."""
        if self.expanded:
            self.collapse()
        else:
            self.expand()
    
    def expand(self):
        """Expand to multi-line height."""
        if not self.expanded:
            self.textarea.styles.height = self.EXPANDED_HEIGHT
            self.button.label = "v"
            self.expanded = True
    
    def collapse(self):
        """Collapse back to single line."""
        if self.expanded:
            self.textarea.styles.height = 1
            self.button.label = "^"
            self.expanded = False
    
    def get_text(self) -> str:
        """Get current text content."""
        return self.textarea.text
    
    def clear(self):
        """Clear input and collapse."""
        self.textarea.text = ""
        self.collapse()
