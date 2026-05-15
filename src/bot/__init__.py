"""Bot - The all in one discord bot for the AWFixer Enterprising Inc Community.

This package provides a comprehensive Discord bot with modular architecture,
extensive functionality, and professional development practices.
"""

# Import the unified version system
from bot.shared.version import get_version

# Module-level version constant
# Uses the unified version system for consistency
__version__: str = get_version()
