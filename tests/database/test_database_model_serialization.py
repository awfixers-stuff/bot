"""
🚀 Database Model Serialization Tests - SQLModel + py-pglite Integration Testing.

Tests for model serialization and data conversion using real database (py-pglite).
These are integration tests because they use a real PostgreSQL database.
"""

import pytest

from bot.database.models.models import Case, CaseType
from bot.database.service import DatabaseService


class TestModelSerialization:
    """📦 Test model serialization and data conversion."""

    @pytest.mark.integration
    @pytest.mark.database
    @pytest.mark.asyncio
    async def test_enum_serialization(self, db_service: DatabaseService) -> None:
        """Test enum field serialization in Case model."""
        async with db_service.session() as session:
            # Create case with enum
            case = Case(
                case_type=CaseType.WARN,
                case_number=1,
                case_reason="Test warning",
                case_user_id=12345,
                case_moderator_id=67890,
            )
            session.add(case)
            await session.commit()
            await session.refresh(case)

            # Test enum serialization
            case_dict = case.to_dict()
            assert case_dict["case_type"] == CaseType.WARN.name  # Should be enum name
