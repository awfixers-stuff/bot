---
title: System Operations
tags:
  - selfhost
  - operations
icon: lucide/activity
---

# System Operations

!!! warning "Work in progress"
    This section is a work in progress. Please help us by contributing to the documentation.

Monitor, maintain, and optimize your Bot installation.

## Monitoring

Monitor Bot health and performance.

### Health Checks

#### Bot Status

```bash
# Check if running
docker compose ps bot

# Check health status
docker inspect bot --format='{{.State.Health.Status}}'
```

#### Database Health

```bash
# Via CLI
docker compose exec bot uv run db health

# Direct check
docker compose exec bot-postgres pg_isready -U botuser
```

#### Discord Connection

Check bot shows online in Discord.

### Metrics

#### Resource Usage

```bash
# Docker stats
docker stats bot bot-postgres

# System resources
htop
free -h
df -h
```

#### Bot Metrics

```text
$ping                               # API latency, uptime, system stats, bot stats
```

The ping command provides:

- API latency and uptime
- System statistics (CPU, RAM usage)
- Bot statistics (guild count, user count, sharding info, gateway intents)

### Alerting

Set up alerts for:

- Bot offline
- High error rate
- Database connection issues
- Resource exhaustion

### Optional: Sentry

Configure Sentry for automatic error tracking:

```bash
EXTERNAL_SERVICES__SENTRY_DSN=your_dsn
```

### Optional: InfluxDB

Time-series metrics:

```bash
EXTERNAL_SERVICES__INFLUXDB_URL=http://influxdb:8086
EXTERNAL_SERVICES__INFLUXDB_TOKEN=token
EXTERNAL_SERVICES__INFLUXDB_ORG=org
```

## Performance Optimization

Optimize Bot for your server size.

### Database Optimization

#### PostgreSQL Tuning

Edit postgresql.conf:

```conf
shared_buffers = 256MB              # 25% of RAM
effective_cache_size = 1GB          # 50% of RAM
work_mem = 16MB
```

### Bot Optimization

#### Resource Limits

In compose.yaml:

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
```

### Monitoring Performance

```bash
# Resource usage
docker stats bot

# Database performance
uv run db queries
```

### Scaling

For large servers (1000+ members):

- Dedicated database server
- Increase connection pool
- Monitor and optimize queries
- Consider caching strategies

## Logging

Log management and configuration.

### Log Output

Bot uses **Loguru** for structured logging.

#### Docker Compose

```bash
# View logs
docker compose logs -f bot

# Last 100 lines
docker compose logs --tail=100 bot

# Since timestamp
docker compose logs --since 2024-01-01T00:00:00 bot
```

#### Systemd

```bash
# Follow logs
sudo journalctl -u bot -f

# Last hour
sudo journalctl -u bot --since "1 hour ago"

# Search for errors
sudo journalctl -u bot | grep ERROR
```

### Log Levels

Configure via `LOG_LEVEL` or `DEBUG`:

```bash
LOG_LEVEL=INFO                       # Explicit log level
DEBUG=false                          # Debug toggle (fallback)
DEBUG=true                           # Debug toggle (development)
```

**Levels:**

- DEBUG - Detailed diagnostic info
- INFO - General operational messages
- WARNING - Warning messages
- ERROR - Error messages
- CRITICAL - Critical failures

### Log Rotation

Docker Compose includes log rotation by default:

```yaml
logging:
  driver: json-file
  options:
    max-size: "10m"
    max-file: "3"
    compress: "true"
```

## Updates

Keep your Bot installation up to date with the latest features and security patches.

### Update Methods

#### Docker Updates

##### Using Docker Compose

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart (use --profile dev or --profile production)
docker compose down
docker compose --profile dev up -d --build
```

##### Using Docker Images

```bash
# Pull latest image
docker pull bot:latest

# Stop current container
docker stop bot

# Remove old container
docker rm bot

# Start new container
docker run -d --name bot bot:latest
```

#### Bare Metal Updates

