---
title: Database Configuration
tags:
  - selfhost
  - configuration
  - database
icon: lucide/database
---

# Database Configuration

Configure database connection settings for Bot. For installation instructions, see [Bare Metal Installation](../install/baremetal.md).

!!! tip "Quick Start"
    If you use Docker Compose, the database configures automatically. Set your `POSTGRES_PASSWORD` in `.env` and start services.

## Docker Compose Setup

The `compose.yaml` file includes a PostgreSQL service (`bot-postgres`) that uses the Alpine-based `postgres:17-alpine` image with optimized settings (256MB shared buffers, 100 max connections, UTC timezone).

!!! note "Base Images"
    The Bot application uses `python:3.13.11-slim` (Debian-based), while PostgreSQL uses `postgres:17-alpine` (Alpine-based) for a smaller database image size.

**Default connection details:**

- **Host:** `bot-postgres` (Docker network)
- **Database:** `botdb` (from `POSTGRES_DB`)
- **User:** `botuser` (from `POSTGRES_USER`)
- **Password:** From `POSTGRES_PASSWORD` environment variable
- **Port:** `5432` (configurable via `POSTGRES_PORT`)

Configure these values via environment variables in `.env`:

```env
POSTGRES_DB=botdb
POSTGRES_USER=botuser
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_PORT=5432
POSTGRES_HOST=bot-postgres
```

!!! tip "Configuration Priority"
    Environment variables override defaults. See [Environment Variables](environment.md) for full configuration options.

### Database Migrations

Migrations run automatically when Bot starts. The bot:

1. Waits for PostgreSQL to become healthy
2. Checks the current database revision
3. Applies any pending migrations
4. Starts normally

!!! tip "Migration Files"
    In Docker, migration files mount automatically from `./src/bot/database/migrations` into the container. No additional configuration needed.

For manual migration management, see [Database Management](../manage/database.md).

## Connection Configuration

You can configure Bot using two methods:

### Option 1: Individual Variables (Recommended)

Set each database parameter separately:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=botdb
POSTGRES_USER=botuser
POSTGRES_PASSWORD=your_password
```

### Option 2: Database URL Override

Use a complete connection string:

```env
# Custom database URL (overrides POSTGRES_* variables)
DATABASE_URL=postgresql://botuser:password@localhost:5432/botdb
```

!!! warning "URL Override"
    When you set `DATABASE_URL`, Bot ignores all `POSTGRES_*` variables. Use one method or the other.

!!! note "URL Format"
    Bot accepts both `postgresql://` and `postgresql+psycopg://` URL formats. When you provide individual variables, Bot constructs the URL using `postgresql+psycopg://`. When you provide a custom `DATABASE_URL`, you can use either format.

### External Database Services

Bot works with managed PostgreSQL services like AWS RDS, DigitalOcean, Railway, and Supabase. Use the `DATABASE_URL` format:

```env
# Example: AWS RDS
DATABASE_URL=postgresql://botuser:password@your-instance.region.rds.amazonaws.com:5432/botdb?sslmode=require

# Example: DigitalOcean
DATABASE_URL=postgresql://botuser:password@your-host.db.ondigitalocean.com:25060/botdb?sslmode=require
```

!!! tip "SSL Connections"
    Most managed databases require SSL. Add `?sslmode=require` to your connection URL.

## Security Best Practices

### Password Security

Generate a strong random password before first startup:

```bash
# Generate a 32-character random password
openssl rand -base64 32
```

Set it in your `.env` file:

```env
POSTGRES_PASSWORD=<paste the generated password here>
```

!!! important "Set before first startup"
    Docker Compose uses `POSTGRES_PASSWORD` to create the initial PostgreSQL superuser
    on first container startup. If you start with the default password and change it
    later in `.env`, the database will still have the old password. To change it after
    first run, connect to PostgreSQL and run
    `ALTER USER botuser WITH PASSWORD 'new_password';`,
    or delete the volume (`docker compose down -v`) and start fresh.

Follow these practices for database passwords:

