"""
V2 CLI Interface
Entry point for the V2 research workflow
"""

import typer
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from consensus.v2.graph import ResearchGraphV2
from consensus.utils.config import load_config, validate_config

app = typer.Typer(
    name="consensus-v2",
    help="Consensus-CLI V2: Dynamic Multi-Agent Research Engine",
    add_completion=False,
)
console = Console()


def display_v2_banner():
    """Display V2 banner"""
    banner = """
[bold cyan]
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ██████╗ ███████╗██████╗  ██████╗ ██╗   ██╗███╗   ██╗       ║
║   ██╔══██╗██╔════╝██╔══██╗██╔═══██╗██║   ██║████╗  ██║       ║
║   ██████╔╝█████╗  ██║  ██║██║   ██║██║   ██║██╔██╗ ██║       ║
║   ██╔══██╗██╔══╝  ██║  ██║██║   ██║██║   ██║██║╚██╗██║       ║
║   ██║  ██║███████╗██████╔╝╚██████╔╝╚██████╔╝██║ ╚████║       ║
║   ╚═╝  ╚═╝╚══════╝╚═════╝  ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝       ║
║                                                              ║
║              V2: Dynamic Agent System                        ║
║              Iteration 2: Dynamic Strategy                   ║
╚══════════════════════════════════════════════════════════════╝
[/bold cyan]
"""
    console.print(banner)


def display_config_info(config: dict):
    """Display configuration summary"""
    table = Table(box=box.ROUNDED, show_header=False)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")
    
    research = config.get("research", {})
    table.add_row("Default Iterations", str(research.get("default_iterations", 5)))
    table.add_row("Consensus Threshold", str(research.get("consensus_threshold", 0.85)))
    
    hitl = config.get("human_in_the_loop", {})
    table.add_row("HITL Enabled", "Yes" if hitl.get("enabled", True) else "No")
    
    console.print(Panel.fit(
        table,
        title="[bold]Configuration[/bold]",
        border_style="green"
    ))


@app.command()
def start(
    topic: str = typer.Option(..., "--topic", "-t", help="Research topic or question"),
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to custom config file"
    ),
    iterations: Optional[int] = typer.Option(
        None, "--iterations", "-i", help="Number of research iterations"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    Start a new V2 research session on the given topic.
    
    This is the V2 implementation with:
    - Dynamic team generation via LLM
    - Report export to file
    """
    display_v2_banner()
    
    # Load configuration
    config_path = config or "config.yaml"
    cfg = load_config(config_path)
    
    # Override config with CLI arguments
    if iterations:
        cfg["research"]["default_iterations"] = iterations
    if verbose:
        cfg["ui"]["verbose"] = True
    
    # Validate configuration
    if not validate_config(cfg):
        console.print("[red]Error: Invalid configuration[/red]")
        raise typer.Exit(1)
    
    display_config_info(cfg)
    
    console.print(f"\n[bold]Topic:[/bold] {topic}")
    console.print("\n[dim]Initializing V2 research engine...[/dim]\n")
    
    # Initialize and run V2 graph
    graph = ResearchGraphV2(config=cfg)
    
    result = graph.run(
        topic=topic,
        verbose=verbose,
    )
    
    # Display results
    if result.get("status") == "completed":
        console.print(f"\n[bold green]{'='*60}[/bold green]")
        console.print("[bold green]Research Complete![/bold green]")
        console.print(f"[bold green]{'='*60}[/bold green]\n")
        
        # Show team
        console.print("[bold]Team Members:[/bold]")
        for agent in result.get("team_manifest", []):
            console.print(f"  • {agent['role']} ({agent['domain']})")
        
        # Show agent outputs summary
        console.print("\n[bold]Agent Outputs:[/bold]")
        for role, output in result.get("agent_outputs", {}).items():
            preview = output[:100].replace('\n', ' ') + "..." if len(output) > 100 else output
            console.print(f"\n[cyan]{role}:[/cyan]")
            console.print(f"  {preview}")
        
        console.print(f"\n[dim]Consensus Status: {result.get('consensus_status')}[/dim]")
        
        # Show report path
        report_path = result.get("report_path")
        if report_path:
            console.print(f"\n[bold green]Report saved:[/bold green] [cyan]{report_path}[/cyan]")
        
    else:
        console.print(f"\n[red]Research failed: {result.get('error')}[/red]")
        raise typer.Exit(1)


@app.command()
def info():
    """Show information about V2 implementation."""
    display_v2_banner()
    
    info_text = """
[bold]V2 Implementation: Iteration 2 - Dynamic Strategy[/bold]

This version introduces:

1. [cyan]Dynamic Team Generation[/cyan]
   - Orchestrator analyzes topic via LLM to propose relevant experts
   - Domain-appropriate roles generated (Economist, Technologist, etc.)
   - 3-5 agents with specialized system prompts

2. [cyan]Dynamic State Schema[/cyan]
   - agent_outputs: dict[str, str] - flexible storage for any agent's output
   - team_manifest: List[AgentConfig] - LLM-generated team

3. [cyan]HITL Team Approval[/cyan]
   - User reviews dynamically generated team
   - Can approve, reject, or add custom agents
   - Then graph executes with approved team

4. [cyan]Sequential Execution[/cyan]
   - Agents run one after another (parallel in Iteration 3)

[bold]Roadmap:[/bold]
• Iteration 1: ✅ The "Dumb" Loop - hardcoded agents
• Iteration 2: ✅ Dynamic Strategy - LLM-generated team
• Iteration 3: 🔄 Parallel Execution (fan-out/fan-in with Send)
• Iteration 4: 📝 Full Debate Loop & Consensus Detection
"""
    console.print(Panel.fit(info_text, border_style="cyan"))


if __name__ == "__main__":
    app()
