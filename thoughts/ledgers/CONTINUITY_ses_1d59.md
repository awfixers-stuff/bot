---
session: ses_1d59
updated: 2026-05-15T06:47:09.582Z
---

# Session Summary

## Goal
Explore the entire bot codebase at `/home/awfixer/Projects/bot` and produce a comprehensive architectural overview covering directory structure, database models, multi-guild support patterns, permission system, config dashboard, cog loading, levels system, and sharding — returning all findings with file paths and line numbers.

## Constraints & Preferences
- Return ALL findings with specific file paths and line numbers
- Be very thorough — understand everything that makes this bot multi-guild vs single-guild
- Preserve exact file paths and identifiers
- Prefer terse bullets over paragraphs
- Use the exact output structure requested

## Progress

### Done

#### 1. Directory Structure — Top-Level under `src/bot/`
- **`cache/`** — `__init__.py`, `backend.py`, `managers.py`, `service.py`, `ttl.py`
- **`core/`** — `app.py`, `base_cog.py`, `bot.py`, `checks.py`, `cog_loader.py`, `context.py`, `converters.py`, `decorators.py`, `flags.py`, `http_config.py`, `logging.py`, `permission_system.py`, `prefix_manager.py`, `setup/`, `task_monitor.py`, `types.py`
- **`database/`** — `controllers/`, `gather_results.py`, `migrations/`, `models/`, `service.py`, `utils.py`
- **`help/`**
- **`main.py`**
- **`modules/`** — `admin/`, `config/`, `features/`, `fun/`, `guild/`, `info/`, `levels/`, `moderation/`, `snippets/`, `tools/`, `utility/`
- **`plugins/`** — `atl/`, `v0_1_db_migrate/`
- **`services/`**
- **`shared/`** — `config/`, `constants.py`, `exceptions/`, `functions.py`, `regex.py`, `version.py`
- **`ui/`** — `banner.py`, `buttons.py`, `embeds.py`, `modals/`, `views/`

#### 2. Database Models — `src/bot/database/models/`

**Model files and their guild-specific fields:**

| Model File | Primary Fields with `guild_id` / Guild Scope |
|---|---|
| **`models.py:35` — `Guild`** | `id` (primary key — the Discord guild ID itself is the PK). Fields: `id` (BigInteger PK), `guild_joined_at`, `case_count`. No separate `guild_id` — the model IS the guild. |
| **`models.py:75` — `GuildConfig`** | `guild_id` (BigInteger, primary key, FK → Guild.id). Fields: `guild_id`, `prefix`, `log_channel_id`, `jail_channel_id`, `jail_role_id`, `mod_log_channel_id`, `member_log_channel_id`, `message_log_channel_id`, `voice_log_channel_id`, `auto_mod_webhook_id`, `onboarding_stage`, `premium_tier`, `premium_expires_at`. |
| **`models.py:141` — `Case`** | `guild_id` (BigInteger, FK → Guild.id, indexed). Fields: `id`, `guild_id`, `case_num` (guild-scoped auto-increment), `case_type`, `target_id`, `moderator_id`, `reason`, `duration`, `created_at`, `updated_at`. Index: `ix_case_guild_number` on (`guild_id`, `case_num`). |
| **`models.py:193` — `Snippet`** | `guild_id` (BigInteger, FK → Guild.id). Fields: `id`, `guild_id`, `name`, `content`, `author_id`, `created_at`, `updated_at`. Index: `ix_snippet_guild_name` on (`guild_id`, `name`). |
| **`models.py:235` — `Reminder`** | **No `guild_id`.** Fields: `id`, `user_id` (BigInteger indexed), `channel_id` (BigInteger), `message_id` (BigInteger), `remind_at`, `content`, `created_at`. |
| **`models.py:275` — `Levels`** | `guild_id` (BigInteger, FK → Guild.id). Fields: `id`, `member_id` (BigInteger), `guild_id`, `xp`, `level`, `blacklisted`, `created_at`, `updated_at`. Index: `ix_levels_member_guild` on (`member_id`, `guild_id`). |
| **`models.py:327` — `AFK`** | **No `guild_id`.** Fields: `id`, `user_id` (BigInteger PK), `reason`, `afk_since`, `guild_id` (BigInteger, nullable — per `src/bot/modules/utility/afk.py:450` it iterates all guilds). |
| **`models.py:363` — `Starboard`** | `guild_id` (BigInteger, FK → Guild.id). Fields: `id`, `guild_id`, `channel_id`, `emoji`, `reaction_count`, `self_star`, `enabled`, `created_at`, `updated_at`. |
| **`models.py:413` — `StarboardMessage`** | **No `guild_id` directly** (linked through Starboard). Fields: `id`, `starboard_id` (FK → Starboard.id), `message_id`, `star_message_id`, `author_id`, `channel_id`, `guild_id` (BigInteger, FK → Guild.id, indexed). |
| **`models.py:481` — `PermissionRank`** | `guild_id` (BigInteger, FK → Guild.id). Fields: `id`, `guild_id`, `rank` (integer 0-10), `name` (e.g., "Admin", "Mod"), `created_at`, `updated_at`. |
| **`models.py:534` — `PermissionCommand`** | `guild_id` (BigInteger, FK → Guild.id). Fields: `id`, `guild_id`, `command_name`, `required_rank`, `created_at`, `updated_at`. |
| **`models.py:578` — `PermissionAssignment`** | `guild_id` (BigInteger, FK → Guild.id). Fields: `id`, `guild_id`, `role_id`, `rank_id`, `created_at`, `updated_at`. |

