# Single-Guild Simplification Plan

**Date**: 2026-05-14  
**Status**: In Progress — Phase 1 foundation work complete  
**Last Updated**: 2026-05-15  
**Goal**: Rebuild the bot to service only the AWFixer Enterprising Inc Discord server, removing ~5,000+ lines of multi-guild infrastructure.

---

## Overview

The bot is currently a multi-tenant platform where every guild is a first-class tenant with its own database rows, cache keys, prefix, permission ranks, and configuration. Since it only ever serves one server, ~30-40% of the codebase is unnecessary abstraction.

**Key stats (current):**
- `GUILD_ID` is now a startup-time constant in `CONFIG.BOT_INFO.GUILD_ID`
- `Guild` and `GuildConfig` models — **removed** ✓
- All 10 remaining DB models — **`guild_id` dropped** ✓
- `GuildController` / `GuildConfigController` — dead code (files on disk, not exported)
- `LogChannels` config model created with all log channel + jail fields ✓
- Remaining work: ~850+ `guild_id` references still in code, all controllers need simplification, config UI removal, prefix manager removal

---

## Guiding Principles

1. **The AWFixer server's guild ID becomes a compile-time/startup constant.** ✅ Done — `CONFIG.BOT_INFO.GUILD_ID`
2. **Global configuration (CONFIG singleton) absorbs everything currently in per-guild DB config.** ✅ Done — `LogChannels` model created
3. **Database models drop `guild_id` — composite PKs become simple PKs.** ✅ Done — all 10 remaining models cleaned
4. **Permission ranks are a single flat list, not per-guild.** ⬜ DB model done; controller & runtime work remains
5. **The config dashboard UI is removed; config becomes file/env driven.** ⬜ Not started
6. **ATL plugins graduate to first-class modules.** ⬜ Not started
7. **Changes are done in dependency order — each phase unblocks the next.** ✅ Foundation (Phase 1) unblocks everything else

---

## Phase 1: Foundation — Guild ID & Database

### 1.1 Add `GUILD_ID` to global CONFIG ✅ COMPLETE

**Files:**
- `src/bot/shared/config/models.py` — `GUILD_ID: int` field added to `BotInfo` model at line 45 ✅
- `LogChannels` model created with all log channel + jail fields ✅
- `CONFIG.LOG_CHANNELS` wired into `settings.py` ✅
- `config/config.json.example` — ❌ Still needs `GUILD_ID` and `LOG_CHANNELS` section
- `.env.example` — ❌ Should document `BOT_INFO__GUILD_ID`

### 1.2 Simplify database models ✅ COMPLETE

**File:** `src/bot/database/models/models.py` — All models verified clean.

| Model | Status | Notes |
|-------|--------|-------|
| `Guild` | **Removed** ✓ | Entire model deleted |
| `GuildConfig` | **Removed** ✓ | Entire model deleted |
| `PermissionRank` | **Clean** ✓ | No `guild_id`, `rank` unique |
| `PermissionAssignment` | **Clean** ✓ | No `guild_id`, FK to `PermissionRank.id` |
| `PermissionCommand` | **Clean** ✓ | No `guild_id`, `command_name` unique |
| `Case` | **Clean** ✓ | No `guild_id`, `case_number` unique |
| `Snippet` | **Clean** ✓ | No `guild_id`, `snippet_name` unique |
| `Reminder` | **Clean** ✓ | No `guild_id`, user-global |
| `AFK` | **Clean** ✓ | PK is `member_id` (no guild_id composite) |
| `Levels` | **Clean** ✓ | PK is `member_id` (no guild_id composite) |
| `Starboard` | **Clean** ✓ | No `guild_id`, single-row config |
| `StarboardMessage` | **Clean** ✓ | No `message_guild_id` |

### 1.3 Simplify database controllers ⬜ NOT STARTED

Each controller method that takes `guild_id` either:
- **Drops the parameter entirely** (the guild is now implicitly THIS guild)
- **Becomes a wrapper** that injects `GUILD_ID` internally (for minimal diff)

