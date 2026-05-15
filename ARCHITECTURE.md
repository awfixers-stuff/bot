# Architecture

**Bot** is an all-in-one Discord bot for the AWFixer Enterprising Inc community, built with Python 3.13, discord.py, PostgreSQL, and Valkey.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.13.2+ (strict typing, `from __future__ import annotations`) |
| Discord | discord.py 2.6+ (`commands.Bot`, hybrid commands) |
| Database | PostgreSQL 17 via SQLModel (SQLAlchemy + Pydantic) + Alembic migrations |
| Cache | Valkey 9.1 (Redis-compatible) via `valkey` library |
| ORM | SQLModel 0.0.24 (extends SQLAlchemy with Pydantic validation) |
| Config | Pydantic-Settings (`.env` + `config.json`) |
| Logging | loguru |
| Telemetry | Sentry SDK (errors, traces, performance) |
| CLI | Typer |
| Testing | pytest + pytest-asyncio + pytest-cov + PGlite (in-memory PG) |
| Container | Docker + Docker Compose (profiles: dev/production) |
| Quality | ruff, basedpyright, pydoclint, pre-commit |
| Package | uv (package & project manager) |

## Directory Structure

```
bot/
├── src/bot/                     # ★ MAIN APPLICATION PACKAGE ★
│   ├── main.py                  # Entry point: instantiates BotApp().run()
│   ├── cache/                   # Valkey caching layer (backend, service, TTL, managers)
│   ├── core/                    # Framework infrastructure
│   │   ├── app.py               #   BotApp — application lifecycle & signal handling
│   │   ├── bot.py               #   Bot class (extends commands.Bot)
│   │   ├── base_cog.py          #   BaseCog — all cogs extend this
│   │   ├── cog_loader.py        #   CogLoader — dynamic cog discovery & loading
│   │   ├── context.py           #   Custom command context
│   │   ├── permission_system.py #   RBAC permission system
│   │   ├── prefix_manager.py    #   Dynamic per-guild prefix
│   │   ├── checks.py            #   Command permission check decorators
│   │   ├── decorators.py        #   Command decorators
│   │   ├── flags.py             #   Command flag parsing
│   │   ├── converters.py        #   Argument type converters
│   │   ├── logging.py           #   loguru configuration, StructuredLogger
│   │   ├── http_config.py       #   Discord HTTP client tuning
│   │   ├── task_monitor.py      #   Background task health
│   │   ├── types.py             #   Custom type definitions
│   │   └── setup/               #   Startup orchestration phases
│   │       ├── orchestrator.py  #     BotSetupOrchestrator — runs all phases
│   │       ├── base.py          #     BaseSetupService abstract class
│   │       ├── database_setup.py
│   │       ├── cache_setup.py
│   │       ├── permission_setup.py
│   │       ├── prefix_setup.py
│   │       └── cog_setup.py
│   ├── database/                # ★ DATA LAYER ★
│   │   ├── service.py           #   DatabaseService singleton
│   │   ├── models/              #   SQLModel ORM definitions
│   │   │   ├── base.py          #     Base SQLModel settings
│   │   │   ├── enums.py         #     CaseType, etc.
│   │   │   └── models.py        #     All domain models (Case, GuildConfig, etc.)
│   │   ├── controllers/         #   Data access layer
│   │   │   ├── base/            #     Generic CRUD (BaseController, bulk, filters, etc.)
│   │   │   └── (domain)         #     afk.py, case.py, permissions.py, etc.
│   │   └── migrations/          #   Alembic migrations
│   ├── modules/                 # ★ COMMAND MODULES (Cogs) ★
│   │   ├── admin/               #   Bot admin/owner (dev, eval)
│   │   ├── config/              #   Per-guild configuration
│   │   ├── features/            #   Optional toggles (starboard, levels, temp VC)
│   │   ├── fun/                 #   Fun commands (xkcd, random)
│   │   ├── guild/               #   Guild-specific (member count)
│   │   ├── info/                #   Server/channel/user info
│   │   ├── levels/              #   XP/levelling system
│   │   ├── moderation/          #   18 moderation commands
│   │   ├── snippets/            #   Saved message snippets
│   │   ├── tools/               #   TLDR, Wolfram Alpha
│   │   └── utility/             #   ping, poll, AFK, remindme, etc.
│   ├── plugins/                 #   External plugins
│   │   ├── atl/                 #   "Atlanta" plugin suite
│   │   └── v0_1_db_migrate/     #   Database migration from v0.1
│   ├── services/                # ★ SERVICE LAYER (business logic) ★
│   │   ├── handlers/            #   Discord event handlers
│   │   │   └── error/           #     Error handling pipeline (extractors, formatter)
│   │   ├── hot_reload/          #   Hot-reload system (watchdog-based)
│   │   ├── moderation/          #   Moderation business logic
│   │   ├── sentry/              #   Sentry error tracking & tracing
│   │   └── wrappers/            #   External API wrappers (GitHub, xkcd, Godbolt, etc.)
│   ├── shared/                  #   Cross-cutting code
│   │   ├── config/              #   Pydantic config models & settings
│   │   ├── exceptions/          #   Custom exception hierarchy (BotError → domain)
│   │   ├── constants.py         #   EMBED_COLORS, COG_PRIORITIES, etc.
│   │   └── version.py           #   Version management
│   └── ui/                      #   Discord UI components
│       ├── embeds.py            #   EmbedCreator
│       ├── buttons.py           #   UI button components
│       ├── banner.py            #   Startup banner
│       └── views/               #   Interactive views (config dashboard, etc.)
├── scripts/                     # CLI tooling (Typer-based)
│   ├── bot/start.py             #   `bot start` command
│   ├── db/                      #   `db *` commands (init, dev, push, etc.)
│   ├── dev/                     #   `dev *` commands (lint, format, type-check, etc.)
│   ├── test/                    #   `test *` commands (quick, all, benchmark, etc.)
│   ├── core.py                  #   CLI factory (create_app)
│   └── ui.py                    #   CLI output helpers
├── tests/                       # ★ TEST SUITE ★ (mirrors src structure)
│   ├── conftest.py              #   Pytest config + mock factories
│   ├── fixtures/                #   Database, Sentry mock fixtures
│   ├── cache/                   #   Cache layer tests
│   ├── core/                    #   Permission, prefix, logging tests
│   ├── database/                #   Model, controller, migration tests
│   ├── modules/                 #   Cog tests (info, jail, moderation, etc.)
│   ├── services/                #   Error handler, Sentry, HTTP tests
│   ├── shared/                  #   Config, version tests
│   ├── performance/             #   Benchmark tests
│   └── e2e/                     #   End-to-end tests
├── docker/                      # Docker infrastructure
│   ├── entrypoint.sh
│   └── postgres/postgresql.conf
├── docs/                        # MkDocs/Mintlify documentation
├── compose.yaml                 # Docker Compose (dev/production profiles)
├── Containerfile                # Docker build
├── pyproject.toml               # Project config & deps
├── uv.lock                      # Lockfile
├── alembic.ini                  # Alembic config
└── .pre-commit-config.yaml      # Pre-commit hooks
```

