"""
Bot Command Group.

Aggregates all bot-related operations.
"""

from scripts.bot import start, version
from scripts.core import create_app

app = create_app(name="bot", help_text="Bot operations")

app.add_typer(start.app)
app.add_typer(version.app)


def main() -> None:
    """Entry point for the bot command group."""
    app()