**Models WITHOUT `guild_id`:** `Reminder` (user-scoped), `AFK` (nullable guild_id, but `afk.py:450` iterates all guilds to check).

**Base classes in `base.py`:**
- `TimestampMixin` (line 22): `created_at`, `updated_at`
- `BaseModel` (line 50): Inherits `TimestampMixin`
- `SoftDeleteMixin` (line 98): `deleted_at`
- `UUIDMixin` (line 143): `id` (UUID4 primary key)

#### 3. Multi-Guild Support — Exhaustive Analysis

**3a. `guild_id` in queries/models — EVERY guild-scoped controller filters by `guild_id`:**

| File | Line(s) | Pattern |
|---|---|---|
| `database/controllers/guild_config.py` | 36-45 | `get_config_by_guild_id(guild_id)` → `get_by_id(guild_id)` |
| `database/controllers/levels.py` | 35-49 | `get_levels_by_member(member_id, guild_id)` → filter `(Levels.member_id == member_id) & (Levels.guild_id == guild_id)` |
| `database/controllers/levels.py` | 71-84 | `get_guild_leaderboard(guild_id, limit)` → filter `Levels.guild_id == guild_id` |
| `database/controllers/levels.py` | 119-134 | `get_rank(member_id, guild_id)` → rank query filtered by `guild_id` |
| `database/controllers/levels.py` | 175-196 | `bulk_get_or_create_levels(member_ids, guild_id)` |
| `database/controllers/guild.py` | 38-47 | `get_guild_by_id(guild_id)` |
| `database/controllers/base.py` | — | Base controller typically uses `get_by_id` (which for GuildConfig maps to `guild_id`) |

**3b. Prefix management — `PrefixManager` (`core/prefix_manager.py`):**
- **Line 35-55**: Class docstring — "in-memory cache mapping guild IDs to prefixes"
- **Line 74**: `_prefix_cache: dict[int, str]` — guild_id → prefix cache
- **Line 122-139**: `get_prefix(guild_id: int | None)` — resolves prefix:
  1. DM/None → returns `CONFIG.get_prefix()` default
  2. Check env override `BOT_INFO__PREFIX`
  3. Check cache (O(1) lookup by guild_id)
  4. Cache miss → load from database (`GuildConfig.prefix` for that guild_id)
  5. Store in cache → return
- **Line 234-246**: `set_prefix(guild_id: int, prefix: str)` — updates cache + DB
- **Line 260-270**: `_warmup_cache()` — bulk loads ALL guild prefixes from DB on startup

