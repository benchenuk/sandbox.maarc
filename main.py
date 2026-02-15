#!/usr/bin/env python3
"""
Consensus-CLI: Iterative Multi-Agent Research Engine
MAARC V2 - Textual UI Entry Point
"""

from maarc.app import MaarcApp


def main():
    """Main entry point - launches TUI"""
    app = MaarcApp()
    app.run()


if __name__ == "__main__":
    main()
