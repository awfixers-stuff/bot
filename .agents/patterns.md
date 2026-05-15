# Code Standards, Architecture Notes, and Domain Patterns

## Tech Stack

**Core:** Python 3.13.2+ • discord.py • PostgreSQL 17+ • SQLModel • Docker

**Tools:** uv • ruff • basedpyright • pytest • loguru • sentry-sdk • httpx • Zensical

**Database:** SQLModel (ORM) • Alembic (migrations) • psycopg (async driver) • py-pglite (test DB)

**Cache:** CacheService with InMemoryBackend or optional ValkeyBackend (when `VALKEY_URL` set).

---

## 1. Python Style Guide

### Naming
| Type | Convention | Example |
|------|------------|---------|
| Functions/vars | `snake_case` | `get_user()`, `user_id` |
| Classes | `PascalCase` | `UserProfile`, `ValidationError` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_RETRIES` |
| Protected | `_single_underscore` | `_internal_helper()` |

### Type Hints (Python 3.13+)
- ✅ `Type | None` (not `Optional[Type]`)
- ✅ `list[str]`, `dict[str, int]` (not `List[str]`, `Dict[str, int]`)
- ✅ Always include param/return type hints

### Comparisons
- ✅ `if attr:` / `if not attr:` for truthiness
- ✅ `if attr is None:` / `if attr is not None:`
- ❌ `if attr == True:` / `if attr == False:`

### Docstrings — NumPy Style
```python
def process_data(data: dict[str, Any], validate: bool = True) -> dict[str, Any]:
    """Process data with optional validation.

    Parameters
    ----
    data : dict[str, Any]
        Data to process.
    validate : bool, optional
        Whether to validate, by default True.

    Returns
    ----
    dict[str, Any]
        Processed data.
    """
```

- Use action words: "Return", "Process" (not "Returns", "Processes")
- Document `__init__` in the class docstring

### Imports
Three groups with blank lines between, each alphabetical:
1. stdlib
2. third-party
3. local

### Best Practices
- ✅ List/set/dict comprehensions over loops with append
- ✅ Generator expressions when just iterating (saves memory)
- ✅ `with` statements for file/async operations
- ✅ Parentheses for line continuations (no backslashes)
- ✅ `str.join()` over string concatenation in loops
- ✅ `.get()` with defaults for dict access
- ✅ Use sets for frequent O(1) lookups
- ✅ `enumerate()` instead of `range(len())`
- ❌ One-letter vars (except short loops)
- ❌ Modifying list while iterating
- ❌ Lambda assignment (use `def`)
- ❌ Bare `except:` (use `except Exception:`)

### Async Python
- `async def` / `await` for all I/O
- `asyncio.gather(*tasks, return_exceptions=True)` for concurrency
- `asyncio.wait_for(coro, timeout=)` for timeouts
- `asyncio.Semaphore` for rate limiting
- `async with` for context managers
- `asyncio.create_task()` for background work (store the reference)
- ❌ `time.sleep()` in async code (use `asyncio.sleep()`)
- ❌ Blocking calls without executor

---

## 2. Database Patterns

### Models — SQLModel
Most models inherit from `BaseModel` (provides `created_at` / `updated_at`). Utility models without timestamps inherit from `SQLModel` directly.

```python
from tux.database.models import BaseModel

class MyModel(BaseModel, table=True):
    """Model description."""

    id: int = Field(primary_key=True, sa_type=BigInteger, description="Discord ID")
    name: str = Field(max_length=255)
    opt: str | None = Field(default=None, nullable=True)
```

**IDs:** `BigInteger` for Discord snowflakes, `UUIDMixin` for internal UUIDs.
**Relationships:** Use `Relationship(sa_relationship=relationship(...))` with `back_populates`, `cascade`, `passive_deletes`, and `lazy="selectin"`.
**Constraints:** `ge`, `le`, `max_length`, CheckConstraint, UniqueConstraint.
**Indexes:** Index frequently queried columns, use partial indexes for filtered queries.
**Serialization:** Use `.to_dict()` from BaseModel (auto-serializes enums, datetimes, UUIDs).
**Mixins:** `UUIDMixin` (UUID PK), `SoftDeleteMixin` (`.soft_delete()` / `.restore()`).

### Controllers — CRUD
Controllers provide async CRUD operations with type safety. One controller per model.

```python
class MyModelController:
    async def get_by_id(self, id: int) -> MyModel | None: ...
    async def get_all(self) -> list[MyModel]: ...
    async def create(self, **data) -> MyModel: ...
    async def update(self, id: int, **data) -> MyModel | None: ...
    async def delete(self, id: int) -> bool: ...