**Called from `core/app.py:27-54` — `get_prefix()` function**:
- Line 46: `guild_id = message.guild.id if message.guild else None`
- Line 50: `prefix = await bot.prefix_manager.get_prefix(guild_id)`
- This is the function passed as `command_prefix` to `commands.Bot.__init__`

**3c. Shard support:**
- **NO ShardedBot, no `shard_id` in bot class**. The bot is `commands.Bot` (line 48 of `bot.py`), not `AutoShardedBot`.
- **`ping.py:106-107`** checks `self.bot.shard_count` — but this is only for info display: `is_sharded = self.bot.shard_count is not None and self.bot.shard_count > 1`. It displays "Not sharded" if false.
- **`help/data.py:22`** uses `commands.Bot | commands.AutoShardedBot` in a type annotation — just union typing, no actual shard logic.
- **`plugins/atl/mock.py:648`** has a mock `{"shard_id": None, "code": 4004}` — for testing.
- **Conclusion**: The bot is NOT sharded. It runs as a single process.

**3d. Guild count / guild counting logic:**
| File | Line(s) | Pattern |
|---|---|---|
| `services/handlers/activity.py` | 128-132 | `len(self.bot.guilds)` for presence activity status |
| `core/permission_system.py` | 861-878 | Pre-warms permission cache for ALL `self.bot.guilds` |
| `modules/utility/ping.py` | 103 | `guild_count = len(self.bot.guilds)` for stats |
| `modules/utility/afk.py` | 450 | `for guild in self.bot.guilds` — iterates ALL guilds for AFK cleanup |
| `modules/features/status_roles.py` | 65 | `for guild in self.bot.guilds` |
| `plugins/atl/fact.py` | 60-63 | `sum(guild.member_count...)`, `len(bot.guilds)` |
| `services/handlers/event.py` | 53, 98, 103 | Iterates `self.bot.guilds` on `on_ready` to register guilds in DB |

**3e. Per-guild configuration patterns — EVERYTHING is scoped by guild:**
- **Database**: All major data models carry `guild_id` as FK or composite key.
- **Config dashboard** (`ui/views/config/dashboard.py`): Every interaction receives `interaction.guild_id` and validates author is in that guild.
- **Permission system** (`core/permission_system.py`): Every method takes `guild_id` — `get_rank(guild_id, ...)`, `get_effective_permission(guild_id, ...)`, `prewarm_cache_for_guild(guild_id)`.
- **Prefix manager**: Per-guild `_prefix_cache[guild_id]`.
- **Commands**: Decorated with `@commands.guild_only()` on all guild-scoped commands.
- **Levels service** (`modules/features/levels.py:125-132`): Processes messages per-guild, uses `message.guild.id` throughout.

#### 4. Permission System — `core/permission_system.py`

**File**: `/home/awfixer/Projects/bot/src/bot/core/permission_system.py`
**Lines**: 1-1035 (full file)

**Architecture — Database-driven, per-guild permission hierarchy:**

```
PermissionRank (guild_id, rank 0-10, name)
    ↑
PermissionCommand (guild_id, command_name, required_rank)
    ↑
PermissionAssignment (guild_id, role_id, rank_id)
```

**Key classes and methods:**
- **`RankDefinition`** (line 117): TypedDict for `{rank, name, is_default, created_at}`
- **`PermissionSystem`** (line 206): Main class with:
  - **`__init__`** (line 212): Stores `bot` reference, `_cache` (AsyncCacheBackendProtocol), `_lock` for thread safety
  - **`get_or_create_default_ranks(guild_id)`** (line 324): Creates default rank definitions for a guild (e.g., Admin=10, Mod=5, Member=0)
  - **`get_rank(guild_id, rank)`** (line 385): Returns rank definition for a guild
  - **`get_effective_permission(guild_id, guild_permissions, roles)`** (line ~410): Computes highest permission rank from member's roles
  - **`get_effective_permission_for_member(guild_id, member_id)`**: Looks up member roles → matches assignments → returns highest rank
  - **`check_required_permission(guild_id, command_name, member_id)`** (line ~480): Core check — gets required rank for command → gets member's effective rank → compares
  - **`set_command_rank(guild_id, command_name, required_rank)`** (line ~540): Configures required rank for a command
  - **`prewarm_cache_for_guild(guild_id)`** (line ~830): Pre-loads permissions for a guild into cache
  - **`prewarm_cache()`** (line ~860): Calls `prewarm_cache_for_guild` for ALL `self.bot.guilds`

