"""
Bot Database Module.

This module provides the core database functionality for the Bot Discord bot,
including SQLModel-based models, controllers for database operations, and
a unified database service interface.
"""

from .service import DatabaseService

# Clean, unified database service
__all__ = ["DatabaseService"]