## Core Components

### Application Lifecycle (`src/bot/core/app.py`)

`BotApp` manages the bot's lifecycle:

```
uv run bot start
  └─ scripts/bot/start.py::start()
       └─ configure_logging()
       └─ BotApp().run()
            └─ asyncio.run(BotApp.start())
                 ├─ configure_logging()           ← Fallback
                 ├─ SentryManager.setup()
                 ├─ _setup_signals()              ← SIGTERM/SIGINT
                 ├─ _create_bot_instance()
                 ├─ bot.login(CONFIG.BOT_TOKEN)
                 │    └─ discord.py calls setup_hook()
                 │         └─ BotSetupOrchestrator.setup()
                 │              ├─ DatabaseSetupService
                 │              ├─ CacheSetupService
                 │              ├─ PermissionSetupService
                 │              ├─ PrefixSetupService
                 │              └─ CogSetupService
                 │                   ├─ load_extension("jishaku")
                 │                   ├─ CogLoader.setup() → all cogs
                 │                   └─ hot_reload
                 ├─ bot.connect(reconnect=True)   ← Blocks until disconnect
                 └─ finally: Bot.shutdown()
                      ├─ Cancel startup task
                      ├─ Cleanup background tasks
                      └─ Close connections (Discord → DB → Cache → HTTP)
```

### Bot Class (`src/bot/core/bot.py`)

Central orchestrator extending `commands.Bot`. Key responsibilities:
- **Lifecycle state**: `is_shutting_down`, `setup_complete`, `start_time`
- **Service references**: `db_service`, `cache_service`, `prefix_manager`, `sentry_manager`
- **Post-ready startup**: banner display, Sentry command instrumentation, stats recording
- **Graceful shutdown**: three-phase cleanup with Sentry tracing
- **Maintenance mode**: global check blocking non-owner commands

### Cog System

All cogs extend `BaseCog` (`src/bot/core/base_cog.py`), which provides:
- `send_after_defer()` — defer-then-send pattern for slash commands
- `unload_if_missing_config()` — graceful self-unload when feature not configured
- Error handling wrappers

Cog loading (via `CogLoader` in `src/bot/core/cog_loader.py`):
- Priority-based ordering via `COG_PRIORITIES` constant
- Filesystem scanning for cog discovery
- Sentry telemetry per cog load

Each cog module follows this pattern:
```python
class Ping(BaseCog):
    @commands.hybrid_command(name="ping")
    async def ping(self, ctx: commands.Context[Bot]) -> None:
        ...

async def setup(bot: Bot) -> None:
    await bot.add_cog(Ping(bot))
```

### Permission System (`src/bot/core/permission_system.py`)

RBAC with:
- `DEFAULT_RANKS`: Owner, Admin, Mod, Member, Jail, Bypass
- `requires_command_permission` decorator
- Permission bypass system for override cases
- In-memory cache with database persistence