**Permission check decorator** (`core/decorators.py`):
- **`requires_command_permission()`** (line 49): Decorator that wraps commands to:
  1. Extract `guild_id` from `ctx.guild.id`
  2. Call `permission_system.check_required_permission(guild_id, command_name, member_id)`
  3. Raise `BotPermissionDeniedError` if insufficient rank
  4. Auto-register command in DB if unconfigured (line 112-130)
- **Default behavior**: Commands are DENIED by default until configured (`allow_unconfigured=False`)

**Per-guild? YES — completely.** Every permission check takes `guild_id`. Ranks, assignments, and command requirements are all scoped to a guild. Two different guilds can have completely different permission configurations.

#### 5. Config Dashboard — `ui/views/config/dashboard.py`

**File**: `/home/awfixer/Projects/bot/src/bot/ui/views/config/dashboard.py`
**Lines**: 1-60710 (very large file)

**Per-guild? YES.**

- Line 23-54: The `ConfigDashboard` class receives guild context from every interaction.
- All callbacks validate `interaction.guild_id` matches (`validate_author` in `callbacks.py`).
- The dashboard launches per-guild (invoked from `@commands.guild_only()` commands in `modules/config/config.py:44-55`).
- Sub-managers (`RankManager`, `RoleManager`, `CommandManager`, `LogManager`, `JailManager`) all operate on the invoking guild's data.
- **`ConfigOverview`** (in `overview.py`) shows guild-specific settings.
- **`PaginationHelper`** supports guild-scoped lists (commands, roles, ranks).

#### 6. Cog Loading — `core/cog_loader.py`

**File**: `/home/awfixer/Projects/bot/src/bot/core/cog_loader.py`
**Lines**: 1-24281 (large file)

**How cogs are loaded:**
- **`CogLoader`** (line 41) extends `commands.Cog` — it's a cog itself that loads other cogs.
- **Discovery**: Scans filesystem paths defined in `CONFIG.COG_PATHS` using `aiofiles.os.scandir()`, finds all `*.py` files.
- **Priority system**: Uses `COG_PRIORITIES` dict from `shared/constants.py` — e.g., core cogs load first, feature cogs later.
- **Concurrent loading**: Within the same priority group, cogs load concurrently via `asyncio.gather`.
- **Validation**: Checks for `setup()` function via AST parsing before attempting load.
- **Error handling**: Skips cogs with missing config requirements (graceful degradation), logs failures to Sentry.

**Hot-reload? YES.** Line ~420-480:
- **`reload_cog(cog_name)`**: Unloads then reloads a single cog.
- **`reload_all_cogs()`**: Reloads all currently loaded cogs.
- **`reload_changed_cogs()`**: Compares file modification timestamps and reloads changed cogs.
- File watching: Uses `aiofiles.os.stat()` to check `st_mtime` on loaded cog files.

**Load order** (from setup/orchestrator.py:40-46):
1. Database setup (`DatabaseSetupService`)
2. Cache setup (`CacheSetupService`)
3. Permission system setup (`PermissionSetupService`)
4. Prefix manager setup (`PrefixSetupService`)
5. Cog loading (`CogSetupService`)

#### 7. Levels System — Per-Guild Analysis

**YES — the levels system is completely per-guild.**

**Data model** (`database/models/models.py:275-317`):
- `Levels` table has `member_id`, `guild_id`, `xp`, `level`, `blacklisted`
- Unique index: `ix_levels_member_guild` on (`member_id`, `guild_id`) — a user has separate levels per guild

