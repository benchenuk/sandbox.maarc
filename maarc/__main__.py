#!/usr/bin/env python3
"""Entry point for running maarc as a module."""

from maarc.app import MaarcApp


def main():
    """Main entry point - launches TUI"""
    app = MaarcApp()
    app.run()


if __name__ == "__main__":
    main()
