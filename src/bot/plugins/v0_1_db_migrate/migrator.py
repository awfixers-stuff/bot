"""
Database migrator for executing data migration.

Handles the actual migration of data from old database to new database,
with transaction support, progress tracking, and error handling.
"""

from __future__ import annotations

from contextlib import suppress
from typing import Any

from loguru import logger
from rich.progress import Progress, SpinnerColumn, TextColumn
from sqlalchemy import delete, inspect, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import PermissionAssignment, PermissionRank
from bot.database.service import DatabaseService

from .config import MigrationConfig
from .extractor import DataExtractor
from .mapper import ModelMapper

# Migration order respecting foreign key dependencies
# Format: (old_db_table_name, new_model_table_name)
# Note: Guild and GuildConfig tables were removed in single-guild simplification.
# Permission ranks were previously migrated from GuildConfig.perm_level_*_role_id
# but that migration path is no longer available.
MIGRATION_ORDER: list[tuple[str, str]] = [
    ("Starboard", "starboard"),
    ("Case", "cases"),
    ("Snippet", "snippet"),
    ("Reminder", "reminder"),
    ("AFKModel", "afk"),  # Old DB table is "AFKModel"
    ("Levels", "levels"),
    ("StarboardMessage", "starboard_message"),
]


class DatabaseMigrator:
    """
    Execute database migration from old to new database.

    Handles batch processing, transactions, progress tracking,
    and error recovery for data migration.

    Attributes
    ----------
    config : MigrationConfig
        Migration configuration.
    mapper : ModelMapper
        Model mapper instance.
    extractor : DataExtractor
        Data extractor instance.
    db_service : DatabaseService
        Database service for new database.
    """

    def __init__(
        self,
        config: MigrationConfig,
        mapper: ModelMapper,
        extractor: DataExtractor,
        db_service: DatabaseService,
    ) -> None:
        """
        Initialize database migrator.

        Parameters
        ----------
        config : MigrationConfig
            Migration configuration.
        mapper : ModelMapper
            Model mapper instance.
        extractor : DataExtractor
            Data extractor instance.
        db_service : DatabaseService
            Database service for new database.
        """
        self.config = config
        self.mapper = mapper
        self.extractor = extractor
        self.db_service = db_service

    def _get_primary_key_fields(self, model_class: type[Any]) -> list[str]:
        """
        Get primary key field names from a SQLModel class.

        Parameters
        ----------
        model_class : type[Any]
            SQLModel class to inspect.

        Returns
        -------
        list[str]
            List of primary key field names.
        """
        mapper_obj = inspect(model_class)  # type: ignore[assignment]
        # Filter out None keys (shouldn't happen, but type checker needs it)
        return [
            col.key  # type: ignore[misc]
            for col in mapper_obj.primary_key  # type: ignore[attr-defined]
            if col.key is not None  # type: ignore[misc]
        ]

    def _validate_row_data(
        self,
        new_table_name: str,
        row_data: dict[str, Any],
    ) -> tuple[bool, str | None]:
        """
        Validate row data against model constraints before insertion.

        Parameters
        ----------
        new_table_name : str
            New SQLModel table name.
        row_data : dict[str, Any]
            Row data to validate.

        Returns
        -------
        tuple[bool, str | None]
            (is_valid, error_message). If valid, error_message is None.
        """
        # Levels-specific validation
        if new_table_name == "levels":
            xp = row_data.get("xp")
            level = row_data.get("level")

            # Validate xp (must be >= 0, numeric)
            if xp is not None:
                if not isinstance(xp, (int, float)):
                    return (
                        False,
                        f"Invalid xp type: {type(xp).__name__} (must be numeric)",
                    )
                if xp < 0:
                    return (
                        False,
                        f"Invalid xp value: {xp} (must be >= 0)",
                    )

            # Validate level (must be >= 0, integer, within INTEGER range)
            if level is not None:
                if not isinstance(level, (int, float)):
                    return (
                        False,
                        f"Invalid level type: {type(level).__name__} (must be numeric)",
                    )
                # Convert to int if float
                level_int = int(level) if isinstance(level, float) else level
                if level_int < 0:
                    return (
                        False,
                        f"Invalid level value: {level_int} (must be >= 0)",
                    )
                # Check for integer overflow (level is INTEGER, max is ~2.1 billion)
                if level_int > 2147483647:
                    return (
                        False,
                        f"Invalid level value: {level_int} (exceeds INTEGER max 2147483647)",
                    )
                # Update row_data with validated integer value
                row_data["level"] = level_int

        return True, None

    async def _get_existing_record(
        self,
        session: AsyncSession,
        model_class: type[Any],
        pk_values: dict[str, Any],
    ) -> Any | None:
        """
        Get existing record with the given primary key values.

        Parameters
        ----------
        session : AsyncSession
            Database session.
        model_class : type[Any]
            SQLModel class to check.
        pk_values : dict[str, Any]
            Dictionary mapping PK field names to values.

        Returns
        -------
        Any | None
            Existing record if found, None otherwise.
        """
        stmt = select(model_class)
        for field_name, field_value in pk_values.items():
            stmt = stmt.where(getattr(model_class, field_name) == field_value)
        result = await session.execute(stmt)
        # Call unique() to handle joined eager loads against collections
        return result.unique().scalar_one_or_none()

    async def migrate_table(  # noqa: PLR0912, PLR0915
        self,
        old_table_name: str,
        new_table_name: str,
        session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """
        Migrate a single table from old to new database.

        Parameters
        ----------
        old_table_name : str
            Old Prisma table name.
        new_table_name : str
            New SQLModel table name.
        session : AsyncSession | None, optional
            Database session to use. If None, creates a new session.
            If provided, does not commit/rollback (caller manages transaction).

        Returns
        -------
        dict[str, Any]
            Migration result with keys:
            - success: bool
            - rows_migrated: int
            - rows_failed: int
            - error: str | None

        Notes
        -----
        Uses transactions for atomicity. If dry_run is enabled,
        changes are rolled back after migration.
        If session is provided, caller is responsible for commit/rollback.
        """
        logger.info(f"Starting migration: {old_table_name} -> {new_table_name}")

        if not self.config.is_table_enabled(new_table_name):
            logger.info(f"Skipping table '{new_table_name}' (disabled in config)")
            return {
                "success": True,
                "rows_migrated": 0,
                "rows_failed": 0,
                "error": None,
            }

        model_class = self.mapper.get_model_class(new_table_name)
        pk_fields = self._get_primary_key_fields(model_class)
        rows_migrated = 0
        rows_failed = 0

        try:
            # Get total row count for progress tracking
            total_rows = self.extractor.get_row_count(old_table_name)
            logger.info(f"Migrating {total_rows} rows from '{old_table_name}'")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
            ) as progress:
                task = progress.add_task(
                    f"Migrating {old_table_name}...",
                    total=total_rows,
                )

                # Use provided session or create new one
                use_provided_session = session is not None

                if use_provided_session:
                    assert session is not None  # Type guard
                    # Use provided session - caller manages transaction
                    # Process in batches
                    for batch in self.extractor.extract_table(old_table_name):
                        try:
                            # Insert batch
                            for row_data in batch:
                                try:
                                    # Validate row (extractor validation)
                                    is_valid, error_msg = self.extractor.validate_row(
                                        new_table_name,
                                        row_data,
                                    )
                                    if not is_valid:
                                        rows_failed += 1
                                        logger.warning(
                                            f"Invalid row skipped: {error_msg}",
                                        )
                                        continue

                                    # Additional data validation (constraints, ranges)
                                    is_valid, error_msg = self._validate_row_data(
                                        new_table_name,
                                        row_data,
                                    )
                                    if not is_valid:
                                        rows_failed += 1
                                        logger.warning(
                                            f"Invalid row data skipped: {error_msg}",
                                        )
                                        continue

                                    # Check if record already exists (update instead of skip)
                                    # Ensure all PK fields are present
                                    pk_values: dict[str, Any] = {}  # type: ignore[no-redef]
                                    missing_pk = False
                                    for field in pk_fields:
                                        if field not in row_data:
                                            logger.warning(
                                                f"Missing PK field '{field}' in row data, skipping row",
                                            )
                                            rows_failed += 1
                                            missing_pk = True
                                            break
                                        pk_values[field] = row_data[field]

                                    if not missing_pk:
                                        # All PK fields present, proceed with check
                                        existing_record = (
                                            await self._get_existing_record(
                                                session,
                                                model_class,
                                                pk_values,
                                            )
                                        )

                                        if existing_record:
                                            # Update existing record with data from old database
                                            for (
                                                field_name,
                                                field_value,
                                            ) in row_data.items():
                                                # Skip PK fields and timestamp fields (created_at/updated_at)
                                                # as they should be preserved from the new database
                                                # Also skip None values to avoid overwriting with None
                                                if (
                                                    field_name not in pk_fields
                                                    and field_name
                                                    not in (
                                                        "created_at",
                                                        "updated_at",
                                                    )
                                                    and field_value is not None
                                                ):
                                                    setattr(
                                                        existing_record,
                                                        field_name,
                                                        field_value,
                                                    )
                                            rows_migrated += 1
                                            logger.debug(
                                                f"Updated existing record: {pk_values}",
                                            )
                                        else:
                                            # Create new record
                                            instance = model_class(**row_data)
                                            session.add(instance)
                                            rows_migrated += 1

                                except Exception as e:
                                    # Any error during row processing should stop migration immediately
                                    error_msg = f"Failed to migrate row: {e}"
                                    logger.error(error_msg)
                                    rows_failed += 1
                                    # Re-raise to stop migration immediately
                                    migration_error = f"Migration stopped due to row processing error: {e}"
                                    raise RuntimeError(migration_error) from e

                            # Flush batch (don't commit - caller manages transaction)
                            try:
                                await session.flush()
                            except SQLAlchemyError as flush_error:
                                # Session is in bad state after flush error - rollback and stop
                                error_str = str(flush_error)

                                # Check for unique constraint violations (e.g., duplicate case_number)
                                if (
                                    "uq_case_guild_case_number" in error_str
                                    or "unique constraint" in error_str.lower()
                                ):
                                    logger.error(
                                        f"Unique constraint violation during migration: {flush_error}. "
                                        f"This may indicate duplicate case_number values in the old database. "
                                        f"Check the old database for duplicate (guild_id, case_number) pairs.",
                                    )
                                else:
                                    logger.error(
                                        f"Database error during flush: {flush_error}",
                                    )

                                await session.rollback()
                                rows_failed += len(batch)
                                # Re-raise to stop migration immediately
                                raise

                            progress.update(task, advance=len(batch))

                        except SQLAlchemyError as e:
                            logger.error(f"Database error during migration: {e}")
                            # Ensure session is rolled back
                            with suppress(Exception):
                                await session.rollback()
                            rows_failed += len(batch)
                            # Always raise on database errors - let caller handle rollback
                            raise
                        except KeyboardInterrupt:
                            logger.error("Migration interrupted by user (Ctrl+C)")
                            await session.rollback()
                            raise
                else:
                    # Create our own session
                    async with self.db_service.session() as db_session:
                        # Process in batches
                        for batch in self.extractor.extract_table(old_table_name):
                            try:
                                # Insert batch
                                for row_data in batch:
                                    try:
                                        # Validate row
                                        is_valid, error_msg = (
                                            self.extractor.validate_row(
                                                new_table_name,
                                                row_data,
                                            )
                                        )
                                        if not is_valid:
                                            rows_failed += 1
                                            logger.warning(
                                                f"Invalid row skipped: {error_msg}",
                                            )
                                            continue

                                        # Check if record already exists (update instead of skip)
                                        # Ensure all PK fields are present
                                        pk_values: dict[str, Any] = {}
                                        for field in pk_fields:
                                            if field not in row_data:
                                                logger.warning(
                                                    f"Missing PK field '{field}' in row data, skipping row",
                                                )
                                                rows_failed += 1
                                                break
                                            pk_values[field] = row_data[field]
                                        else:
                                            # All PK fields present, proceed with check
                                            existing_record = (
                                                await self._get_existing_record(
                                                    db_session,
                                                    model_class,
                                                    pk_values,
                                                )
                                            )

                                            if existing_record:
                                                # Update existing record with data from old database
                                                for (
                                                    field_name,
                                                    field_value,
                                                ) in row_data.items():
                                                    # Skip PK fields and timestamp fields (created_at/updated_at)
                                                    # as they should be preserved from the new database
                                                    # Also skip None values to avoid overwriting with None
                                                    if (
                                                        field_name not in pk_fields
                                                        and field_name
                                                        not in (
                                                            "created_at",
                                                            "updated_at",
                                                        )
                                                        and field_value is not None
                                                    ):
                                                        setattr(
                                                            existing_record,
                                                            field_name,
                                                            field_value,
                                                        )
                                                rows_migrated += 1
                                                logger.debug(
                                                    f"Updated existing record: {pk_values}",
                                                )
                                            else:
                                                # Create new record
                                                instance = model_class(**row_data)
                                                db_session.add(instance)
                                                rows_migrated += 1

                                    except Exception as e:
                                        # Any error during row processing should stop migration immediately
                                        error_msg = f"Failed to migrate row: {e}"
                                        logger.error(error_msg)
                                        rows_failed += 1
                                        # Re-raise to stop migration immediately
                                        migration_stopped_msg = f"Migration stopped due to row processing error: {e}"
                                        raise RuntimeError(migration_stopped_msg) from e

                                # Flush batch before commit
                                try:
                                    await db_session.flush()
                                except SQLAlchemyError as flush_error:
                                    # Session is in bad state after flush error - rollback and stop
                                    error_str = str(flush_error)

                                    # Check for unique constraint violations (e.g., duplicate case_number)
                                    if (
                                        "uq_case_guild_case_number" in error_str
                                        or "unique constraint" in error_str.lower()
                                    ):
                                        logger.error(
                                            f"Unique constraint violation during migration: {flush_error}. "
                                            f"This may indicate duplicate case_number values in the old database. "
                                            f"Check the old database for duplicate (guild_id, case_number) pairs.",
                                        )
                                    else:
                                        logger.error(
                                            f"Database error during flush: {flush_error}",
                                        )

                                    await db_session.rollback()
                                    rows_failed += len(batch)
                                    # Re-raise to stop migration immediately
                                    raise

                                # Commit batch (or rollback if dry_run)
                                if self.config.dry_run:
                                    await db_session.rollback()
                                    logger.info("Dry-run mode: rolled back changes")
                                else:
                                    await db_session.commit()

                                progress.update(task, advance=len(batch))

                            except SQLAlchemyError as e:
                                logger.error(f"Database error during migration: {e}")
                                # Ensure session is rolled back
                                with suppress(Exception):
                                    await db_session.rollback()
                                rows_failed += len(batch)
                                raise
                            except KeyboardInterrupt:
                                logger.error("Migration interrupted by user (Ctrl+C)")
                                await db_session.rollback()
                                raise
        except KeyboardInterrupt:
            logger.error("Migration interrupted by user (Ctrl+C)")
            return {
                "success": False,
                "rows_migrated": rows_migrated,
                "rows_failed": rows_failed,
                "error": "Migration interrupted by user",
            }
        except Exception as e:
            error_msg = f"Migration failed: {e}"
            logger.error(error_msg)
            return {
                "success": False,
                "rows_migrated": rows_migrated,
                "rows_failed": rows_failed,
                "error": error_msg,
            }
        else:
            # Migration completed successfully
            logger.success(
                f"Migration complete: {old_table_name} -> {new_table_name} "
                f"({rows_migrated} migrated, {rows_failed} failed)",
            )

            return {
                "success": True,
                "rows_migrated": rows_migrated,
                "rows_failed": rows_failed,
                "error": None,
            }

    async def migrate_all(self) -> dict[str, dict[str, Any]]:  # noqa: PLR0915
        """
        Migrate all tables in dependency order.

        Returns
        -------
        dict[str, dict[str, Any]]
            Dictionary mapping table names to migration results.

        Notes
        -----
        Tables are migrated in dependency order to respect foreign keys.
        Entire migration is atomic - if any table fails, all changes are rolled back.
        """
        logger.info("Starting full database migration")

        results: dict[str, dict[str, Any]] = {}

        # Use a single transaction for the entire migration
        # On any failure, rollback everything
        async with self.db_service.session() as session:
            try:
                for old_table_name, new_table_name in MIGRATION_ORDER:
                    if not self.config.is_table_enabled(new_table_name):
                        logger.info(f"Skipping table '{new_table_name}' (disabled)")
                        continue

                    result = await self.migrate_table(
                        old_table_name,
                        new_table_name,
                        session=session,
                    )
                    results[new_table_name] = result

                    # Stop immediately on any failure
                    if not result["success"]:
                        error_msg = result.get("error", "Unknown error")
                        logger.error(
                            f"Migration failed for '{new_table_name}': {error_msg}",
                        )
                        logger.error("Rolling back all changes...")
                        await session.rollback()
                        logger.error("All changes rolled back. Migration stopped.")
                        # Raise exception to prevent context manager from committing
                        migration_failed_msg = (
                            f"Migration failed for '{new_table_name}': {error_msg}"
                        )
                        raise RuntimeError(migration_failed_msg)  # noqa: TRY301

                    # Note: Permission rank migration (migrate_permission_ranks) has been
                    # removed because it depended on GuildConfig model which no longer exists.
                    # Permission ranks should be configured via the new permission system.

                # If we got here without breaking, commit everything
                if all(r["success"] for r in results.values()):
                    if self.config.dry_run:
                        await session.rollback()
                        logger.info("Dry-run mode: rolled back all changes")
                    else:
                        await session.commit()
                        logger.success(
                            "Migration completed successfully - all changes committed",
                        )

            except KeyboardInterrupt:
                # User interrupted - rollback and stop
                logger.error("Migration interrupted by user (Ctrl+C)")
                logger.error("Rolling back all changes...")
                await session.rollback()
                logger.error("All changes rolled back. Migration stopped.")
                raise
            except Exception as e:
                # Any unhandled exception - rollback everything
                logger.error(f"Unexpected error during migration: {e}")
                logger.error("Rolling back all changes...")
                await session.rollback()
                logger.error("All changes rolled back. Migration stopped.")
                raise

        # Summary
        total_migrated = sum(r["rows_migrated"] for r in results.values())
        total_failed = sum(r["rows_failed"] for r in results.values())
        successful_tables = sum(1 for r in results.values() if r["success"])

        logger.info(
            f"Migration summary: {successful_tables}/{len(results)} tables successful, "
            f"{total_migrated} rows migrated, {total_failed} rows failed",
        )

        return results

    async def rollback_table(self, table_name: str) -> bool:
        """
        Rollback migration for a single table (delete all rows).

        Parameters
        ----------
        table_name : str
            Table name to rollback.

        Returns
        -------
        bool
            True if rollback successful, False otherwise.

        Notes
        -----
        This deletes all rows from the table. Use with caution!
        Only works if table has no foreign key dependencies from other tables.
        """
        logger.warning(f"Rolling back table '{table_name}' (deleting all rows)")

        try:
            model_class = self.mapper.get_model_class(table_name)

            async with self.db_service.session() as session:
                # Delete all rows
                stmt = delete(model_class)
                await session.execute(stmt)

                if self.config.dry_run:
                    await session.rollback()
                    logger.info("Dry-run mode: rolled back deletion")
                else:
                    await session.commit()
        except Exception as e:
            logger.error(f"Rollback failed for '{table_name}': {e}")
            return False
        else:
            logger.success(f"Rollback complete for '{table_name}'")
            return True
