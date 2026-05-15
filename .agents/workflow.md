# Workflow, Docker, and contributing

> ## Branch and Pull Request Requirement
>
> **All changes — including AI-generated changes — MUST be created on a new feature branch and submitted as a pull request.**
>
> Direct commits to `main` are strictly prohibited. Every change follows this lifecycle:
>
> **Create branch → Develop → Commit → Push → Open PR → Review → Merge → Delete branch**
>
> Branch naming: `<type>/<short-description>` (e.g., `feat/add-auth`, `fix/memory-leak`, `docs/update-readme`).
> See [branch naming conventions](../docs/content/developer/best-practices/branch-naming.md) for all types.

## Development workflow

1. **Branch:** Create a feature branch from `main`: `git checkout -b feat/your-change` (see [branch naming](best-practices/branch-naming.md) for types)
2. **Setup:** `uv sync` → configure `.env` & `config.json` → `docker compose up -d tux-postgres` → `uv run db init`
3. **Develop:** Make changes → `uv run dev all` → `uv run test quick`
4. **Database:** Modify models → `uv run db new "description"` → `uv run db dev` (or `uv run db dev --name "description"` for auto-create+apply)
5. **Rules:** Validate rules/commands → `uv run ai validate-rules`
6. **Commit:** `uv run dev pre-commit` → `uv run test all`
7. **PR:** Push branch → open pull request → get review → merge → delete branch

## Docker Compose

Tux uses a single `compose.yaml` with profiles for development and production:

```bash
# Development (build from source, hot reload)
docker compose --profile dev up -d
docker compose --profile dev up --watch  # With hot reload

# Production (pre-built image, security hardening)
docker compose --profile production up -d

# Add Adminer (database UI)
docker compose --profile dev --profile adminer up -d
docker compose --profile production --profile adminer up -d

# Using environment variable
COMPOSE_PROFILES=dev docker compose up -d
COMPOSE_PROFILES=production docker compose up -d

# PostgreSQL only (no profile needed)
docker compose up -d tux-postgres
```

**Profiles:**

- `dev` - Development mode with source bindings and hot reload
- `production` - Production mode with pre-built image and security hardening
- `adminer` - Optional database management UI (combine with dev or production)

**Note:** `tux-postgres` has no profile and always starts. Use `--profile valkey` to start Valkey (optional cache). Do not use `--profile dev` and `--profile production` together.

**Optional: Valkey (cache):** For shared cache across processes or restarts, start Valkey and set env:

```bash
docker compose --profile valkey up -d tux-valkey
# In .env: VALKEY_URL=valkey://localhost:6379/0  (or leave unset to use in-memory cache)
```

When `VALKEY_URL` is set and reachable, guild config, jail status, prefix, and permission caches use Valkey; otherwise they use in-memory TTL caches.

## Conventional commits

Format: `<type>[scope]: <description>`

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`

**Rules:**

- Lowercase type
- Max 120 chars subject
- No period at end
- Start with lowercase

**Examples:**

```bash
feat: add user authentication
fix: resolve memory leak in message handler
docs: update API documentation
refactor(database): optimize query performance
```

## Pull requests

**Title:** `[module/area] Brief description`

**Requirements:**

- Branch is up to date with `main` (rebase before opening)
- All tests pass (`uv run test all`)
- Quality checks pass (`uv run dev all`)
- Migrations tested (`uv run db dev`)
- Cursor rules/commands validated (`uv run ai validate-rules`)
- Documentation updated
- Type hints complete
- Docstrings for public APIs
- **Never commit directly to `main`** — always use a feature branch and PR
