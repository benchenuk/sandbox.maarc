"""
Markdown Report Generator
Generate research reports in Markdown format
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
import re

from rich.console import Console

console = Console()


def generate_report(
    topic: str,
    result: Dict[str, Any],
    output_dir: str = "reports",
) -> str:
    """
    Generate a markdown report from research results.

    Args:
        topic: Research topic
        result: Research results dictionary
        output_dir: Directory to save report

    Returns:
        Path to generated report
    """
    # Ensure output directory exists
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate filename
    safe_topic = re.sub(r'[^\w\s-]', '', topic)
    safe_topic = re.sub(r'[-\s]+', '-', safe_topic).lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"research_report_{safe_topic}_{timestamp}.md"
    filepath = output_path / filename

    # Build report content
    content = _build_report_content(topic, result)

    # Write to file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return str(filepath)


def _build_report_content(topic: str, result: Dict[str, Any]) -> str:
    """Build the markdown report content"""

    # Extract data from result
    iterations = result.get("iterations", 0)
    consensus_score = result.get("consensus_score", 0)
    consensus_reached = result.get("consensus_reached", False)

    final_research = result.get("final_research", "")
    final_critique = result.get("final_critique", "")
    final_design = result.get("final_design", "")
    final_estimate = result.get("final_estimate", "")

    agreements = result.get("agreements", [])
    conflicts = result.get("conflicts", [])

    # Build markdown
    lines = []

    # Title
    lines.append(f"# Research Report: {topic}")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # Executive Summary
    lines.append("## Executive Summary")
    lines.append("")
    status = "Achieved" if consensus_reached else "Partial"
    lines.append(f"This research on **{topic}** reached **{status}** consensus after {iterations} iteration(s).")
    lines.append(f"Consensus score: **{consensus_score:.0f}%**")
    lines.append("")

    # Research Process
    lines.append("## Research Process")
    lines.append("")
    lines.append(f"- **Topic:** {topic}")
    lines.append(f"- **Iterations:** {iterations}")
    lines.append(f"- **Consensus Reached:** {'Yes' if consensus_reached else 'No'}")
    lines.append(f"- **Consensus Score:** {consensus_score:.0f}%")
    lines.append("")

    # Key Agreements
    if agreements:
        lines.append("## Key Agreements")
        lines.append("")
        for agreement in agreements:
            lines.append(f"- {agreement}")
        lines.append("")

    # Unresolved Conflicts
    if conflicts:
        lines.append("## Unresolved Conflicts")
        lines.append("")
        lines.append("The following points remain unresolved:")
        lines.append("")
        for conflict in conflicts:
            lines.append(f"- {conflict}")
        lines.append("")

    # System Design
    if final_design:
        lines.append("## System Design")
        lines.append("")
        lines.append(_clean_markdown(final_design))
        lines.append("")

    # Research Findings
    if final_research:
        lines.append("## Research Findings")
        lines.append("")
        lines.append(_clean_markdown(final_research))
        lines.append("")

    # Critiques and Concerns
    if final_critique:
        lines.append("## Critiques and Concerns")
        lines.append("")
        lines.append(_clean_markdown(final_critique))
        lines.append("")

    # Effort Estimation
    if final_estimate:
        lines.append("## Effort Estimation")
        lines.append("")
        lines.append(_clean_markdown(final_estimate))
        lines.append("")

    # Recommendations
    lines.append("## Recommendations")
    lines.append("")
    if consensus_reached:
        lines.append("Based on the research, the following recommendations are provided:")
        lines.append("")
        lines.append("1. Review the system design and proceed with implementation")
        lines.append("2. Address any remaining concerns in the implementation phase")
        lines.append("3. Consider follow-up research for detailed technical specifications")
    else:
        lines.append("Consensus was not fully reached. Recommendations:")
        lines.append("")
        lines.append("1. Review the unresolved conflicts")
        lines.append("2. Consider additional research on contested areas")
        lines.append("3. Make final decisions based on specific project requirements")
    lines.append("")

    # Appendix
    lines.append("---")
    lines.append("")
    lines.append("## Appendix")
    lines.append("")
    lines.append("### Research Agents")
    lines.append("")
    lines.append("- **Researcher**: Gathers information and documents findings")
    lines.append("- **Critic**: Challenges assumptions and identifies flaws")
    lines.append("- **Architect**: Synthesizes findings into coherent designs")
    lines.append("- **Estimator**: Analyzes complexity and estimates efforts")
    lines.append("")

    # Iteration Details
    iteration_results = result.get("iteration_results", [])
    if iteration_results:
        lines.append("### Iteration Details")
        lines.append("")
        for i, iter_result in enumerate(iteration_results, 1):
            lines.append(f"**Iteration {i}**")
            lines.append(f"- Consensus Score: {iter_result.get('consensus_score', 0):.0f}%")
            lines.append("")

    return "\n".join(lines)


def _clean_markdown(text: str) -> str:
    """Clean and format text for markdown"""
    if not text:
        return ""

    # Remove any existing markdown headers that might interfere
    # but keep the content
    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        # Skip very long lines that might be artifacts
        if len(line) > 500:
            cleaned_lines.append(line[:500] + "...")
        else:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def format_iteration_summary(iteration: int, result: Dict[str, Any]) -> str:
    """Format a summary of a single iteration"""
    lines = []

    lines.append(f"### Iteration {iteration}")
    lines.append("")

    if result.get("researcher_output"):
        lines.append("**Research:**")
        lines.append(result["researcher_output"][:500])
        lines.append("")

    if result.get("critic_output"):
        lines.append("**Critique:**")
        lines.append(result["critic_output"][:500])
        lines.append("")

    if result.get("architect_output"):
        lines.append("**Design:**")
        lines.append(result["architect_output"][:500])
        lines.append("")

    if result.get("estimator_output"):
        lines.append("**Estimate:**")
        lines.append(result["estimator_output"][:500])
        lines.append("")

    return "\n".join(lines)
