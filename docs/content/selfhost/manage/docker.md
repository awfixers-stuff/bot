---
title: Docker Operations
tags:
  - selfhost
  - operations
  - docker
icon: lucide/container
---

# Docker Operations

Detailed guide for managing and operating Bot Docker containers.

## Service Management

### View Logs

```bash
# Follow all logs
docker compose logs -f

# Follow Bot logs only
docker compose logs -f bot

# Last 100 lines
docker compose logs --tail=100 bot

# Since timestamp
docker compose logs --since "1 hour ago" bot

# Filter logs
docker compose logs bot | grep -i "error\|warning"
```

### Start Services

```bash
# Start all services (use --profile dev or --profile production)
docker compose --profile dev up -d

# Start specific service (use --profile dev or --profile production)
docker compose --profile dev up -d bot

# Start with build
docker compose --profile dev up -d --build
```

### Stop Services

```bash
# Stop all services
docker compose down

# Stop services (keep volumes)
docker compose stop

# Stop and remove volumes (⚠️ deletes database)
docker compose down -v
```

### Restart Services

```bash
# Restart all services
docker compose restart

# Restart specific service
docker compose restart bot

# Restart with recreation (use --profile dev or --profile production)
docker compose --profile dev up -d --force-recreate bot
```

### Check Status

```bash
# View running containers
docker compose ps

# View detailed status
docker compose ps -a

# Check service health
docker compose ps --format json | jq '.[] | {name: .Name, status: .State, health: .Health}'

# View resource usage
docker stats bot bot-postgres
```

## Adminer (Database Management)

Adminer provides a web-based database management interface for PostgreSQL.

### Accessing Adminer

Access Adminer at `http://localhost:8080`:

- **System**: PostgreSQL
- **Server**: `bot-postgres`
- **Username**: Value from `POSTGRES_USER` (default: `botuser`)
- **Password**: Value from `POSTGRES_PASSWORD`
- **Database**: Value from `POSTGRES_DB` (default: `botdb`)

### Configuration

To change Adminer port:

```env
ADMINER_PORT=9000
```

To disable Adminer, omit `--profile adminer`. To enable it with production or dev:

```bash
docker compose --profile production --profile adminer up -d
docker compose --profile dev --profile adminer up -d
```

### Using Adminer

**Common operations:**

1. **Browse tables**: Click on database name → Select table
2. **Run SQL queries**: Click "SQL command" → Enter query → Execute
3. **Export data**: Navigate to table → Click "Export" → Select format (SQL, CSV, etc.)
4. **Import data**: Click "Import" → Select file → Execute

## Backup and Restore

### Backup Database

**Using pg_dump (recommended):**

```bash
# Create backup with timestamp
docker compose exec bot-postgres pg_dump -U botuser botdb > backup_$(date +%Y%m%d_%H%M%S).sql

# Create backup with custom format (smaller, faster)
docker compose exec bot-postgres pg_dump -U botuser -Fc botdb > backup_$(date +%Y%m%d).dump

# Compressed backup
docker compose exec bot-postgres pg_dump -U botuser botdb | gzip > backup_$(date +%Y%m%d).sql.gz
```

**Using Adminer:**

1. Navigate to `http://localhost:8080`
2. Select database
3. Click "Export" → Choose format (SQL recommended)
4. Click "Save output"

### Restore Database

**From SQL file:**

```bash
# Restore from backup
docker compose exec -T bot-postgres psql -U botuser -d botdb < backup_20240101.sql

# Restore with error checking
docker compose exec -T bot-postgres psql -U botuser -d botdb -v ON_ERROR_STOP=1 < backup_20240101.sql
```

**From custom format:**

```bash
docker compose exec -T bot-postgres pg_restore -U botuser -d botdb < backup_20240101.dump
```

**Using Adminer:**

1. Navigate to `http://localhost:8080`
2. Select database
3. Click "SQL command"
4. Paste SQL content or upload file
5. Click "Execute"

### Backup Volumes

**List volumes:**

```bash
docker volume ls | grep bot
```

**Backup volume:**

```bash
# Backup PostgreSQL data volume (using lightweight utility container)
docker run --rm \
  -v bot_postgres_data:/data \
  -v $(pwd):/backup \
  alpine:latest tar czf /backup/postgres_backup_$(date +%Y%m%d).tar.gz -C /data .

# Backup all volumes (using lightweight utility container)
docker run --rm \
  -v bot_postgres_data:/data \
  -v bot_cache:/cache \
  -v bot_temp:/temp \
  -v bot_user_home:/home \
  -v $(pwd):/backup \
  alpine:latest sh -c "tar czf /backup/volumes_backup_$(date +%Y%m%d).tar.gz /data /cache /temp /home"
```

!!! note "Utility Container"
    The `alpine:latest` image is used here as a lightweight utility container for running tar commands. It's not related to the Bot application image, which uses `python:3.13.11-slim` (Debian-based).

**Restore volume:**

```bash
# Stop services first
docker compose down

# Restore volume (using lightweight utility container)
docker run --rm \
  -v bot_postgres_data:/data \
  -v $(pwd):/backup \
  alpine:latest sh -c "cd /data && tar xzf /backup/postgres_backup_20240101.tar.gz"

# Start services (use --profile dev or --profile production)
docker compose --profile production up -d
```

## Monitoring

### Container Health

```bash
# Check health status
docker inspect bot --format='{{json .State.Health}}' | jq

# Check all health statuses
docker compose ps --format json | jq '.[] | {name: .Name, health: .Health}'
```

### Resource Usage

```bash
# Real-time stats
docker stats bot bot-postgres

# Container details
docker compose exec bot ps aux
docker compose exec bot df -h

# Memory usage
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"
```

### Database Health

```bash
# Via CLI
docker compose exec bot uv run db health

# Direct PostgreSQL check
docker compose exec bot-postgres pg_isready -U botuser

# Check database size
docker compose exec bot-postgres psql -U botuser -d botdb -c "SELECT pg_size_pretty(pg_database_size('botdb'));"

# Check table sizes
docker compose exec bot-postgres psql -U botuser -d botdb -c "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size FROM pg_tables WHERE schemaname = 'public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

## Maintenance

### Clean Up

```bash
# Remove stopped containers
docker compose rm

# Remove unused images
docker image prune

# Remove unused volumes (⚠️ careful!)
docker volume prune

# Full cleanup (removes unused containers, networks, images, build cache)
docker system prune -a
```

### Update Images

```bash
# Pull latest images
docker compose pull

# Rebuild and restart (use --profile dev or --profile production)
docker compose --profile dev up -d --build

# Update specific service
docker compose pull bot
docker compose --profile dev up -d bot
```

### View Container Information

```bash
# Inspect container
docker inspect bot

# View container logs location
docker inspect bot --format='{{.LogPath}}'

# View network configuration
docker network inspect bot_default

# View volume details
docker volume inspect bot_postgres_data
```

## Related Documentation

- **[Docker Installation](../install/docker.md)** - Initial setup and installation
- **[Production Deployment](../../reference/docker-production.md)** - Production deployment guide
- **[Docker Troubleshooting](../../support/troubleshooting/docker.md)** - Common issues and solutions
