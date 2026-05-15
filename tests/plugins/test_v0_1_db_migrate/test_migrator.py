"""Tests for database migrator."""

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.database.models import PermissionAssignment, PermissionRank
from bot.database.service import DatabaseService
from bot.plugins.v0_1_db_migrate.config import (
    MigrationConfig,
)
from bot.plugins.v0_1_db_migrate.extractor import (
    DataExtractor,
)
from bot.plugins.v0_1_db_migrate.mapper import (
    ModelMapper,
)
from bot.plugins.v0_1_db_migrate.migrator import (
    DatabaseMigrator,
)


@pytest.mark.asyncio
@pytest.mark.unit
class TestDatabaseMigrator:
    """Test DatabaseMigrator class."""

    @pytest.fixture
    def config(self) -> MigrationConfig:
        """Create test config."""
        return MigrationConfig(old_database_url="sqlite:///:memory:", batch_size=10)

    @pytest.fixture
    def mapper(self) -> ModelMapper:
        """Create test mapper."""
        return ModelMapper()

    @pytest.fixture
    def extractor(self, config: MigrationConfig, mapper: ModelMapper) -> DataExtractor:
        """Create test extractor."""
        return DataExtractor(config, mapper)

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
    def old_db_engine(self):
        """Create old database engine."""
        return create_engine("sqlite:///:memory:")

    @pytest.fixture
    def migrator(
        self,
        config: MigrationConfig,
        mapper: ModelMapper,
        extractor: DataExtractor,
        db_service: DatabaseService,
    ) -> DatabaseMigrator:
        """Create test migrator."""
        return DatabaseMigrator(config, mapper, extractor, db_service)

    async def test_init(self, migrator: DatabaseMigrator) -> None:
        """Test initialization."""
        assert migrator.config is not None
        assert migrator.mapper is not None
        assert migrator.extractor is not None
        assert migrator.db_service is not None
