"""Bot Discord Bot Main Entry Point."""

from bot.core.app import BotApp


def run() -> int:
    """Instantiate and run the Bot application."""
    app = BotApp()
    return app.run()
