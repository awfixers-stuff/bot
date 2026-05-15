# Code Style

This document captures the coding conventions and patterns used throughout **Bot**. All new code should follow these conventions unless a specific exception is justified.

## Naming Conventions

| Category | Convention | Example |
|----------|-----------|---------|
| Classes | PascalCase | `class BotSetupOrchestrator`, `class EmbedCreator` |
| Exceptions | `Bot` prefix + PascalCase | `class BotDatabaseConnectionError(BotError)` |
| Functions/Methods | `snake_case` | `async def send_after_defer()`, `def get_prefix_cache_stats()` |
| Private methods | `_` prefix + `snake_case` | `async def _post_ready_startup()` |
| Variables | `snake_case` | `guild_id`, `setup_complete`, `self.start_time` |
| Private attributes | `_` prefix + `snake_case` | `self._banner_logged`, `self._emoji_manager_initialized` |
| Constants | `UPPER_SNAKE_CASE` | `EMBED_COLORS`, `COG_PRIORITIES`, `HTTP_TIMEOUT` |
| Modules/Files | `snake_case` | `base_cog.py`, `permission_system.py`, `prefix_manager.py` |
| Packages | Single short word | `cache/`, `database/`, `services/` |

> **Exception hierarchy**: All project exceptions extend `BotError` (in `bot.shared.exceptions.base`). Domain-specific exceptions live in their own module under `bot.shared.exceptions.*`.

## Type Hints

**All functions must have complete type hints.** The codebase uses Python 3.13 features.

```python
# Union syntax (preferred over Optional)
def get_prefix(bot: Bot, message: discord.Message) -> list[str]: ...
self.start_time: float | None = None

# Generic type syntax (Python 3.12+)
class BaseController[ModelT]: ...

# TYPE_CHECKING for import cycles
if TYPE_CHECKING:
    from bot.shared.config.settings import Config

# __future__ annotations at top of every module
from __future__ import annotations
```

## File Organization

Every module follows this structure:

```python
"""Module docstring in triple quotes."""
from __future__ import annotations

import stdlib       # Standard library first (blank line after)
import third_party  # Third-party imports (blank line after)
from local import ...  # Local imports (blank line after)

__all__ = [...]     # Explicit exports

# Classes (PascalCase)
# Functions (snake_case)
# Module-level constants (UPPER_SNAKE_CASE=) go here

class SomeClass:
    """Google-style docstring."""

def some_function() -> None:
    ...
```

## Import Style

- **Order**: stdlib → third-party → local, separated by blank lines
- **Explicit** `__all__` in every `__init__.py` and public module
- **Relative imports** within packages (`from .builders import ...`)
- **Lazy imports** inside functions to break circular deps (with `# noqa: PLC0415`)
- **Re-exports** through `__init__.py` aggregators

```python
from __future__ import annotations

import asyncio
import contextlib

import discord
from discord.ext import commands
from loguru import logger

from bot.cache import CacheService
from bot.core.bot import Bot  # type-aware import
from bot.core.setup.orchestrator import BotSetupOrchestrator

# Lazy import (only inside method to break cycle)
@property
def maintenance_mode(self) -> bool:
    from bot.shared.config import CONFIG  # noqa: PLC0415
    return CONFIG.MAINTENANCE_MODE
```

## Code Patterns

### Cog Pattern (every command module)

```python
"""Module docstring."""
from __future__ import annotations

import discord
from discord.ext import commands
from loguru import logger

from bot.core.base_cog import BaseCog
from bot.core.bot import Bot

__all__ = ["Ping"]


class Ping(BaseCog):
    """Short description of this cog."""

    def __init__(self, bot: Bot) -> None:
        super().__init__(bot)

    @commands.hybrid_command(name="ping", aliases=["pingpong"])
    @discord.app_commands.describe()
    async def ping(self, ctx: commands.Context[Bot]) -> None:
        """Short description shown in help."""
        if ctx.interaction:
            await ctx.defer(ephemeral=True)
        await ctx.send("Pong!")


async def setup(bot: Bot) -> None:
    """Load the Ping cog."""
    await bot.add_cog(Ping(bot))
```

### Service/Controller Pattern

```python
class SomeService:
    """Single responsibility, injected dependencies."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    async def do_thing(self, arg: str) -> Result:
        """Short description."""
        ...
```

### Error Handling

```python
# Use specific exception types
try:
    result = await risky_operation()
except BotDatabaseConnectionError as e:
    logger.error("Database unavailable: {}", e)
    raise
except BotAPIRequestError as e:
    logger.warning("API request failed: {}", e)
    return fallback_value

# Exception chaining with raise ... from
except httpx.HTTPStatusError as exc:
    raise BotAPIRequestError(
        service_name="xkcd",
        status_code=exc.response.status_code,
    ) from exc

# Broad catch-all with inline comment explaining WHY
except Exception as e:  # Catch-all: shutdown must continue
    logger.error("Unexpected error: {}", e)
```

### Guard Clauses

Use guard clauses early in functions for validation:

```python
async def do_something(self, ctx: commands.Context[Bot]) -> None:
    if not ctx.guild:
        await ctx.send("This command can only be used in a server.")
        return

    if self.bot.is_shutting_down:
        return
```

### Idempotent Operations

Use boolean flags to prevent double initialization:

```python
if self.setup_complete:
    logger.debug("Setup already complete, skipping")
    return
self.setup_complete = True
```

## Error Handling

- **Custom exception hierarchy** rooted at `BotError`
- Domain sub-exceptions in separate files under `bot/shared/exceptions/`
- Always `raise ... from exc` when re-raising to preserve chain
- Broad `except Exception` **only** at top-level boundaries (setup, shutdown, background tasks), with an inline comment explaining why
- Use `tryceratops` lint rules (enforced by ruff) for proper try/except patterns

## Logging

Uses **loguru** singleton throughout:

```python
from loguru import logger

logger.debug("Debug detail (not in production)")
logger.info("Normal operation message")
logger.success("Significant achievement (setup complete)")
logger.warning("Concerning but non-fatal")
logger.error("Handled failure")
logger.exception("Error with auto-captured traceback")
logger.critical("Unrecoverable failure")
```

- Use f-strings or `.format()` — loguru handles lazy evaluation
- Never use `print()` — ruff's `T20` rule enforces this
- Third-party loggers (discord, SQLAlchemy, etc.) are intercepted and routed through loguru with appropriate levels

## Testing

### Test File Naming

```
tests/<domain>/test_<module>.py
```

Example:
```
tests/core/test_permission_setup.py
tests/database/test_database_models.py
tests/modules/test_jail_system.py
```

### Test Function Naming

Pattern: `test_<domain>_<unit_of_work>_<expected_behavior>`

```python
def test_config_database_url_uses_explicit_database_url() -> None:
def test_config_get_prefix() -> None:
def test_config_valkey_url_builds_from_components() -> None:
```

### Test Structure

```python
"""Module docstring."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit  # or .integration, .database, etc.

def test_something() -> None:
    """Docstring describing what's being tested."""
    # Arrange
    input_value = ...
    # Act
    result = function_under_test(input_value)
    # Assert
    assert result == expected
```

### Fixtures

- Fixture plugins registered in `tests/conftest.py` via `pytest_plugins`
- Shared fixtures in `tests/fixtures/`
- Use `pyproject.toml` markers (not `conftest.py`) for all pytest markers
- PGlite (in-memory PostgreSQL) for database tests — no external DB needed
- `pytest-httpx` for HTTP mocking — network is blocked by default via `pytest-socket`

## Docstrings

**Google-style** with `Parameters`/`Returns`/`Raises` sections. Enforced by pydoclint.

```python
def function_name(param1: str, param2: int | None = None) -> bool:
    """
    Short description on one line.

    Parameters
    ----------
    param1 : str
        Description of param1.
    param2 : int | None
        Description of param2, by default None.

    Returns
    -------
    bool
        Description of return value.

    Raises
    ------
    ValueError
        When something is invalid.
    """
```

- Module-level docstrings required for all `.py` files
- Class-level docstrings with `Attributes` section
- `__init__` docstrings allowed (opt-in via config)
- Short docstrings (one line) skip extended sections
- Always use `convention = "numpy"` style (per pydoclint and ruff config)

## Tool Configuration

| Tool | Config File | Key Settings |
|------|------------|-------------|
| ruff | `pyproject.toml` | Line length 88, py313 target, numpy docstrings |
| basedpyright | `pyproject.toml` | Strict mode, Python 3.13 |
| pydoclint | `pyproject.toml` | NumPy style, require return types |
| pre-commit | `.pre-commit-config.yaml` | ruff, pydoclint, yamlfix, trailing commas |
| Coverage | `pyproject.toml` | Branch coverage, source `src/bot` |

## Do's and Don'ts

### ✅ Do

- Use `from __future__ import annotations` at the top of every file
- Use `X | None` instead of `Optional[X]`
- Add `__all__` to every public module
- Use relative imports within packages
- Use `@commands.hybrid_command()` for dual prefix + slash support
- Use Google-style docstrings with `Parameters`/`Returns`/`Raises`
- Use `self._private` convention for non-public attributes
- Use guard clauses for early returns
- Use `raise ... from exc` for exception chaining
- Write tests with `test_<domain>_<unit_of_work>_<behavior>` naming
- Add inline comments explaining broad `except` blocks

### ❌ Don't

- Don't use `print()` — use `logger.*` instead
- Don't use `Optional[X]` — use `X | None`
- Don't use bare `except:` — always catch specific exceptions
- Don't skip type hints — all functions must be annotated
- Don't use relative imports that go up multiple levels (`from ...core import`)
- Don't forget `async def setup(bot: Bot)` at the end of every cog module
- Don't add `# noqa: PLC0415` without an inline comment explaining why the lazy import is needed
- Don't import from `bot.core.bot` at module top if it causes circular imports — use lazy import
- Don't commit without running `uv run dev all` (lint + format + type-check)