```

- Single `get_*` methods return `Model | None`
- Batch `get_*` methods return `list[Model]`
- Use `select()` from SQLModel, execute via session
- Controllers are stateless — session injected per call

### DatabaseService
Central service exposing all controllers as properties: `db.guild`, `db.guild_config`, `db.case`, etc. Single instance created at startup, shared via dependency injection.

### Migrations — Alembic
- `uv run db new "description"` for creating migration files
- `uv run db dev` to auto-create + apply
- Migration safety: check for data loss, test with py-pglite, avoid `drop column` without verification

---

## 3. Module / Cog Patterns

### Cog Structure
All cogs inherit from `BaseCog` (provides `self.db`, `self.get_config()`, auto-usage generation).

```python
from discord.ext import commands
from tux.core.base_cog import BaseCog
from tux.core.bot import Tux

class MyCog(BaseCog):
    """Description."""

    def __init__(self, bot: Tux) -> None:
        super().__init__(bot)

    async def cog_load(self) -> None: ...   # Setup
    async def cog_unload(self) -> None: ... # Cleanup

async def setup(bot: Tux) -> None:
    await bot.add_cog(MyCog(bot))
```

- **Specialized bases:** `ModerationCogBase` (provides `self.moderation`), `SnippetsBaseCog` (provides snippet utilities)
- **Config check:** `if self.unload_if_missing_config(condition=not CONFIG.X, config_name="X"): return`

### Commands
Use hybrid commands (`@commands.hybrid_command()`) for both slash + prefix support.

```python
@commands.hybrid_command(name="mycommand")
async def my_command(self, ctx: commands.Context[Tux], member: discord.Member, reason: str | None = None) -> None:
    ...
```

- Permissions via `@requires_command_permission()` decorator
- Cooldowns via `@commands.cooldown(rate=1, per=5, type=...)`
- Rate limiting with `@commands.max_concurrency(number=1, per=...)`

### Events
Event listeners use `@commands.Cog.listener()`.

```python
@commands.Cog.listener()
async def on_message(self, message: discord.Message) -> None: ...
```

### Permissions
Role-based permission system with hierarchical ranks. Use `@requires_command_permission()` — checks automatically handled. For custom checks, use `self.db.permission_rank` controller.

### Interactions
- Defer slow operations: `await ctx.defer()` or `await interaction.response.defer()`
- Edit original response for progressive updates
- Ephemeral responses for user-specific feedback

---

## 4. Testing Patterns

### Test Structure
```
tests/
├── conftest.py           # Config + fixtures
├── fixtures/             # Shared fixtures
├── unit/                 # Fast, isolated tests
├── integration/          # Database + service tests
└── e2e/                  # Full workflow tests
```

### Test Patterns
```python
import pytest

@pytest.mark.unit
async def test_my_function(db_service: DatabaseService) -> None:
    """Test description."""
    # Arrange
    # Act
    # Assert
    assert result == expected
```

- **Markers:** `unit`, `integration`, `slow`, `database`, `async` (defined in `pyproject.toml`)
- **Async tests:** Use `@pytest.mark.asyncio` + `@pytest.mark.unit`
- **Descriptive names:** `test_user_has_correct_age_in_dog_years`
- **Isolated:** Tests should not depend on each other
- **py-pglite:** In-memory PostgreSQL for database tests
- **Factories:** Prefer over fixtures for test data
- **Coverage:** Use `uv run test all` (terminal, XML, JSON, LCOV, HTML)

### Fixtures
- Defined in `conftest.py` or `tests/fixtures/`
- Use `yield` for teardown
- Type-annotate fixture return values

---

## 5. Security Patterns

- **Validate all inputs** — never trust user input (limit lengths, check types)
- **Parameterized queries** — SQLModel handles this automatically
- **Environment variables** for secrets — never hard-code tokens/passwords
- **Sanitize sensitive data** before logging (`_sanitize_sensitive_data()`)
- **Permission checks** — always use `@requires_command_permission()`
- **Validate interaction authors** — use `validate_author()` for UI callbacks
- **Generic error messages** for users — log details internally, show generic externally
- **Non-root user** in Docker (UID 1001)
- **Read-only filesystem** in production containers
- **`no-new-privileges`** in production Docker

### Common Anti-Patterns
- ❌ Logging sensitive data (passwords, tokens, DB URLs)
- ❌ Exposing internal error details to users
- ❌ Missing permission checks
- ❌ SQL injection via string concatenation

---

## 6. Error Handling & Logging

### Exception Hierarchy
Custom exceptions in `tux.shared.exceptions`:
```
TuxError
├── TuxDatabaseError / TuxDatabaseConnectionError / TuxDatabaseQueryError
├── TuxPermissionError / TuxPermissionDeniedError / TuxPermissionLevelError
├── TuxAPIError / TuxAPIConnectionError / TuxAPIRequestError
├── TuxServiceError / TuxCogLoadError / TuxHotReloadError
├── TuxConfigurationError / TuxRuntimeError / TuxSetupError
```

### Error Handling Patterns
- ✅ `except Exception:` (never bare `except:` — it catches `KeyboardInterrupt`)
- ✅ `raise NewError from e` to chain and preserve traceback
- ✅ `contextlib.suppress()` for intentional exception suppression
- ✅ `logger.exception()` in except blocks (includes traceback)
- ✅ Local error handlers for command-specific errors, re-raise for global handler
- Global `ErrorHandler` cog catches unhandled errors → formats embeds → logs → Sentry

### Logging — loguru
```python
from loguru import logger