**Controller** (`database/controllers/levels.py`):
- `get_levels_by_member(member_id, guild_id)` (line 35-49): Filters by BOTH member_id AND guild_id
- `get_or_create_levels(member_id, guild_id)` (line 52-69): Creates per-guild level record
- `get_guild_leaderboard(guild_id, limit)` (line 71-84): Completely guild-scoped
- `get_rank(member_id, guild_id)` (line 119-134): Rank within a specific guild
- `add_xp(member_id, guild_id, xp)` (line 96-117): Adds XP per-guild
- `bulk_get_or_create_levels(member_ids, guild_id)` (line 175-196): Bulk per-guild

**Service** (`modules/features/levels.py`):
- `LevelsService` (line 29): Processes `on_message` events — line 125: `guild_id = message.guild.id`
- `_check_and_assign_roles(member_id, guild_id, level)` (line 86): XP roles are guild-specific
- XP roles configured via `CONFIG.XP_CONFIG.XP_ROLES` (a list of `{level, role_id}` dicts — but these are global config, not per-guild DB config)

**Commands** (`modules/levels/levels.py` and `modules/levels/level.py`):
- All commands decorated with `@commands.guild_only()` (e.g., `levels.py:52`, `level.py:46`)
- Commands take `guild_id` from `ctx.guild.id`
- Admin commands: `setxp`, `setlevel`, `reset`, `blacklist` — all guild-scoped

**Important note on XP role config**: The `XP_ROLES` are read from global config (`CONFIG.XP_CONFIG.XP_ROLES`) — not from per-guild database. This means all guilds share the same XP→role mapping. The level/XP data itself is per-guild, but the role assignment mapping is global.

### In Progress
- [ ] No active work — this was a discovery/exploration session.

### Blocked
- (none)

## Key Decisions
- **Entire bot is multi-guild by design**: Every feature (levels, permissions, config, snippets, moderation, starboard) stores data per-guild using `guild_id` foreign keys. The bot is built to serve many Discord servers simultaneously.
- **Not sharded**: The bot uses `commands.Bot` (not `AutoShardedBot`). Shard info is display-only. This means the bot is designed for a single-process deployment with a single gateway connection.
- **Permission system is fully dynamic and per-guild**: Ranks (0-10 hierarchy), role assignments, and command requirements are all stored in the database per-guild. No hardcoded permission checks.
- **Prefix is per-guild**: Stored in `GuildConfig.prefix`, cached in memory (dict[int, str]), lazy-loaded on cache miss.
- **XP/levels are per-guild data, but role mappings are global**: `XP_ROLES` config is shared across all guilds via `CONFIG.XP_CONFIG.XP_ROLES`, not per-guild database.
- **AFK and Reminders are user-global, not per-guild**: `Reminder` has no `guild_id`. `AFK` has a nullable `guild_id` (and its cleanup iterates all guilds).
- **Cog loader supports hot-reload**: File-watching-based reload capability for development/debugging.

## Critical Context

### Architecture Summary
```
src/bot/
├── cache/              — Redis/memory caching backend
├── core/               — Bot class, cog loader, permissions, prefix, setup
├── database/           — SQLModel ORM, controllers, migrations
├── help/               — Help command system
├── main.py             — Entry point
├── modules/            — Discord cogs (config, features, fun, guild, info, levels, moderation, snippets, tools, utility)
├── plugins/            — Bot migration plugins (v0_1_db_migrate) and ATL
├── services/           — Event handlers, HTTP client, sentry, emoji manager
├── shared/             — Config, constants, exceptions, utilities
└── ui/                 — Embeds, modals, views, banners, buttons
```

### Multi-Guild vs Single-Guild Summary

