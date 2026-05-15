# Architecture

**Bot** is a feature-rich Discord bot for the [AWFixer Enterprising Inc](https://github.com/awfixers-stuff/bot) community. It provides moderation, leveling, snippets, reminders, AFK tracking, starboard, custom permissions, and more.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.13.2+ (3.13.11 pinned) |
| Discord | discord.py 2.6+ |
| Database | PostgreSQL 17 + SQLModel + SQLAlchemy 2.0 async |
| Migrations | Alembic |
| Cache | Valkey 9.x (Redis-compatible), optional |
| Config | Pydantic Settings (.env + config.json) |
| CLI | Typer |
| Logging | Loguru |
| Error Tracking | Sentry SDK |
| HTTP | httpx |
| Container | Docker (multi-stage), Docker Compose |
| CI | GitHub Actions |

## Directory Structure

```
bot/
├── pyproject.toml             # Project metadata, deps, tool config
├── uv.lock                    # Locked dependency versions
├── Containerfile              # Multi-stage Docker build
├── compose.yaml               # Docker Compose (dev + production)
├── .env.example               # Environment variable template
├── alembic.ini                # Alembic migration config
├── mise.toml                  # Python version pinning
│
├── src/
│   └── bot/
│       ├── main.py            # Entry point: calls BotApp
│       ├── core/              # Framework core
│       │   ├── app.py         # BotApp lifecycle (signals, startup, shutdown)
│       │   ├── bot.py         # Bot class (extends commands.Bot)
│       │   ├── base_cog.py    # BaseCog (foundation for all cogs)
│       │   ├── cog_loader.py  # Priority-based dynamic cog loader
│       │   ├── logging.py     # Loguru configuration
│       │   ├── permission_system.py  # DB-driven permission hierarchy
│       │   ├── prefix_manager.py     # Per-guild prefix support
│       │   ├── decorators.py  # @requires_command_permission
│       │   ├── converters.py  # Discord argument converters
│       │   ├── context.py     # Custom command context
│       │   ├── task_monitor.py # Background task management
│       │   ├── checks.py      # Global command checks
│       │   ├── flags.py       # Flag converters
│       │   ├── types.py       # Custom type annotations
│       │   ├── http_config.py # Discord HTTP client tuning
│       │   └── setup/         # Orchestrated startup
│       │       ├── orchestrator.py
│       │       ├── database_setup.py
│       │       ├── cog_setup.py
│       │       ├── cache_setup.py
│       │       ├── permission_setup.py
│       │       ├── prefix_setup.py
│       │       └── base.py
│       │
│       ├── database/
│       │   ├── service.py     # DatabaseService (connection pool, sessions)
│       │   ├── models/        # SQLModel table definitions
│       │   │   ├── base.py    # BaseModel, SoftDeleteMixin, UUIDMixin
│       │   │   ├── models.py  # All table models (807 lines)
│       │   │   └── enums.py   # CaseType, PermissionType
│       │   ├── controllers/   # CRUD operations per domain
│       │   │   ├── base/      # BaseController, CRUD mixins, bulk, upsert, query, filters, transaction
│       │   │   ├── case.py, afk.py, levels.py, snippet.py
│       │   │   ├── reminder.py, starboard.py
│       │   │   ├── permissions.py  # Permission*Controller
│       │   │   └── __init__.py     # DatabaseCoordinator (facade)
│       │   ├── migrations/    # Alembic migration files
│       │   ├── utils.py       # Query helpers
│       │   └── gather_results.py
│       │
│       ├── cache/
│       │   ├── service.py     # CacheService (Valkey or in-memory)
│       │   ├── backend.py     # Cache backend protocol + implementations
│       │   ├── managers.py    # Domain-specific cache managers
│       │   └── ttl.py         # TTL constants
│       │
│       ├── modules/           # Discord command cogs (features)
│       │   ├── admin/         # Admin/owner commands
│       │   ├── config/        # Guild configuration dashboard
│       │   ├── features/      # Misc features
│       │   ├── fun/           # Fun commands
│       │   ├── guild/         # Guild info/management
│       │   ├── info/          # Information commands
│       │   ├── levels/        # XP/leveling system
│       │   ├── moderation/    # Ban, kick, warn, jail, timeout, purge, etc.
│       │   ├── snippets/      # Custom snippet/command system
│       │   ├── tools/         # Utility tools
│       │   └── utility/       # General utility commands
│       │
│       ├── services/
│       │   ├── handlers/      # Event handlers (activity, error, event)
│       │   ├── sentry/        # Sentry integration (tracing, metrics, config)
│       │   ├── hot_reload/    # Hot reload service
│       │   ├── moderation/    # Moderation service logic
│       │   ├── wrappers/      # Service wrappers
│       │   ├── emoji_manager.py
│       │   └── http_client.py
│       │
│       ├── shared/
│       │   ├── config/        # Pydantic Settings models
│       │   │   ├── settings.py    # Config class, CONFIG singleton
│       │   │   └── models.py      # Sub-config models (BotInfo, UserIds, etc.)
│       │   ├── exceptions/    # Custom exception hierarchy
│       │   ├── constants.py   # Embed colors, icons, limits, priorities
│       │   ├── functions.py   # Shared utility functions
│       │   ├── regex.py       # Regex patterns
│       │   └── version.py     # Version management
│       │
│       ├── ui/                # Discord UI components
│       │   ├── embeds.py      # Embed builders
│       │   ├── buttons.py     # Button presets
│       │   ├── banner.py      # Startup ASCII art banner
│       │   ├── views/         # Discord UI Views (config dashboard, TLDR, confirmation)
│       │   └── modals/        # Discord UI Modals (report, etc.)
│       │
│       └── help/              # Custom help command system
│           ├── help.py, components.py, data.py
│           ├── navigation.py, renderer.py, utils.py
│
├── scripts/                   # CLI commands (uv run <cmd>)
│   ├── core.py                # Typer app factory
│   ├── bot/start.py           # uv run bot start
│   ├── db/                    # uv run db * (init, dev, push, etc.)
│   ├── dev/                   # uv run dev * (lint, format, typecheck, etc.)
│   ├── test/                  # uv run test * (quick, all, parallel, etc.)
│   ├── config/                # uv run config * (generate, validate)
│   ├── docs/                  # uv run docs * (build, serve, lint)
│   └── ai/                    # uv run ai validate-rules
│
├── tests/
│   ├── conftest.py            # Global pytest config
│   ├── fixtures/              # Shared test fixtures
│   ├── core/                  # Core system tests
│   ├── database/              # Database model & controller tests
│   ├── modules/               # Cog/feature tests
│   ├── services/              # Service layer tests
│   ├── cache/                 # Cache tests
│   ├── shared/                # Config & version tests
│   ├── plugins/               # Plugin tests
│   ├── performance/           # Performance benchmarks
│   ├── help/                  # Help system tests
│   └── e2e/                   # End-to-end tests
│
├── docs/                      # MkDocs documentation
├── .cursor/                   # Cursor IDE rules & commands
├── .agents/                   # Agent documentation
├── .github/workflows/         # CI/CD pipelines
├── docker/                    # Docker entrypoint, postgres config
├── assets/                    # Images, emojis, branding
└── typings/                   # Type stubs
```

## Core Components

### 1. Application Lifecycle (`src/bot/core/app.py`)

`BotApp` orchestrates the entire bot lifecycle:
1. **Logging config** (Loguru) — first thing
2. **Sentry initialization** — telemetry
3. **Signal handlers** — SIGTERM/SIGINT for graceful shutdown
4. **Bot creation** — `Bot` instance with intents from config
5. **Login & connect** to Discord gateway
6. **Shutdown** — cleanup DB, cache, HTTP, flush Sentry

### 2. Bot Class (`src/bot/core/bot.py`)

Extends `discord.ext.commands.Bot` with:
- **`setup_hook()`** — database connection, cog loading, cache init
- **Maintenance mode** — blocks non-owner commands
- **Graceful shutdown** — 3-phase: cancel startup, cleanup tasks, close connections
- **Managed services**: `DatabaseService`, `CacheService`, `PrefixManager`, `TaskMonitor`, `EmojiManager`
- **Sentry tracing** — commands instrumented after setup

### 3. Cog Loading System (`src/bot/core/cog_loader.py`)

Priority-based, concurrent cog loading:
1. **Services/Handlers** (priority 90) — loaded first
2. **Modules** (priority varies: config=85, admin=80, levels=70, moderation=60, snippets=50, guild=40, utility=30, info=20, fun=10, tools=5)
3. **Plugins** (priority 1) — loaded last

Cogs within the same priority group are loaded concurrently via `asyncio.gather`. Uses AST pre-validation to skip non-cog files.

### 4. Database Layer

**Service** (`database/service.py`):
- Async PostgreSQL via SQLAlchemy 2.0 + psycopg
- Connection pooling with retry logic
- Automatic reconnection

**Models** (`database/models/models.py`):
- SQLModel (SQLAlchemy + Pydantic) table models
- Key models: `Case`, `AFK`, `Levels`, `Reminder`, `Snippet`, `Starboard`, `PermissionRank`, `PermissionAssignment`, `PermissionCommand`
- Mixins: `SoftDeleteMixin`, `UUIDMixin`

**Controllers** (`database/controllers/`):
- Domain-specific CRUD per model
- `DatabaseCoordinator` — lazy-loaded facade over all controllers
- Base controller with reusable CRUD, bulk, upsert, query, filter, transaction mixins

**Migrations**: Alembic with custom CLI (`uv run db push`, `uv run db dev`, etc.)

### 5. Permission System (`src/bot/core/permission_system.py`)

Database-driven, guild-specific permission hierarchy:
- **Ranks 0-10** (default: 0=Member, 7=Server Owner)
- **Role-to-rank assignments** — multiple roles per rank
- **Command permissions** — override per-command required rank, with parent fallback
- **Caching** — Valkey/in-memory backend with 2-hour TTL for command fallback

Access control via `@requires_command_permission()` decorator (no arguments — config in DB). Commands denied by default (safe mode).

### 6. UI Layer (`src/bot/ui/`)

- `embeds.py` — standardized embed builders with consistent colors/icons
- `buttons.py` — reusable button components
- `views/` — complex views (config dashboard with pagination, TLDR, confirmation)
- `modals/` — modal dialogs (report, etc.)

### 7. Help System (`src/bot/help/`)

Custom help command with:
- Permission-filtered command listing
- Category-based navigation
- Rich embed rendering

### 8. Caching (`src/bot/cache/`)

- **Valkey** (preferred) or in-memory fallback
- Domain-specific cache managers
- TTL-based expiration

## Data Flow

```
Discord Gateway
     ↓
Bot.on_message / on_interaction
     ↓
commands.Bot (prefix + slash commands)
     ↓
Cog dispatch → @requires_command_permission check
     │                ↓
     │         PermissionSystem.get_command_permission()
     │                ↓
     │         DB query (cached) → allow/deny
     ↓
Command execution → Controller → DatabaseService → PostgreSQL
                                        ↓
                                  CacheService → Valkey (optional)
     ↓
Response → Discord API (embeds, views, modals)
```

## External Integrations

| Integration | Purpose |
|-------------|---------|
| Sentry | Error tracking, performance monitoring, tracing |
| GitHub API (githubkit) | GitHub app auth, repo interaction |
| Mailcow API | Email management |
| Wolfram Alpha | Computation queries |
| Godbolt/Compiler Explorer | Code compilation |
| Wandbox | Code execution |
| Wikipedia/Arch Wiki | Info lookups |

## Configuration

**Sources** (priority order):
1. Programmatic overrides
2. Environment variables
3. `.env` file (BOT_TOKEN, DB, Valkey, external services)
4. `config/config.json` or `config.json` (bot info, intents, features, ranks)
5. Docker secrets (`/run/secrets`)

**Key env vars**: `BOT_TOKEN`, `POSTGRES_*`, `VALKEY_*`, `DEBUG`, `LOG_LEVEL`, `MAINTENANCE_MODE`, `EXTERNAL_SERVICES__*`

## Build & Deploy

```bash
# Install dependencies
uv sync

# Development database
docker compose --profile dev up -d    # Start Postgres
uv run db init                         # Create tables
uv run db dev                          # Auto-migrate on model changes

# Run the bot
uv run bot start

# Quality checks
uv run dev all                         # lint + format + typecheck + docs

# Tests
uv run test quick                      # Fast unit tests
uv run test all                        # Full test suite

# Docker production
docker compose --profile production up -d
```

## Test Architecture

- **pytest** with `--import-mode=importlib`, `--asyncio-mode=auto`
- **py-pglite** for in-memory PostgreSQL in unit tests
- **pytest-socket** blocks network access (allow Unix sockets for PGlite)
- **pytest-httpx** for HTTP mocking
- **pytest-alembic** for migration testing
- Test markers: `unit`, `integration`, `e2e`, `database`, `slow`, `core`, `services`, `modules`, `performance`
- Fixtures in `tests/fixtures/` (database, data, sentry)
