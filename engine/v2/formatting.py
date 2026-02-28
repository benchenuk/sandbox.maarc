"""
V2 Formatting Utilities
Text wrapping and pane formatting for UI display.
"""

from typing import List, Dict, Union


def format_pane(items: Union[List[Dict], Dict, List[str]], 
                title: str = None,
                item_label_key: str = None,
                item_content_key: str = None,
                use_bullets: bool = False,
                label_color: str = None,
                bg_style: str = "on grey23", 
                text_style: str = "grey82") -> str:
    """
    Format content items as a styled pane with wrapped text.
    
    Supports three formats:
    1. List of dicts: [{label_key: str, content_key: str}, ...] - for team data
    2. Dict: {label: content, ...} - for agent summaries
    3. List of strings: [content, ...] - for takeaways (uses bullets if use_bullets=True)
    
    Args:
        items: Content to format (list of dicts, dict, or list of strings)
        title: Optional title for the pane
        item_label_key: Key for label when items is list of dicts
        item_content_key: Key for content when items is list of dicts
        use_bullets: Whether to use bullet points (for list of strings)
        label_color: Rich color for labels (e.g., "cyan", "bold")
        bg_style: Background style for the pane
        text_style: Text style for the content
        
    Returns:
        Formatted multi-line string ready for logging
    """
    import textwrap
    
    lines = []
    all_content = []
    
    # Normalize items to list of (label, content) tuples
    normalized_items = []
    if isinstance(items, dict):
        # Dict format: {label: content}
        for label, content in items.items():
            if content:
                normalized_items.append((label, content))
    elif items and isinstance(items[0], dict):
        # List of dicts format
        for item in items:
            label = item.get(item_label_key, "") if item_label_key else ""
            content = item.get(item_content_key, "") if item_content_key else str(item)
            if content:
                normalized_items.append((label, content))
    else:
        # List of strings format
        for content in items:
            if content:
                normalized_items.append(("", content))
    
    if not normalized_items:
        return ""
    
    # Calculate pane width based on all content
    for label, content in normalized_items:
        if label:
            all_content.append(f"{label}: {content}")
        else:
            all_content.append(content)
    
    max_natural = max((len(c) for c in all_content), default=0)
    # Add padding for label prefix and margins
    max_label_len = max((len(label) for label, _ in normalized_items), default=0) if any(l for l, _ in normalized_items) else 0
    pane_width = min(max(max_natural + 4, 80), 100)
    text_width = pane_width - max_label_len - 8 if not use_bullets else pane_width - 8
    
    # Build the pane
    lines.append(f"[{bg_style}]" + " " * pane_width + f"[/{bg_style}]")
    
    # Title row
    if title:
        title_len = len(title)
        title_padding = " " * (pane_width - title_len - 4)
        lines.append(f"[{text_style} {bg_style}]  [bold]{title}[/bold]{title_padding}[/{text_style} {bg_style}]")
        lines.append(f"[{bg_style}]" + " " * pane_width + f"[/{bg_style}]")
    
    # Content rows
    for i, (label, content) in enumerate(normalized_items):
        # Label row (if present)
        if label:
            label_display = f"[{label_color}]{label}[/]" if label_color else label
            label_padding = " " * (pane_width - (len(label) + 4))
            lines.append(f"[{text_style} {bg_style}]  {label_display}:{label_padding}[/{text_style} {bg_style}]")
        
        # Content (wrapped)
        prefix = "  • " if use_bullets else "    "
        wrapped_lines = textwrap.wrap(content, width=text_width)
        for j, line in enumerate(wrapped_lines):
            if use_bullets and j > 0:
                line_prefix = "    "
            else:
                line_prefix = prefix
            content_line = f"{line_prefix}{line}"
            padding = " " * (pane_width - len(content_line))
            lines.append(f"[{text_style} {bg_style}]{content_line}{padding}[/{text_style} {bg_style}]")
        
        # Gap between items (except last)
        lines.append(f"[{bg_style}]" + " " * pane_width + f"[/{bg_style}]")
    
    return "\n".join(lines)


def format_team_pane(team_data: List[Dict], bg_style: str = "on grey23", text_style: str = "grey82") -> str:
    """Format team data as a styled pane."""
    return format_pane(
        team_data,
        item_label_key="role",
        item_content_key="goal",
        label_color="bold",
        bg_style=bg_style,
        text_style=text_style
    )


def format_takeaways_pane(takeaways: List[str], bg_style: str = "on grey23", text_style: str = "grey82") -> str:
    """Format key takeaways as a styled pane with bullet points."""
    return format_pane(
        takeaways,
        title="Key Takeaways",
        use_bullets=True,
        bg_style=bg_style,
        text_style=text_style
    )


def format_agent_summaries_pane(summaries: Dict[str, str], title: str = "Agent Summaries",
                                 bg_style: str = "on grey23", text_style: str = "grey82") -> str:
    """Format agent summaries as a styled pane."""
    return format_pane(
        summaries,
        title=title,
        label_color="cyan",
        bg_style=bg_style,
        text_style=text_style
    )