| Feature | Multi-Guild? | How |
|---|---|---|
| **Guild data** | YES | `Guild` table (PK = discord guild_id) |
| **Guild config** | YES | `GuildConfig` with `guild_id` PK |
| **Prefix** | YES | Per-guild in DB + in-memory cache |
| **Permissions** | YES | 3 tables all with `guild_id` FK |
| **Levels/XP** | YES | Per-guild `Levels` records |
| **Moderation cases** | YES | `Case` with `guild_id` + per-guild case numbering |
| **Snippets** | YES | `Snippet` with `guild_id` |
| **Starboard** | YES | `Starboard` with `guild_id` |
| **Jail** | YES | Jail channel/role in `GuildConfig` |
| **Reminders** | NO | User-global (no `guild_id`) |
| **AFK** | PARTIAL | Nullable `guild_id`, global iteration |
| **Sharding** | NO | Single `commands.Bot`, no `AutoShardedBot` |
| **XP role config** | NO | Global `CONFIG.XP_CONFIG.XP_ROLES` |

### Key Pattern: Guild Initialization
In `services/handlers/event.py` on `on_ready` and `on_guild_join`:
- Line 48-103: Iterates `self.bot.guilds`, calls `db.guilds.upsert_guild(guild.id)` for each
- Line 85-95: On `on_guild_join`: creates `Guild` record, creates `GuildConfig` record (with default prefix), creates default permission ranks

### Permission Check Flow
1. Command invoked → `@requires_command_permission()` decorator
2. `decorators.py:112-130`: Extract `guild_id` from `ctx.guild`
3. `permission_system.check_required_permission(guild_id, command_name, member_id)`
4. Lookup `PermissionCommand` for `(guild_id, command_name)` → get `required_rank`
5. Lookup member's roles → `PermissionAssignment` for `(guild_id, role_id)` → get assigned ranks
6. Get member's highest rank → compare to required rank → allow/deny

## Next Steps
1. If continuing development, consider whether to add per-guild XP role configuration (currently global-only in `CONFIG.XP_CONFIG.XP_ROLES`)
2. If sharding is needed, the bot class (`bot.py:48`) extends `commands.Bot` — would need `AutoShardedBot`
3. Could audit AFK system to make it fully per-guild if desired (currently nullable `guild_id` with global iteration)

## File Operations