##### Manual Update

```bash
# Stop the bot
sudo systemctl stop bot

# Backup current installation
cp -r /opt/bot /opt/bot.backup.$(date +%Y%m%d)

# Pull latest changes
cd /opt/bot
git pull origin main

# Update dependencies
uv sync

# Run database migrations
uv run db push

# Start the bot
sudo systemctl start bot
```

##### Automated Update Script

```bash
#!/bin/bash
# update-bot.sh

set -e

echo "Stopping Bot..."
sudo systemctl stop bot

echo "Backing up current installation..."
sudo cp -r /opt/bot /opt/bot.backup.$(date +%Y%m%d)

echo "Updating Bot..."
cd /opt/bot
sudo -u bot git pull origin main

echo "Updating dependencies..."
sudo -u bot uv sync

echo "Running database migrations..."
sudo -u bot uv run db push

echo "Starting Bot..."
sudo systemctl start bot

echo "Update complete!"
```

### Update Types

#### Minor Updates

- Bug fixes
- Performance improvements
- New features
- Usually safe to update immediately

#### Major Updates

- Breaking changes
- Database schema changes
- Configuration changes
- Review changelog before updating

#### Security Updates

- Critical security patches
- Update immediately
- May require immediate restart

### Pre-Update Checklist

#### Backup

- [ ] Database backup
- [ ] Configuration files
- [ ] Custom modifications
- [ ] Bot data

#### Testing

- [ ] Test in development environment
- [ ] Verify compatibility
- [ ] Check breaking changes
- [ ] Review migration notes

#### Preparation

- [ ] Schedule maintenance window
- [ ] Notify users
- [ ] Prepare rollback plan
- [ ] Monitor system resources

### Database Migrations

#### Automatic Migrations

Migrations run automatically when the bot starts. Check logs if startup fails.

#### Manual Migrations

```bash
# Check migration status
uv run db status

# Apply pending migrations
uv run db push

# Rollback migration
uv run db downgrade 20231201_001
```

### Rollback Procedures

#### Docker Rollback

```bash
# Stop current container
docker compose down

# Restore previous image
docker tag bot:previous bot:latest

# Start with previous version (use --profile dev or --profile production)
docker compose --profile production up -d
```

#### Bare Metal Rollback

```bash
# Stop bot
sudo systemctl stop bot

# Restore backup
sudo rm -rf /opt/bot
sudo mv /opt/bot.backup.20231201 /opt/bot

# Restore database (if needed)
sudo -u postgres psql bot < backup.sql

# Start bot
sudo systemctl start bot
```

### Update Monitoring

#### Health Checking

```bash
# Check bot status
docker compose ps bot

# Check logs
docker compose logs --tail=100 bot

# Test commands
/ping
```

#### Monitoring Commands

```bash
# Monitor resource usage
htop

# Check disk space
df -h

# Database sequence synchronization (if needed)
uv run db fix-sequences --dry-run
```

### Troubleshooting Updates

#### Common Issues

**Bot won't start after update**:

- Check logs for errors
- Verify configuration compatibility
- Check database migrations
- Restore from backup if needed

**Database migration errors**:

- Check database connectivity
- Verify migration files
- Manual migration if needed
- Contact support for complex issues

**Performance issues**:

- Monitor resource usage
- Check for memory leaks
- Review configuration changes
- Consider rollback

### Update Schedule

#### Recommended Schedule

- **Security updates**: Immediate
- **Minor updates**: Weekly
- **Major updates**: Monthly
- **Maintenance**: Quarterly

#### Notification Setup

- Subscribe to release notifications
- Monitor GitHub releases
- Set up automated alerts
- Join community channels

## Security

Security considerations for your Bot installation.

*Security documentation in progress. Basic recommendations:*

- Keep dependencies updated
- Use strong passwords
- Limit database access
- Monitor for unusual activity
- Regular security audits

## Related

- **[Database Management](database.md)**

---

*Complete system operations guide consolidated from individual topic files.*
