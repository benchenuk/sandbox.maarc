#!/usr/bin/env python3
"""
Consensus-CLI: Iterative Multi-Agent Research Engine
Main entry point for the CLI application
"""

import sys
from typing import Optional
import typer
from rich.console import Console

# Add the consensus package to path
from consensus.cli import app as cli_app
from consensus.ui import display_banner, display_help

app = cli_app

# Main typer application
def main():
    """Main entry point for Consensus-CLI"""
    display_banner()
    app()

if __name__ == "__main__":
    main()
