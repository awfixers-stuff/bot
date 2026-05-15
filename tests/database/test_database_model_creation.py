"""
🚀 Database Model Creation Tests - SQLModel + py-pglite Integration Testing.

Tests for basic model creation and validation using real database (py-pglite).
These are integration tests because they use a real PostgreSQL database.
"""

import pytest

from bot.database.models.models import Case, CaseType
from bot.database.service import DatabaseService


class TestModelCreation:
    """🏗️ Test basic model creation and validation."""

    @pytest.mark.integration
    @pytest.mark.database
    @pytest.mark.asyncio
    async def test_case_model_creation(self, db_service: DatabaseService) -> None:
        """Test Case model creation with enum types."""
        async with db_service.session() as session:
            # Create case with enum
            case = Case(
                case_type=CaseType.BAN,
                case_number=1,
                case_reason="Test ban reason",
                case_user_id=12345,
                case_moderator_id=67890,
            )

            session.add(case)
            await session.commit()
            await session.refresh(case)

            # Verify case creation and enum handling
            assert case.case_type == CaseType.BAN
            assert case.case_number == 1
            assert case.case_reason == "Test ban reason"
            assert case.case_user_id == 12345
            assert case.case_moderator_id == 67890