logger.info("message")
logger.error("message")
logger.exception("Operation failed")  # Includes traceback
logger.bind(guild_id=guild_id).info("Processing")  # Structured context
```

- **Levels:** TRACE → DEBUG → INFO → SUCCESS → WARNING → ERROR → CRITICAL
- **StructuredLogger** for performance, database, and API metrics
- Auto-configured at startup — just import and use
- Third-party logs auto-intercepted through loguru
- ❌ `print()` — always use logger
- ❌ `logging` module — use loguru

---

## 7. UI Components V2 (discord.py 2.6+)

### LayoutView (V2) vs View (Legacy)
**LayoutView** — Components V2. Define items as class variables (no `add_item`). Max 40 components total.
**View** — Legacy. Max 25 top-level, 5 ActionRows. Still supported.

```python
class MyLayout(ui.LayoutView):
    text = ui.TextDisplay("Hello", id=100)
    row = ui.ActionRow()

    @row.button(label="Click")
    async def btn(self, i: discord.Interaction, btn: ui.Button):
        await i.response.send_message("Hi!")
```

### Key Components
| Component | Purpose | Constraints |
|-----------|---------|-------------|
| TextDisplay | Markdown text (pings work anywhere) | 4000 chars total across all |
| ActionRow | Buttons/selects container | 5 buttons OR 1 select |
| Button | Interactive button | 34-38 chars label, 5 styles |
| StringSelect | Custom dropdown | 25 options max |
| Section | Label + accessory (Button/Thumbnail) | 1-3 TextDisplay, 1 accessory |
| Container | Embed-like box with accent color | No fields/author/footer |
| Separator | Visual divider | Top-level only |
| MediaGallery | 1-10 images/videos | URLs or local files |

### Modal Usage
```python
class MyModal(ui.Modal, title="Form"):
    header = ui.TextDisplay("# Title")
    field = ui.Label(text="Name", component=ui.TextInput(custom_id="name"))

    async def on_submit(self, i: discord.Interaction):
        value = self.field.component.value
        await i.response.send_message(f"Value: {value}")
```

- Max 5 top-level components in modal
- TextDisplay works in modals
- Label wraps TextInput/Selects/FileUpload

### Best Practices
- ✅ Use LayoutView for new components
- ✅ Store component refs as instance vars for dynamic updates
- ✅ Use `find_item(id)` for nested access
- ❌ Mixing V1 and V2 in same view
- ❌ Manual `add_item` — use class variables
- ❌ Missing ActionRow for buttons/selects

---

## 8. Cache System

**Service:** `tux.cache.CacheService` — async Valkey client lifecycle (connect/ping/close).
**Backends:** `get_cache_backend(bot)` returns ValkeyBackend when `VALKEY_URL` is set and reachable, else shared InMemoryBackend.
**Key format:** `tux:{model}:{id}` — JSON values.
**Managers:** GuildConfigCacheManager, JailStatusCache, prefix/permission caches — auto-switch between in-memory and Valkey.
**Config:** Set `VALKEY_URL=valkey://host:port/db` in `.env` to enable Valkey; leave unset for in-memory only.

---

## 9. Documentation Patterns

**Tool:** Zensical documentation platform. Content in `docs/content/`.
**Structure:**
- `user/` — User guides
- `admin/` — Admin features
- `selfhost/` — Self-hosting
- `developer/` — Development guides + concepts
- `reference/` — Technical specs
- `community/` — General info

**Diátaxis Framework:**
- **Tutorials** — step-by-step learning
- **How-to guides** — solve specific problems
- **Reference** — technical specifications
- **Explanation** — understanding concepts

**Standards:** Active voice, second person, practical examples, NumPy-style docstrings for API docs.
**Validation:** `uv run docs lint`, `uv run docs build` to verify.
