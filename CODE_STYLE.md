# Code Style

This document describes the coding conventions and patterns used in **Bot**, derived from the actual codebase, config files, and linting setup.

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Files/directories | `snake_case` | `base_cog.py`, `permission_system.py` |
| Classes | `PascalCase` | `class BotApp`, `class DatabaseService` |
| Functions/methods | `snake_case` | `def configure_logging()`, `async def setup_hook()` |
| Variables | `snake_case` | `guild_id`, `owner_ids`, `load_time` |
| Constants | `UPPER_SNAKE_CASE` | `EMBED_COLORS`, `COG_PRIORITIES`, `DEFAULT_REASON` |
| Private attrs/methods | `_leading_underscore` | `_state`, `_startup_task`, `_close_connections()` |
| "Private" modules | `_prefix` (no, not used) | All modules are public |
| Type aliases | `PascalCase` | `RankDefinition`, `F = TypeVar("F")` |
| Enums | `PascalCase` members | `class CaseType: JAIL, WARN, KICK` |
| Tests | `test_<subject>` | `test_database_service.py`, `test_jail_system.py` |
| Test classes | `Test*` | `class TestDatabaseService` |
| Test functions | `test_*` | `test_create_case_success()` |
| Cog files | `snake_case` | `ban.py`, `purge.py`, `snippetban.py` |

## File Organization

```
module.py
├── """Module docstring (NumPy style)"""
├── from __future__ import annotations
├── Standard library imports
├── Third-party imports
├── Local imports
├── if TYPE_CHECKING: block (optional)
├── __all__ = [...] (explicit exports)
├── Constants (module-level, UPPER_CASE)
├── Classes (one per file where possible)
└── Functions
```

**Rules**:
- One class per file is preferred, especially for cogs
- No `__init__.py` code besides imports and docstrings
- Module docstrings explain **what** the module provides
- Class docstrings explain **responsibility** and **attributes**
- Method docstrings explain **behavior**, **parameters**, **returns**, **raises**

## Import Style

```python
from __future__ import annotations  # Always first (if used)

import asyncio
import contextlib
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import discord
from discord.ext import commands
from loguru import logger

from bot.core.permission_system import PermissionSystem
from bot.shared.config import CONFIG
from bot.shared.exceptions import BotPermissionDeniedError

if TYPE_CHECKING:
    from bot.core.bot import Bot
```

**Rules** (enforced by Ruff `I`):
1. `from __future__ import annotations` (optional, first)
2. Standard library
3. Third-party libraries (discord, loguru, sqlalchemy, etc.)
4. Local (`bot.*`) imports
5. `if TYPE_CHECKING:` guard for type-only imports
- Sort alphabetically within each group

## Docstring Style

**NumPy convention** (enforced by pydoclint + Ruff D):

```python
def configure_logging(
    environment: str | None = None,
    level: str | None = None,
    config: Config | None = None,
) -> None:
    """
    Brief summary line.

    Longer description if needed. Explain parameters, behavior, edge cases.

    Parameters
    ----------
    environment : str | None, optional
        Deprecated parameter, kept for backward compatibility.
    level : str | None, optional
        Explicit log level override (for testing). Highest priority.
    config : Config | None, optional
        Config instance with LOG_LEVEL and DEBUG from .env file.

    Raises
    ------
    ValueError
        If the log level is not valid.

    Examples
    --------
    >>> configure_logging(config=CONFIG)
    >>> configure_logging(level="DEBUG")
    """
```

**Rules**:
- Every public function/class/method needs a docstring
- `__init__` docstrings are allowed (`allow-init-docstring = true`)
- Short docstrings can skip sections (`skip-checking-short-docstrings = true`)
- Return section optional when returning nothing
- Arg type hints in both signature AND docstring

## Code Patterns

### Cog Definition

```python
class BanCog(BaseCog):
    """Moderation ban commands."""

    def __init__(self, bot: Bot) -> None:
        super().__init__(bot)

    @commands.hybrid_command(name="ban")
    @commands.has_permissions(ban_members=True)
    @requires_command_permission()
    async def ban(
        self,
        ctx: commands.Context[Bot],
        member: discord.Member,
        *,
        reason: str = "No reason provided",
    ) -> None:
        ...  # Implementation
```

### Error Handling

```python
try:
    result = await some_operation()
except BotDatabaseConnectionError as e:
    logger.error(f"Database connection failed: {e}")
    capture_database_error(e, operation="connection")
    raise
except ValueError as e:
    logger.warning(f"Invalid input: {e}")
    await ctx.send(f"Error: {e}", ephemeral=True)
    return
except Exception as e:  # Catch-all with comment justifying it
    logger.exception(f"Unexpected error in {operation}")
    capture_exception_safe(e)
    await ctx.send("An unexpected error occurred.", ephemeral=True)
```

**Guidelines**:
- Catch specific exceptions first, fallback to `Exception` as last resort
- Always comment why a broad `except` is used
- Use `logger.exception()` in except blocks for traceback
- Use `capture_exception_safe()` for Sentry reporting
- Prefer early returns over deep nesting

### Async Patterns

```python
# Always async for I/O
async def get_user(self, user_id: int) -> User | None:
    ...

# Run CPU-bound work in thread
result = await asyncio.to_thread(cpu_intensive_function, arg)

# Concurrent operations within priority groups
results = await asyncio.gather(
    *[load_single_cog(cog) for cog in group],
    return_exceptions=True,
)

# Lazy property pattern (deferred init)
@property
def db(self) -> DatabaseCoordinator:
    if self._db_coordinator is None:
        self._db_coordinator = DatabaseCoordinator(self.db_service)
    return self._db_coordinator
```

### Logging

