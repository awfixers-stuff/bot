"""Tests for migration validator."""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.database.service import DatabaseService
from bot.plugins.v0_1_db_migrate.mapper import (
    ModelMapper,
)
from bot.plugins.v0_1_db_migrate.validator import (
    MigrationValidator,
)


@pytest.mark.asyncio
@pytest.mark.unit
class TestMigrationValidator:
    """Test MigrationValidator class."""

    @pytest.fixture
    def mapper(self) -> ModelMapper:
        """Create test mapper."""
        return ModelMapper()

    @pytest.fixture
    def old_db_engine(self):
        """Create old database engine."""
        return create_engine("sqlite:///:memory:")

    @pytest.fixture
    async def db_service(self, pglite_engine) -> DatabaseService:
        """Create test database service."""
        service = DatabaseService(echo=False)
        service._engine = pglite_engine

        service._session_factory = async_sessionmaker(
            pglite_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        return service

    @pytest.fixture
    def validator(
        self,
        mapper: ModelMapper,
        old_db_engine,
        db_service: DatabaseService,
    ) -> MigrationValidator:
        """Create test validator."""
        return MigrationValidator(mapper, old_db_engine, db_service)

    async def test_generate_validation_report_noop(
        self,
        validator: MigrationValidator,
    ) -> None:
        """Test validation report with no guild data."""
        report = await validator.generate_validation_report()

        assert "row_counts" in report
        assert "relationships" in report
        assert "constraints" in report
        assert "samples" in report
        assert "summary" in report