- Use a randomly generated password (the `openssl` command above is sufficient)
- Never commit passwords to version control
- Rotate passwords periodically
- Consider secrets management tools (`pass`, `1Password`, cloud secrets)

!!! warning "Default Password"
    If you don't set `POSTGRES_PASSWORD`, Bot defaults to `ChangeThisToAStrongPassword123!`. This is a stronger default than many projects use, but **you should still set a strong, unique password in production**.

### Network Security

**Docker setup:**

The database is only accessible within the Docker network. You don't need to expose the port externally.

**Manual setup:**

Configure `pg_hba.conf` to restrict access, use firewall rules, and consider SSL/TLS.

**Example `pg_hba.conf` for manual setup:**

```conf
# Local connections only
host    botdb    botuser    127.0.0.1/32    scram-sha-256
```

### Backup Security

- Encrypt backups before storing
- Use secure backup storage (encrypted volumes, cloud storage)
- Test restore procedures regularly

See [Database Management](../manage/database.md) for backup strategies.

## Database Health Checks

Verify your database setup with these commands:

```bash
# Check database connection
uv run db health

# Check migration status and history
uv run db status
uv run db history

# List tables and validate schema
uv run db tables
uv run db schema

# Docker-specific checks
docker compose ps bot-postgres
docker compose logs bot-postgres
docker compose exec bot-postgres psql -U botuser -d botdb
```

## Troubleshooting

### Connection Errors

Check if PostgreSQL is running:

```bash
# Docker
docker compose ps bot-postgres

# Manual installation
sudo systemctl status postgresql
```

Verify connection and network:

```bash
# Test database connection
uv run db health

# Docker: Test network connectivity
docker compose exec bot ping bot-postgres

# Manual: Test port connectivity
telnet localhost 5432
```

**Common issues:**

- **"Authentication failed":** Verify `POSTGRES_PASSWORD` matches your database password and check that `POSTGRES_USER` exists
- **"Database does not exist":** Create the database: `docker compose exec bot-postgres psql -U postgres -c "CREATE DATABASE botdb;"`

### Migration Issues

Check migration status and view details:

```bash
# Check current status
uv run db status

# View head migration details
uv run db show head
```

Reset migrations (WARNING: destroys data):

```bash
uv run db reset
docker compose --profile dev up -d bot
```

### Performance Issues

Check for long-running queries:

```bash
# Check long-running queries
uv run db queries

# View active connections
docker compose exec bot-postgres psql -U botuser -d botdb -c "SELECT * FROM pg_stat_activity;"
```

**Optimization tips:**

- Adjust `shared_buffers` in PostgreSQL config
- Reduce `max_connections` if needed
- Monitor resource usage with `docker stats bot-postgres`

### Docker-Specific Issues

**Volume permissions:**

```bash
docker compose down
sudo chown -R 999:999 ./docker/postgres/data
docker compose up -d bot-postgres
```

**Port conflicts:**

Change `POSTGRES_PORT` in `.env` and restart services.

See [Database Management](../manage/database.md) for detailed troubleshooting.

## Adminer Web UI

Access your database through Adminer when enabled with the adminer profile:

```bash
# With dev profile
docker compose --profile dev --profile adminer up -d

# Or just adminer (only starts adminer and postgres)
docker compose --profile adminer up -d
```

**Access:** `http://localhost:8080`

Auto-login is enabled by default (development only). Credentials:

- **System:** PostgreSQL
- **Server:** `bot-postgres`
- **Username:** `botuser`
- **Password:** (from your `.env`)
- **Database:** `botdb`

!!! danger "Production Security"
    **Disable auto-login in production:**

  Add `ADMINER_AUTO_LOGIN=false` to your `.env` file. Also ensure Adminer is not publicly accessible. Use SSH tunnels or VPN.

See [Database Management](../manage/database.md) for Adminer usage details.

## Next Steps

After you configure your database:

- [Bot Token Setup](bot-token.md) - Configure Discord bot token
- [Environment Variables](environment.md) - Complete configuration
- [First Run](../install/first-run.md) - Initial setup and testing
- [Database Management](../manage/database.md) - Backups, migrations, administration