**Notes:**
- `guild.py` and `guild_config.py` files are dead code — not imported/exported by `__init__.py` or `DatabaseCoordinator` ⚠️ Files not yet deleted
- All other controllers still have `guild_id` in method signatures and queries

**Files:** `src/bot/database/controllers/`

| Controller | Lines | `guild_id` refs | Key changes needed |
|-----------|-------|-----------------|--------------------|
| `guild.py` | 223 | 17 | **Delete entire file** — no guild table |
| `guild_config.py` | 776 | 94 | **Delete entire file** — config is global CONFIG |
| `permissions.py` | 812 | 92 | Drop `guild_id` from every method, simplify cache keys |
| `case.py` | 703 | 60 | Drop `guild_id` param, `get_cases_by_guild` → `get_all_cases` |
| `snippet.py` | 436 | 39 | Drop `guild_id` from all methods |
| `levels.py` | 385 | 45 | Drop `guild_id` from all methods |
| `reminder.py` | 233 | 14 | Drop `guild_id` from all methods |
| `afk.py` | 290 | 29 | Drop `guild_id` from all methods |
| `starboard.py` | 359 | 31 | Drop `guild_id` from all methods |

### 1.4 Squash migrations ⬜ NOT STARTED

**Files:** 
- `src/bot/database/migrations/versions/2026_01_20_1143-12e5d7b32ddf_initial_schema.py` (721 lines)
- `src/bot/database/migrations/versions/2026_01_23_0138-0b3288704dea_add_case_perf_indexes.py` (48 lines)
- `src/bot/database/migrations/versions/2026_01_23_1811-b83284093e38_add_jail_unjail_index.py` (43 lines)

**Old migrations still reference `guild` and `guild_config` tables** that no longer exist in models. These must be replaced with a fresh migration.

**Action:** Generate a fresh initial migration from the new models. Drop and recreate the database.

### 1.5 Update base controller infrastructure ✅ COMPLETE

**File:** `src/bot/database/controllers/base/base_controller.py`  
**Check:** No `get_or_create(id=guild_id)` patterns found. Base controller was already generic — uses SQLModel session + type params only, no guild-specific logic.

---

## Phase 2: Permission System — Single Guild ⬜ NOT STARTED

### 2.1 Simplify PermissionSystem class

**File:** `src/bot/core/permission_system.py` (1015 lines — unchanged)

**Changes needed:**
1. Remove `initialize_guild(guild_id)` — ranks are initialized once at startup, not per guild
2. Remove `prewarm_cache_for_all_guilds()` → becomes `prewarm_cache()` (one guild)
3. All methods drop `guild_id` parameter:
   - `get_user_permission_rank(ctx)` → uses `ctx.guild.id` internally (which is now always `GUILD_ID`)
   - `get_command_permission(command_name)` — drops `guild_id`
   - `assign_permission_rank(rank, role_id)` — drops `guild_id`
   - `set_command_permission(command_name, required_rank)` — drops `guild_id`
4. Cache keys: `perm:command_permission_fallback:{command_name}` instead of `perm:command_permission_fallback:{guild_id}:{command_name}`
5. Remove `load_from_config(guild_id, config)` — config is global

**Result:** ~600-700 lines removed.

### 2.2 Update decorators

**File:** `src/bot/core/decorators.py` (446 lines)

**Changes:**
- `_check_permissions()` — `guild` is still available from `ctx.guild`/`interaction.guild`, but it's now always `GUILD_ID`. No logical change needed — the parameter still flows through, it's just that the permission system ignores it.

---

## Phase 3: Cache & Prefix — Single Guild ⬜ NOT STARTED

### 3.1 Prefix Manager → Simple Constant

**File:** `src/bot/core/prefix_manager.py` (329 lines — unchanged)

**Change:** 
- Remove `PrefixManager` class entirely
- `get_prefix()` already exists as `CONFIG.get_prefix()` which returns `CONFIG.BOT_INFO.PREFIX`
- Remove `bot.prefix_manager` reference
- Remove prefix cache (in-memory dict, Valkey keys)
- Remove `load_all_prefixes()`, `_persist_prefix()`, `_load_guild_prefix()`
- Remove `PrefixSetupService` (or gut it)

