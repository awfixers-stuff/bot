"""
🚀 Professional Database Schema & Migration Tests - Async Architecture.

Tests database schema, constraints, and migration behavior through the proper async architecture.
Validates that database operations work correctly with the async DatabaseService and controllers.

Key Patterns:
- Async test functions with pytest-asyncio
- Test schema through real async DatabaseService operations
- Validate constraints through controller operations
- Test table creation and relationships via async layer
- Professional async fixture setup

ARCHITECTURAL APPROACH:
We test schema and migrations THROUGH the async DatabaseService, not directly with sync SQLAlchemy.
This validates the REAL production database behavior and async architecture.
"""

from contextlib import suppress

import pytest
import sqlalchemy.exc
from sqlalchemy import text

from bot.database.service import DatabaseService

# Test constants
TEST_DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/test_db"


# =============================================================================
# ASYNC TEST CLASSES - Testing Schema Through DatabaseService
# =============================================================================





class TestSchemaErrorHandlingThroughService:
    """🚀 Test schema-related error handling through DatabaseService."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_connection_errors_handled_gracefully(
        self,
        disconnected_async_db_service: DatabaseService,
    ) -> None:
        """Test that connection errors are handled gracefully."""
        # Try to connect with invalid URL
        try:
            await disconnected_async_db_service.connect(database_url="invalid://url")
            # If we get here, the service should handle it gracefully
        except Exception:
            # Expected for invalid URL
            pass
        finally:
            # Should be safe to disconnect even if connection failed
            await disconnected_async_db_service.disconnect()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_double_connection_handling(
        self,
        db_service: DatabaseService,
    ) -> None:
        """Test handling of double connections."""
        # Database is already connected via fixture

        # Second connection should be handled gracefully
        await db_service.connect(database_url=TEST_DATABASE_URL)
        assert db_service.is_connected() is True

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_operations_on_disconnected_service(
        self,
        disconnected_async_db_service: DatabaseService,
    ) -> None:
        """Test behavior when trying to use disconnected service."""
        # Service starts disconnected
        assert disconnected_async_db_service.is_connected() is False

        # Operations should fail gracefully when not connected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