### Read
- `/home/awfixer/Projects/bot/src/bot`
- `/home/awfixer/Projects/bot/src/bot/__init__.py`
- `/home/awfixer/Projects/bot/src/bot/cache`
- `/home/awfixer/Projects/bot/src/bot/cache/__init__.py`
- `/home/awfixer/Projects/bot/src/bot/cache/backend.py`
- `/home/awfixer/Projects/bot/src/bot/cache/managers.py`
- `/home/awfixer/Projects/bot/src/bot/cache/service.py`
- `/home/awfixer/Projects/bot/src/bot/cache/ttl.py`
- `/home/awfixer/Projects/bot/src/bot/core`
- `/home/awfixer/Projects/bot/src/bot/core/app.py`
- `/home/awfixer/Projects/bot/src/bot/core/base_cog.py`
- `/home/awfixer/Projects/bot/src/bot/core/bot.py`
- `/home/awfixer/Projects/bot/src/bot/core/checks.py`
- `/home/awfixer/Projects/bot/src/bot/core/cog_loader.py`
- `/home/awfixer/Projects/bot/src/bot/core/decorators.py`
- `/home/awfixer/Projects/bot/src/bot/core/permission_system.py`
- `/home/awfixer/Projects/bot/src/bot/core/prefix_manager.py`
- `/home/awfixer/Projects/bot/src/bot/core/setup`
- `/home/awfixer/Projects/bot/src/bot/core/setup/orchestrator.py`
- `/home/awfixer/Projects/bot/src/bot/database`
- `/home/awfixer/Projects/bot/src/bot/database/controllers/__init__.py`
- `/home/awfixer/Projects/bot/src/bot/database/controllers/afk.py`
- `/home/awfixer/Projects/bot/src/bot/database/controllers/base.py`
- `/home/awfixer/Projects/bot/src/bot/database/controllers/case.py`
- `/home/awfixer/Projects/bot/src/bot/database/controllers/guild.py`
- `/home/awfixer/Projects/bot/src/bot/database/controllers/guild_config.py`
- `/home/awfixer/Projects/bot/src/bot/database/controllers/levels.py`
- `/home/awfixer/Projects/bot/src/bot/database/controllers/permissions.py`
- `/home/awfixer/Projects/bot/src/bot/database/controllers/reminder.py`
- `/home/awfixer/Projects/bot/src/bot/database/controllers/snippet.py`
- `/home/awfixer/Projects/bot/src/bot/database/controllers/starboard.py`
- `/home/awfixer/Projects/bot/src/bot/database/models`
- `/home/awfixer/Projects/bot/src/bot/database/models/__init__.py`
- `/home/awfixer/Projects/bot/src/bot/database/models/base.py`
- `/home/awfixer/Projects/bot/src/bot/database/models/enums.py`
- `/home/awfixer/Projects/bot/src/bot/database/models/models.py`
- `/home/awfixer/Projects/bot/src/bot/main.py`
- `/home/awfixer/Projects/bot/src/bot/modules`
- `/home/awfixer/Projects/bot/src/bot/modules/config/__init__.py`
- `/home/awfixer/Projects/bot/src/bot/modules/config/base.py`
- `/home/awfixer/Projects/bot/src/bot/modules/config/commands.py`
- `/home/awfixer/Projects/bot/src/bot/modules/config/config.py`
- `/home/awfixer/Projects/bot/src/bot/modules/config/jail.py`
- `/home/awfixer/Projects/bot/src/bot/modules/config/logs.py`
- `/home/awfixer/Projects/bot/src/bot/modules/config/overview.py`
- `/home/awfixer/Projects/bot/src/bot/modules/config/ranks.py`
- `/home/awfixer/Projects/bot/src/bot/modules/config/roles.py`
- `/home/awfixer/Projects/bot/src/bot/modules/features/levels.py`
- `/home/awfixer/Projects/bot/src/bot/modules/levels/level.py`
- `/home/awfixer/Projects/bot/src/bot/modules/levels/levels.py`
- `/home/awfixer/Projects/bot/src/bot/modules/utility/ping.py`
- `/home/awfixer/Projects/bot/src/bot/plugins`
- `/home/awfixer/Projects/bot/src/bot/services/handlers/activity.py`
- `/home/awfixer/Projects/bot/src/bot/services/handlers/event.py`
- `/home/awfixer/Projects/bot/src/bot/shared`
- `/home/awfixer/Projects/bot/src/bot/shared/config`
- `/home/awfixer/Projects/bot/src/bot/shared/config/__init__.py`
- `/home/awfixer/Projects/bot/src/bot/shared/constants.py`
- `/home/awfixer/Projects/bot/src/bot/shared/exceptions`
- `/home/awfixer/Projects/bot/src/bot/shared/exceptions/__init__.py`
- `/home/awfixer/Projects/bot/src/bot/shared/functions.py`
- `/home/awfixer/Projects/bot/src/bot/shared/regex.py`
- `/home/awfixer/Projects/bot/src/bot/shared/version.py`
- `/home/awfixer/Projects/bot/src/bot/ui`
- `/home/awfixer/Projects/bot/src/bot/ui/banner.py`
- `/home/awfixer/Projects/bot/src/bot/ui/buttons.py`
- `/home/awfixer/Projects/bot/src/bot/ui/embeds.py`
- `/home/awfixer/Projects/bot/src/bot/ui/modals`
- `/home/awfixer/Projects/bot/src/bot/ui/views`
- `/home/awfixer/Projects/bot/src/bot/ui/views/config/dashboard.py`
- `/home/awfixer/Projects/bot/src/bot/ui/views/config/callbacks.py`
- `/home/awfixer/Projects/bot/src/bot/ui/views/config/command_discovery.py`
- `/home/awfixer/Projects/bot/src/bot/ui/views/config/helpers.py`
- `/home/awfixer/Projects/bot/src/bot/ui/views/config/modals.py`
- `/home/awfixer/Projects/bot/src/bot/ui/views/config/pagination.py`
- `/home/awfixer/Projects/bot/src/bot/ui/views/config/ranks.py`

### Modified
- (none)