**Result:** ~329 lines removed. Prefix is already a constant; just need to remove the infrastructure.

### 3.2 Simplify cache layer

**File:** `src/bot/cache/managers.py`

**Change:**
- `GuildConfigCacheManager` — remove entirely (no more GuildConfig)
- All cache keys that include `{guild_id}:` — drop the prefix. Keys like:
  - `prefix:{guild_id}` → removed (no prefix manager)
  - `perm:...:{guild_id}:{cmd}` → `perm:...:{cmd}`
  - `guild_config:{guild_id}` → removed

---

## Phase 4: Event Handlers — Single Guild ⬜ NOT STARTED

### 4.1 Remove multi-guild registration

**File:** `src/bot/services/handlers/event.py` (260 lines)

**Changes:**
1. `on_ready()`: Remove the `for guild in self.bot.guilds:` loop that registers guilds in DB. Replace with a single check or remove entirely since guild registration is no longer needed.
2. `on_guild_join()`: Remove or no-op.
3. `on_guild_remove()`: Remove or no-op.
4. `on_guild_channel_create()`: Change `db.guild_config.get_jail_role_id(guild.id)` to `CONFIG.LOG_CHANNELS.JAIL_ROLE_ID`
5. Remove `_guilds_registered` flag and related logic

### 4.2 Remove `guilds_registered` from Bot

**File:** `src/bot/core/bot.py`

**Change:**
- Remove `self.guilds_registered = asyncio.Event()`
- Remove all references to `self.guilds_registered`
- Waiters (`status_roles.py`, `remindme.py`) — remove wait

### 4.3 Update startup banner/stats

**File:** `src/bot/core/bot.py`

**Change:**
- `_log_startup_banner()`: `len(self.guilds)` → `1`. `sum(len(g.channels) for g in self.guilds)` → `len(guild.channels)`
- `_record_bot_stats()`: guild_count is 1.

---

## Phase 5: Config Dashboard — Remove or Replace

### 5.1 Remove entire config UI ⬜ NOT STARTED

**Files to remove:** `src/bot/ui/views/config/` (4,432 lines)

| File | Lines | Action |
|------|-------|--------|
| `dashboard.py` | 2,736 | Delete |
| `callbacks.py` | 828 | Delete |
| `modals.py` | 278 | Delete |
| `pagination.py` | 287 | Delete |
| `helpers.py` | 94 | Delete |
| `command_discovery.py` | 94 | Delete |
| `ranks.py` | 102 | Delete |
| `__init__.py` | — | Remove `ConfigDashboard` export |

### 5.2 Remove or gut config commands ⬜ NOT STARTED

**Files:** `src/bot/modules/config/` (624 lines)

- `config.py` — Remove hybrid command group
- `base.py` — Remove `BaseConfigManager` and `configure_dashboard()`
- `overview.py`, `ranks.py`, `roles.py`, `commands.py`, `logs.py`, `jail.py` — Remove all
- OR: Replace with a minimal `/config` read-only status command

### 5.3 Move per-guild config fields to global CONFIG ✅ COMPLETE

**`LogChannels` model created in `src/bot/shared/config/models.py`:**

| Field | Location | Status |
|-------|----------|--------|
| `prefix` | `CONFIG.BOT_INFO.PREFIX` | ✅ Already existed |
| `mod_log_id` | `CONFIG.LOG_CHANNELS.MOD_LOG_ID` | ✅ Done |
| `audit_log_id` | `CONFIG.LOG_CHANNELS.AUDIT_LOG_ID` | ✅ Done |
| `join_log_id` | `CONFIG.LOG_CHANNELS.JOIN_LOG_ID` | ✅ Done |
| `private_log_id` | `CONFIG.LOG_CHANNELS.PRIVATE_LOG_ID` | ✅ Done |
| `report_log_id` | `CONFIG.LOG_CHANNELS.REPORT_LOG_ID` | ✅ Done |
| `dev_log_id` | `CONFIG.LOG_CHANNELS.DEV_LOG_ID` | ✅ Done |
| `jail_channel_id` | `CONFIG.LOG_CHANNELS.JAIL_CHANNEL_ID` | ✅ Done |
| `jail_role_id` | `CONFIG.LOG_CHANNELS.JAIL_ROLE_ID` | ✅ Done |
| `onboarding_completed` | Removed | ✅ N/A |
| `onboarding_stage` | Removed | ✅ N/A |

