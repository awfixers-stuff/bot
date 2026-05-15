---
title: Database Management
tags:
  - selfhost
  - operations
  - database
icon: lucide/database
---

# Database Management

!!! warning "Work in progress"
    This section is a work in progress. Please help us by contributing to the documentation.

Manage your Bot database including backups, migrations, and administration tools.

## Database Backups

Protect your data with regular backups.

### Backup Strategies

#### Manual Backup

```bash
# Docker Compose
docker compose exec bot-postgres pg_dump -U botuser botdb > backup_$(date +%Y%m%d).sql

# With compression
docker compose exec bot-postgres pg_dump -U botuser botdb | gzip > backup_$(date +%Y%m%d).sql.gz

# Local PostgreSQL
pg_dump -h localhost -U botuser botdb > backup.sql
```

#### Automated Backups

Create `backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup
docker compose exec bot-postgres pg_dump -U botuser botdb | gzip > "$BACKUP_DIR/bot_$DATE.sql.gz"

# Keep only last 30 days
find "$BACKUP_DIR" -name "bot_*.sql.gz" -mtime +30 -delete

# Optional: Upload to cloud storage
# rclone copy "$BACKUP_DIR/bot_$DATE.sql.gz" remote:backups/
```

**Add to cron:**

```bash
# Daily at 2 AM
0 2 * * * /path/to/backup.sh
```

### Restore

```bash
# From SQL file
docker compose exec -T bot-postgres psql -U botuser botdb < backup.sql

# From gzip
gunzip < backup.sql.gz | docker compose exec -T bot-postgres psql -U botuser botdb

# Or
docker compose exec bot-postgres psql -U botuser botdb < backup.sql
```

### Best Practices

- Backup daily (minimum)
- Test restore procedures regularly
- Store backups off-site
- Encrypt sensitive backups
- Keep multiple backup generations
- Document restore process

## Database Migrations

Manage database schema changes with Alembic migrations.

### What Are Migrations?

Migrations are version-controlled database schema changes:

- Track schema history
- Apply changes incrementally
- Rollback if needed
- Share schema changes with team

Bot uses **Alembic** for migrations.

### CLI Commands

#### Apply Migrations

```bash
# Apply all pending migrations
uv run db push

# Check status
uv run db status

# View history
uv run db history
```

#### After Updates

When updating Bot:

```bash
git pull
uv sync
uv run db push                      # Apply new migrations
docker compose restart bot          # Restart bot
```

### Migration Files

Located in: `src/bot/database/migrations/versions/`

**Don't manually edit** migration files unless you know what you're doing.

### Docker Migrations

Migrations run automatically on container startup. By default, migrations come from the Docker image (no source code needed).

**For development or customization:**

Enable migration mount for local development:

Create `compose.override.yaml`:

```yaml
services:
  bot:
    volumes:
      # Mount migrations for faster development/customization iteration
      # Without this, migrations come from the Docker image (production behavior)
      - ./src/bot/database/migrations:/app/src/bot/database/migrations:ro
```

```bash
# Migrations now come from local mount
docker compose restart bot
```

See [Docker Migration Setup](../../developer/concepts/database/migrations.md#-docker-migration-setup) for complete details.

### Fixing Sequence Synchronization

If you encounter duplicate key violations after data restoration or manual database operations, you may need to fix PostgreSQL sequences:

```bash
# Check what would be fixed (dry run)
uv run db fix-sequences --dry-run

# Fix all sequences
uv run db fix-sequences
```

This command resets all sequences to match the maximum ID value in their respective tables, preventing duplicate key violations.

!!! tip "When to Use"
    Use `fix-sequences` after:
    - Restoring data from a backup
    - Manual database operations that bypass sequences
    - Encountering duplicate key violations on insert

### Troubleshooting

#### Migration Fails

```bash
# Check what's wrong
uv run db status

# View specific migration
uv run db show head

# Check for conflicts
uv run db check
```

#### Database Out of Sync

```bash
# Reset safely (via migrations)
uv run db reset

# Nuclear option (destroys data!)
uv run db nuke --force
uv run db push
```

#### Sequence Synchronization Issues

If you see duplicate key violations:

```bash
# Fix sequences
uv run db fix-sequences

# Verify fixes
uv run db health
```

## Adminer Web UI

Web-based database administration interface.

### Accessing Adminer

**Docker Compose users:**

Adminer is available when enabled with the adminer profile:

```bash
# With dev profile
docker compose --profile dev --profile adminer up -d

# Or just adminer (only starts adminer and postgres)
docker compose --profile adminer up -d
```

Then access it at:

```text
http://localhost:8080
```

**Auto-login** is enabled by default for development.

### Features

- Browse tables and data
- Run SQL queries
- Export/import data
- View table structure
- Edit records directly
- User-friendly interface
- Dracula theme

### Manual Login

If auto-login is disabled:

- **System:** PostgreSQL
- **Server:** bot-postgres
- **Username:** botuser
- **Password:** (from your .env)
- **Database:** botdb

### Common Tasks

#### Browse Data

1. Click database name (botdb)
2. Click table name
3. View/edit data

#### Run SQL Query

1. Click "SQL command"
2. Enter your query
3. Click "Execute"

#### Export Database

1. Click "Export"
2. Choose format (SQL, CSV)
3. Click "Export"

### Security

!!! danger "Production Warning"
    **Disable auto-login in production!**

  In `.env`:

  ```bash
  ADMINER_AUTO_LOGIN=false
  ```

!!! warning "Don't Expose Publicly"
    Adminer should only be accessible locally or via VPN/SSH tunnel.

#### SSH Tunnel

For remote access:

```bash
ssh -L 8080:localhost:8080 user@your-server
```

Then access `http://localhost:8080` on your local machine.

### Configuration

#### Change Port

In `.env`:

```bash
ADMINER_PORT=9090
```

Then access at `http://localhost:9090`

#### Disable Adminer

Stop the service or omit the adminer profile:

```bash
docker compose stop bot-adminer
```

## Related

- **[Bare Metal Installation](../install/baremetal.md)**
- **[Database CLI Reference](../../reference/cli.md)**
- **[Developer Migration Guide](../../developer/concepts/database/migrations.md)**