```python
from loguru import logger

logger.trace("Very detailed debug")          # TRACE (most verbose)
logger.debug(f"Loading cog {name}")           # DEBUG
logger.info(f"Bot connected to {guild_count} guilds")  # INFO
logger.success("Setup completed")             # SUCCESS
logger.warning(f"Skipping {cog} - no config") # WARNING
logger.error(f"Failed to load {module}")      # ERROR
logger.exception("Database error")            # ERROR + traceback
logger.critical("No bot token!")              # CRITICAL

# Structured logging
logger.bind(operation="db_query", duration=0.123).info("Query completed")
```

### Configuration Access

```python
from bot.shared.config import CONFIG

# Direct attribute access
token = CONFIG.BOT_TOKEN
debug = CONFIG.DEBUG

# Via computed property
db_url = CONFIG.database_url

# Via method
prefix = CONFIG.get_prefix()
ignore_list = CONFIG.get_cog_ignore_list()

# Nested config (from BaseCog)
self.get_config("BOT_INFO.BOT_NAME", default="Bot")
```

### Sentry Integration

```python
from bot.services.sentry import capture_exception_safe, capture_database_error
from bot.services.sentry.tracing import start_span, start_transaction

# Report errors
capture_exception_safe(e, extra_context={"operation": "load_cog"})
capture_database_error(e, operation="connection")

# Trace operations
with start_span("bot.setup", "Bot setup process") as span:
    span.set_data("key", value)

# Transaction for multi-step flows
with start_transaction("bot.shutdown", "Shutdown") as transaction:
    ...
```

## Error Handling

**Exception hierarchy** (`src/bot/shared/exceptions/`):
- `BotError` (base)
  - `BotConfigurationError`
  - `BotCogLoadError`
  - `BotDatabaseError`
    - `BotDatabaseConnectionError`
  - `BotPermissionDeniedError`
  - `BotAPIError`
  - `BotServiceError`

**Pattern**: Raise domain-specific exceptions. Catch broadly only at boundaries (cog commands, service entry points). Convert external errors to domain exceptions.

## Testing

```python
# File: tests/database/test_database_service.py
"""Tests for the database service."""

import pytest

class TestDatabaseService:
    """Test suite for DatabaseService."""

    async def test_connect_success(self, db_service):
        """Test successful database connection."""
        ...

    async def test_connect_failure(self, db_service):
        """Test connection failure handling."""
        ...

    @pytest.mark.database
    async def test_session_commit(self, db_session):
        """Test session commit and rollback."""
        ...
```

**Patterns**:
- One test file per module/feature: `tests/<domain>/test_<feature>.py`
- Fixtures in `tests/fixtures/` (database_fixtures, data_fixtures, sentry_fixtures)
- Test functions use `async def` for async code
- Markers for categorization: `@pytest.mark.database`, `@pytest.mark.integration`, etc.
- Network disabled by default; use `httpx_mock` or `@pytest.mark.enable_socket`
- Database tests use **py-pglite** (in-memory Postgres) for speed
- `--asyncio-mode=auto` — no need for `@pytest.mark.asyncio`

## Linter & Formatter Configuration

**Ruff** (from `pyproject.toml`):
- Line length: **88**
- Target: **Python 3.13**
- Indent: **4 spaces**
- Quote style: **double quotes**
- Selected rulesets: `I, E, F, PERF, N, TRY, UP, FURB, PL, B, SIM, ASYNC, A, C4, DTZ, EM, PIE, T20, Q, RET, PTH, INP, RSE, ICN, PT, D, RUF`
- Ignored: `E501` (line-length, defer to formatter), `N814`, `PLR0913`, `PLR2004`, `E402`, `RUF022`
- Docstring convention: **NumPy**

**Pydoclint**: NumPy style, arg type hints in docstring + signature, check return/yield types.

**basedpyright**: `strict` mode for `src/`, relaxed for `tests/` and `scripts/`.

**pre-commit**: Check JSON/TOML, EOF fixer, trailing whitespace, yamlfix, yamllint, actionlint, markdownlint, trailing commas, ruff, pydoclint, shellcheck, shfmt, gitleaks, commitlint.

## Do's and Don'ts

### Do
- ✅ Use `from __future__ import annotations` for type safety
- ✅ Use `typing.TYPE_CHECKING` for circular import-safe type hints
- ✅ Use `loguru` over `logging` standard library
- ✅ Use `pathlib.Path` over `os.path` (enforced by Ruff `PTH`)
- ✅ Use `f-string` formatting for all string interpolation
- ✅ Use `async/await` for all I/O operations
- ✅ Use `@requires_command_permission()` for command access control
- ✅ Use `self.bot.db` (or `self.db` in cogs) for database access
- ✅ Handle graceful startup with `unload_if_missing_config()` for optional features
- ✅ Write docstrings in NumPy format for all public APIs

### Don't
- ❌ Don't use `print()` (enforced by Ruff `T20`) — use `logger.*`
- ❌ Don't use bare `except:` — catch specific exceptions
- ❌ Don't use `os.path` — use `pathlib.Path`
- ❌ Don't mix sync and async DB access
- ❌ Don't ignore `asyncio.gather` results unless using `return_exceptions=True`
- ❌ Don't put business logic in models — use controllers
- ❌ Don't hardcode config values — use `CONFIG` or `self.get_config()`
- ❌ Don't use wildcard imports (`from module import *`)
- ❌ Don't commit `.env` files (use `.env.example`)

## Pre-commit Workflow

All changes must pass pre-commit before commit. Run manually:

```bash
uv run dev all          # Full quality check
uv run dev lint         # Ruff only
uv run dev format       # Ruff format only
uv run dev type_check   # basedpyright only
```

Pre-commit runs automatically on `git commit`. If hooks modify files (`ruff-format`, `yamlfix`, `end-of-file-fixer`), stage and retry.