**Also needed:** Update `config/config.json.example` to include `LOG_CHANNELS` and `GUILD_ID` sections.

### 5.4 Update all consumers of per-guild config ⬜ NOT STARTED

Files that still reference `guild_config.get_*` methods — must read from CONFIG instead:

- `src/bot/services/handlers/event.py` — `get_jail_role_id` → `CONFIG.LOG_CHANNELS.JAIL_ROLE_ID`
- `src/bot/services/moderation/communication_service.py` — `get_log_channel_ids` → CONFIG
- `src/bot/modules/moderation/jail.py` — `get_jail_channel_id`, `get_jail_config` → CONFIG
- `src/bot/modules/moderation/unjail.py` — `get_jail_role_id` → CONFIG
- `src/bot/modules/moderation/cases.py` — `get_log_channel_ids` → CONFIG

---

## Phase 6: Modules Cleanup ⬜ NOT STARTED

### 6.1 Move ATL plugins to modules

**Source:** `src/bot/plugins/atl/` (12 files)  
**Destination:** `src/bot/modules/features/`

| Plugin | Destination | Notes |
|--------|-------------|-------|
| `supportnotifier.py` | `modules/features/support_notifier.py` | Hardcoded IDs → CONFIG |
| `fact.py` | `modules/features/fact.py` | Already generic |
| `mock.py` | `modules/admin/mock.py` | Admin debugging tool |
| `deepfry.py` | `modules/fun/deepfry.py` | Fun/utility command |
| `flagremover.py` | `modules/features/flag_remover.py` | Channel ID → CONFIG |
| `git.py` | `modules/tools/git.py` | Already generic |
| `harmfulcommands.py` | `modules/features/harmful_commands.py` | Already generic |
| `mail.py` | `modules/tools/mail.py` | Already generic |
| `rolecount.py` | `modules/features/role_count.py` | Hardcoded ATL IDs |
| `tty_roles.py` | `modules/features/tty_roles.py` | Already generic |

### 6.2 Clean up `bot.guilds` iteration ⬜ NOT STARTED

Files that iterate `bot.guilds` — need to use single guild reference:

| File | What needs changing |
|------|-------------------|
| `bot.py` | Startup banner stats, guild count |
| `event.py` | Guild registration loop |
| `permission_system.py` | `prewarm_cache_for_all_guilds()` |
| `activity.py` | `{member_count}`, `{guild_count}` placeholders |
| `fact.py` | Same as activity.py |
| `status_roles.py` | `guilds_registered` wait |
| `afk.py` | Guild iteration |
| `ping.py` | `guild_count` |
| `remindme.py` | `guilds_registered` wait |
| `tempban.py` | Guild iteration |

---

## Phase 7: Clean Up Services & Utilities ⬜ NOT STARTED

### 7.1 Remove migration plugin

**File:** `src/bot/plugins/v0_1_db_migrate/` — Old migration plugin no longer needed.

### 7.2 Simplify hot-reload (if kept)

**File:** `src/bot/services/hot_reload/` — Keep as-is; doesn't add complexity.

### 7.3 Remove `Guild`-dependent methods from BaseCog

**File:** `src/bot/core/base_cog.py` — Methods like `is_jailed`, `is_snippetbanned` that reference guild-level data need simplification.

---

## Phase 8: Testing & Verification ⬜ NOT STARTED

### 8.1 Update tests

- `tests/database/test_database_service.py` — Update for new models
- `tests/shared/test_config_settings.py` — Add GUILD_ID test
- `tests/shared/test_config_models.py` — Update for LogChannels
- All tests referencing `guild_id` — bulk update

### 8.2 Migration script

Generate a fresh initial migration from new models. Drop and recreate the database since this is a rebuild.

---

## Line Count Summary

