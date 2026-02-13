"""
UI Components using Rich
Terminal interface components for displaying agent activities
"""

import time
from typing import Any, Dict, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

console = Console()

# ASCII Art Banner
BANNER = """
[bold cyan]
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ██████╗ ███████╗████████╗██████╗  ██████╗                  ║
║   ██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔═══██╗                 ║
║   ██████╔╝█████╗     ██║   ██████╔╝██║   ██║                 ║
║   ██╔══██╗██╔══╝     ██║   ██╔══██╗██║   ██║                 ║
║   ██║  ██║███████╗   ██║   ██║  ██║╚██████╔╝                 ║
║   ╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝                  ║
║                                                              ║
║         ██████╗ ███████╗ █████╗ ██████╗                      ║
║         ██╔══██╗██╔════╝██╔══██╗██╔══██╗                     ║
║         ██████╔╝█████╗  ███████║██║  ██║                     ║
║         ██╔══██╗██╔══╝  ██╔══██║██║  ██║                     ║
║         ██║  ██║███████╗██║  ██║██████╔╝                     ║
║         ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═════╝                      ║
║                                                              ║
║              CLI: Iterative Multi-Agent Research             ║
╚══════════════════════════════════════════════════════════════╝
[/bold cyan]
"""


def display_banner():
    """Display the application banner"""
    console.print(BANNER)


def display_help():
    """Display help information"""
    help_text = """
[bold]Usage:[/bold]
    consensus start --topic "Your research topic"
    consensus agents
    consensus configure --show
    consensus version

[bold]Examples:[/bold]
    consensus start -t "Design a REST API for a todo app"
    consensus start -t "Database selection for e-commerce" --hitl
    consensus start -t "Microservices patterns" -i 7 -v

[bold]For more information:[/bold]
    consensus start --help
"""
    console.print(Panel.fit(help_text, title="Help", border_style="cyan"))


def display_topic_input(topic: str, config: Dict[str, Any]):
    """Display the topic being researched"""
    iterations = config.get("research", {}).get("default_iterations", 5)
    hitl = config.get("human_in_the_loop", {}).get("enabled", True)

    table = Table(box=box.ROUNDED, show_header=False)
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Topic", topic)
    table.add_row("Iterations", str(iterations))
    table.add_row("Human-in-the-Loop", "Enabled" if hitl else "Disabled")

    console.print(Panel.fit(
        table,
        title="[bold]Research Session Configuration[/bold]",
        border_style="green"
    ))
    console.print()


def display_agent_spawn(agent_name: str, role: str):
    """Display when an agent is spawned"""
    console.print(f"[bold blue]→[/bold blue] Spawning [bold]{agent_name}[/bold] ({role})")


def display_agent_thinking(agent_name: str, action: str):
    """Display agent thinking/processing"""
    console.print(f"[dim][bold magenta]{agent_name}[/bold magenta]:[/dim] {action}")


def display_agent_output(agent_name: str, output: str, max_length: int = 200):
    """Display agent output"""
    truncated = output[:max_length] + "..." if len(output) > max_length else output
    console.print(f"\n[bold green]{agent_name}[/bold green]:\n{truncated}\n")


def display_checkpoint(
    checkpoint_name: str,
    options: list,
    current_state: Dict[str, Any]
):
    """Display a human-in-the-loop checkpoint"""
    console.print()
    console.print(Panel.fit(
        f"[bold yellow]⚠ HUMAN INTERVENTION REQUIRED[/bold yellow]\n\n"
        f"Checkpoint: {checkpoint_name}",
        border_style="yellow"
    ))

    # Display current state summary
    if current_state:
        console.print("\n[bold]Current State:[/bold]")
        for key, value in current_state.items():
            console.print(f"  {key}: {value}")

    # Display options
    console.print("\n[bold]Options:[/bold]")
    for i, option in enumerate(options, 1):
        console.print(f"  [{i}] {option}")

    console.print()


def display_consensus_reached(iterations: int):
    """Display when consensus is reached"""
    console.print()
    console.print(Panel.fit(
        f"[bold green]✓ CONSENSUS REACHED[/bold green]\n\n"
        f"Research completed after {iterations} iteration(s)",
        border_style="green"
    ))
    console.print()


def display_report_generated(report_path: str):
    """Display when report is generated"""
    console.print()
    console.print(Panel.fit(
        f"[bold]📄 Report Generated[/bold]\n\n"
        f"Location: [cyan]{report_path}[/cyan]",
        border_style="cyan"
    ))
    console.print()


def display_error(error_message: str):
    """Display an error message"""
    console.print(f"[bold red]✗ Error:[/bold red] {error_message}")


def display_warning(warning_message: str):
    """Display a warning message"""
    console.print(f"[bold yellow]⚠ Warning:[/bold yellow] {warning_message}")


def display_info(message: str):
    """Display an info message"""
    console.print(f"[bold blue]ℹ Info:[/bold blue] {message}")


def display_iteration_header(iteration: int, total: int):
    """Display iteration header"""
    console.print()
    console.print(f"[bold cyan]═══ Iteration {iteration}/{total} ═══[/bold cyan]")
    console.print()


def display_debate_summary(agents: Dict[str, str]):
    """Display a summary of the debate"""
    table = Table(title="Debate Summary", box=box.ROUNDED)
    table.add_column("Agent", style="cyan")
    table.add_column("Position", style="white")

    for agent, position in agents.items():
        table.add_row(agent, position)

    console.print(table)


def prompt_user(prompt: str, default: Optional[str] = None) -> str:
    """Prompt user for input"""
    if default:
        result = console.input(f"{prompt} [{default}]: ")
        return result if result.strip() else default
    return console.input(f"{prompt}: ")


def confirm(prompt: str) -> bool:
    """Ask user for confirmation"""
    response = console.input(f"{prompt} [y/N]: ")
    return response.lower() in ("y", "yes")