### Configuration (`src/bot/shared/config/`)

Two-tier config loading:
1. **`.env` file** → environment variables (via `pydantic-settings`)
2. **`config.json`** → JSON file in `config/` directory

Config model hierarchy:
- `Config` — root model with all settings
- `BotInfo`, `BotIntents`, `UserIdConfig`, `DatabaseConfig`, etc.
- `CONFIG` singleton imported via `from bot.shared.config import CONFIG`

### Data Layer (`src/bot/database/`)

Controller pattern over SQLModel:
- `DatabaseService` — async engine lifecycle, connection pooling
- **Models**: SQLModel ORM definitions in `models/models.py`
- **Controllers**: Domain-specific data access in `controllers/` (case, permissions, afk, etc.)
- **Base controllers**: Generic CRUD with bulk, upsert, filters, transactions in `controllers/base/`
- **Migrations**: Alembic-managed versioned migrations

### Cache Layer (`src/bot/cache/`)

Valkey-based caching:
- `CacheService` — high-level API (get, set, delete, invalidate patterns)
- `backend.py` — Valkey connection pooling
- `TTLManager` — time-to-live management
- Used for: prefix cache, permission cache, session data

### Error Handling Pipeline (`src/bot/services/handlers/error/`)

Structured error handling for Discord commands:
- **extractors.py** — domain-specific error extractors (HTTP, permissions, arguments, etc.)
- **formatter.py** — user-facing error message formatting
- **suggestions.py** — smart error suggestions
- **config.py** — error handling configuration

### Hot Reload System (`src/bot/services/hot_reload/`)

Watchdog-based file watcher that automatically reloads cogs on change. Tracks dependencies between modules for cascade reloading.

## Data Flow

### Command Execution Flow

```
Discord Message
  → Bot.get_prefix()           ← Resolves guild prefix (cached)
  → Bot._maintenance_mode_check ← Global guard
  → Command check decorators   ← Permission checks
  → setup_hook()               ← Cog-level pre-execution
  → Command function           ← Business logic
       → Controller layer       ← Database queries
       → API wrappers            ← External calls (xkcd, GitHub, etc.)
       → UI components           ← Embed/button building
  → Response to Discord
```

### Database Session Flow

```
Command
  → DatabaseCoordinator        ← Routes to domain controller
  → Controller (e.g., CaseController)
       → BaseController         ← CRUD operations
            → SQLModel Session (async)
                 → PostgreSQL
  → Result returned
```

### Error Handling Flow

```
Exception in command
  → ErrorCog (cog.py)
       → ErrorHandler
            → ErrorExtractors    ← Identify error type
            → ErrorFormatter     ← Create user-friendly message
            → Suggestions        ← Offer solutions
            → Sentry capture     ← Report to Sentry
  → User gets error embed
```

## External Integrations

| Service | Wrapper | Purpose |
|---------|---------|---------|
| GitHub | `services/wrappers/github.py` | Integration with GitHub API |
| xkcd | `services/wrappers/xkcd.py` | Comic fetching |
| Godbolt | `services/wrappers/godbolt.py` | Compiler Explorer API |
| Wandbox | `services/wrappers/wandbox.py` | Online compiler API |
| TLDR | `services/wrappers/tldr.py` | TLDR pages lookup |
| Wolfram Alpha | `modules/tools/wolfram.py` | Computational knowledge |
| Sentry | `services/sentry/` | Error tracking & APM |
| Jishaku | `cog_setup.py` | Debug/development commands |

## Configuration

| File | Purpose |
|------|---------|
| `.env` | Environment variables (secrets, tokens, DB URLs) |
| `config/config.json` | JSON settings (colors, ranks, API keys) |
| `pyproject.toml` | Python dependencies, tool configs |
| `compose.yaml` | Docker services (profiles: dev/production) |
| `alembic.ini` | Database migration config |

## Database Migrations

Managed via Alembic with custom CLI commands (`uv run db *`):
```
uv run db init        # Create database
uv run db dev         # Auto-generate migration from model changes
uv run db push        # Apply pending migrations
uv run db new         # Create empty migration
uv run db rollback    # Revert last migration
```

## Deployment

Two Docker Compose profiles:
- **`dev`**: Build from source, hot-reload via file sync, no security hardening
- **`production`**: Pre-built image, read-only filesystem, no-new-privileges

```bash
# Development
docker compose --profile dev up -d
docker compose --profile dev up --watch   # Hot reload

# Production
docker compose --profile production up -d
```

Container entrypoint (`docker/entrypoint.sh`) handles:
- Database readiness wait loop
- Config validation
- Retry logic (3 attempts, 5s delay)
- Cache directory permission setup

## Testing

```bash
uv run test quick       # Fast subset (unit tests)
uv run test all         # Full suite
uv run test coverage    # With coverage report
uv run test benchmark   # Performance benchmarks
```

Testing stack: pytest + pytest-asyncio + PGlite (in-memory PostgreSQL) + pytest-httpx (HTTP mocking) + pytest-socket (network isolation).