| Area | Current Lines | After | Removed | Status |
|------|--------------|-------|---------|--------|
| Config UI (`ui/views/config/`) | 4,432 | 0 | -4,432 | ⬜ |
| Config commands (`modules/config/`) | 624 | ~50 | -574 | ⬜ |
| GuildConfigController | 776 | 0 | -776 | ⬜ |
| GuildController | 223 | 0 | -223 | ⬜ |
| Permission controllers | 812 | ~300 | -512 | ⬜ |
| CaseController | 703 | ~400 | -303 | ⬜ |
| SnippetController | 436 | ~250 | -186 | ⬜ |
| LevelsController | 385 | ~200 | -185 | ⬜ |
| ReminderController | 233 | ~150 | -83 | ⬜ |
| AfkController | 290 | ~180 | -110 | ⬜ |
| StarboardController | 359 | ~200 | -159 | ⬜ |
| PermissionSystem | 1,015 | ~400 | -615 | ⬜ |
| PrefixManager | 329 | 0 | -329 | ⬜ |
| Event handlers | 260 | ~150 | -110 | ⬜ |
| Bot core (guild stuff) | 410 | ~350 | -60 | ⬜ |
| Migration plugin | ~500 | 0 | -500 | ⬜ |
| Database models | 812 (already slim) | 700 | -112 | ✅ |
| Config models (new) | +631 added | — | +631 (new) | ✅ |
| **Totals** | **~12,466** | **~3,330** | **~-9,136** | |

---

## Risk Assessment

| Risk | Likelihood | Mitigation | Status |
|------|-----------|------------|--------|
| Breaking existing data (guild_id queries) | Low (rebuild) | Fresh database for rebuild | ⬜ |
| Permission system regression | Medium | Test all permission levels after simplification | ⬜ |
| Missing log channel references | **Low now** | ✅ LogChannels already in CONFIG | ✅ |
| Case numbering without Guild.case_count | **Resolved** | `case_number` is unique auto-increment | ✅ |
| Forgetting a `bot.guilds` iteration | Low | Search and verify all references | ⬜ |
| Import errors from removed files | Low | Let mypy/ruff catch them | ⬜ |

---

## Execution Order

```
Phase 1 (Foundation) — 1.1 ✅ 1.2 ✅ 1.5 ✅ | 1.3 ⬜ 1.4 ⬜
  ├── 1.1 ✅ Add GUILD_ID to CONFIG
  ├── 1.2 ✅ Simplify DB models
  ├── 1.3 ⬜ Simplify DB controllers  ← ACTIVE
  ├── 1.4 ⬜ Squash migrations
  └── 1.5 ✅ Update base controller
        │
Phase 2 (Permission) — ⬜
  ├── 2.1 ⬜ Simplify PermissionSystem
  └── 2.2 ⬜ Update decorators
        │
Phase 3 (Cache & Prefix) — ⬜
  ├── 3.1 ⬜ Remove PrefixManager
  └── 3.2 ⬜ Simplify cache layer
        │
Phase 4 (Events) — ⬜
  ├── 4.1 ⬜ Remove multi-guild registration
  ├── 4.2 ⬜ Remove guilds_registered event
  └── 4.3 ⬜ Update startup banner/stats
        │
Phase 5 (Config Dashboard) — 5.3 ✅ | 5.1 ⬜ 5.2 ⬜ 5.4 ⬜
  ├── 5.1 ⬜ Remove config UI files
  ├── 5.2 ⬜ Gut config commands
  ├── 5.3 ✅ Move fields to CONFIG
  └── 5.4 ⬜ Update consumers
        │
Phase 6 (Modules) — ⬜
  ├── 6.1 ⬜ Move ATL plugins → modules
  └── 6.2 ⬜ Clean up bot.guilds iteration
        │
Phase 7 (Cleanup) — ⬜
  ├── 7.1 ⬜ Remove migration plugin
  └── 7.3 ⬜ Simplify BaseCog methods
        │
Phase 8 (Testing) — ⬜
  ├── 8.1 ⬜ Update tests
  └── 8.2 ⬜ Migration script
```

Each phase is blocked on the previous phase completing. Within a phase, tasks are parallel where possible.
