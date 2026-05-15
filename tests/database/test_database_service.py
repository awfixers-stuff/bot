"""
🚀 Database Service Tests - Self-Contained Testing.

This test suite uses py-pglite for all tests:
- ALL TESTS: Self-contained PostgreSQL in-memory using py-pglite
- No external dependencies required
- Full PostgreSQL feature support

Test Categories:
- @pytest.mark.integration: All tests use real database (py-pglite) via db_session or db_service fixtures
- Note: Even "unit" tests in this file use real database, so they are integration tests

Run modes:
- pytest tests/database/test_database_service.py             # All tests
- pytest tests/database/test_database_service.py -m unit     # Unit tests only
- pytest tests/database/test_database_service.py -m integration # Integration tests only
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.service import DatabaseService

# =============================================================================
# INTEGRATION TESTS - Fast SQLModel + py-pglite (Real Database)
# =============================================================================


class TestDatabaseModelsIntegration:
    """🌐 Integration tests for database models using SQLModel + py-pglite (real database)."""

    @pytest.mark.integration
    @pytest.mark.database
    @pytest.mark.asyncio
    async def test_raw_sql_execution(self, db_session: AsyncSession) -> None:
        """Test raw SQL execution with py-pglite."""
        # Test basic query
        result = await db_session.execute(text("SELECT 1 as test_value"))
        value = result.scalar()
        assert value == 1

        # Test PostgreSQL-specific features work with py-pglite
        result = await db_session.execute(text("SELECT version()"))
        version = result.scalar()
        assert version is not None
        assert "PostgreSQL" in str(version)


# =============================================================================
# INTEGRATION TESTS - Full Async DatabaseService + Real PostgreSQL
# =============================================================================


class TestDatabaseServiceIntegration:
    """🌐 Integration tests for DatabaseService using async SQLModel + PostgreSQL."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_async_service_initialization(
        self,
        db_service: DatabaseService,
    ) -> None:
        """Test async database service initialization."""
        assert db_service.is_connected() is True

        # Test health check
        health = await db_service.health_check()
        assert health["status"] == "healthy"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_async_connection_lifecycle(
        self,
        disconnected_async_db_service: DatabaseService,
    ) -> None:
        """Test async connection lifecycle management."""
        service = disconnected_async_db_service

        # Initially disconnected
        assert service.is_connected() is False

        # Connect
        test_db_url = "postgresql+asyncpg://botuser:botpass@localhost:5432/botdb"
        await service.connect(test_db_url)
        assert service.is_connected() is True

        # Disconnect
        await service.disconnect()
        assert service.is_connected() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
