"""
CLI Interface using Typer
Handles command-line argument parsing and orchestration
"""

import os
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from consensus.ui import (
    display_banner,
    display_topic_input,
    display_agent_spawn,
    display_agent_thinking,
    display_checkpoint,
    display_consensus_reached,
    display_report_generated,
)
from consensus.utils.config import load_config, validate_config
from consensus.workflow.graph import ResearchGraph
from consensus.utils.markdown import generate_report

app = typer.Typer(
    name="consensus",
    help="Consensus-CLI: Iterative Multi-Agent Research Engine",
    add_completion=False,
)

console = Console()


@app.command()
def start(
    topic: str = typer.Option(..., "--topic", "-t", help="Research topic or question"),
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to custom config file"
    ),
    iterations: Optional[int] = typer.Option(
        None, "--iterations", "-i", help="Number of research iterations"
    ),
    hitl: bool = typer.Option(
        False, "--hitl/--no-hitl", help="Enable Human-in-the-Loop checkpoints"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    Start a new research session on the given topic.

    The system will spawn multiple agents to research the topic,
    debate the findings, and generate a comprehensive report.
    """
    display_banner()

    # Load configuration
    config_path = config or "config.yaml"
    cfg = load_config(config_path)

    # Override config with CLI arguments
    if iterations:
        cfg["research"]["default_iterations"] = iterations
    if hitl:
        cfg["human_in_the_loop"]["enabled"] = True
    if verbose:
        cfg["ui"]["verbose"] = True

    # Validate configuration
    if not validate_config(cfg):
        console.print("[red]Error: Invalid configuration[/red]")
        raise typer.Exit(1)

    display_topic_input(topic, cfg)

    # Initialize the research graph
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Initializing research engine...", total=None)

        graph = ResearchGraph(config=cfg)
        progress.update(task, description="Research engine initialized!")

    # Run the research workflow
    console.print("\n[bold cyan]Starting research process...[/bold cyan]\n")

    result = graph.run(
        topic=topic,
        verbose=verbose,
    )

    # Display results
    if result.get("status") == "completed":
        display_consensus_reached(result.get("iterations", 0))

        # Generate and save report
        report_path = generate_report(
            topic=topic,
            result=result,
            output_dir=cfg["output"]["directory"],
        )

        display_report_generated(report_path)
    else:
        console.print("[red]Research failed: {}[/red]".format(result.get("error")))


@app.command()
def configure(
    show: bool = typer.Option(False, "--show", help="Show current configuration"),
):
    """
    Configure the application settings.
    """
    if show:
        cfg = load_config("config.yaml")
        import json

        console.print(Panel.fit(
            "[bold]Current Configuration[/bold]\n" +
            json.dumps(cfg, indent=2),
            border_style="cyan"
        ))


@app.command()
def agents():
    """
    List available agent types and their roles.
    """
    from consensus.agents import AGENT_ROLES

    console.print(Panel.fit(
        "[bold]Available Agent Roles[/bold]",
        border_style="cyan"
    ))

    for role, description in AGENT_ROLES.items():
        console.print(f"  [cyan]{role}[/cyan]: {description}")


@app.command()
def version():
    """Show version information."""
    from consensus import __version__

    console.print(f"[bold]Consensus-CLI[/bold] version {__version__}")


# Default command
@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context):
    """Consensus-CLI: Iterative Multi-Agent Research Engine"""
    if ctx.invoked_subcommand is None:
        display_banner()
        display_help()


if __name__ == "__main__":
    app()
