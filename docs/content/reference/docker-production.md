---
title: Docker Production Deployment
tags:
  - reference
  - docker
  - production
icon: lucide/container
---

# Docker Production Deployment

Reference guide for deploying Bot in production using Docker. The project uses a single `compose.yaml`; production mode is selected with the `production` profile.

## Production Profile

`compose.yaml` defines both development and production in one file. For production:

- **bot** (profile `production`): pre-built image, no build, security hardening
- No source bindings or hot reload
- Adminer is off unless you add `--profile adminer`

### Usage

```bash
# Deploy production (set RESTART_POLICY=unless-stopped in .env)
docker compose --profile production up -d

# Or via COMPOSE_PROFILES (https://docs.docker.com/compose/how-tos/profiles/)
COMPOSE_PROFILES=production docker compose up -d

# With specific image version
BOT_IMAGE=ghcr.io/awfixers-stuff/bot BOT_IMAGE_TAG=v1.0.0 \
  docker compose --profile production up -d

# Add Adminer for debugging
docker compose --profile production --profile adminer up -d
```

### Profiles at a glance

| Profile      | Use for                         |
|-------------|----------------------------------|
| `production`| Production app (pre-built image) |
| `dev`       | Development (build, hot reload)  |
| `adminer`   | Database UI (combine with dev or production) |

### Development vs production

| Feature            | `--profile dev`          | `--profile production`   |
|--------------------|--------------------------|---------------------------|
| App service        | bot-dev (build from source) | bot (pre-built image)   |
| Source bindings    | For watch/sync           | In image only             |
| Hot reload         | Yes with `--watch`       | No                        |
| Adminer            | Add `--profile adminer`  | Add `--profile adminer`   |
| security_opt       | No                       | no-new-privileges         |
| read_only, tmpfs   | No                       | Yes                       |
| restart            | no                       | unless-stopped            |

## Using Pre-Built Images

Bot images are published to GitHub Container Registry:

```env
# Use official image
BOT_IMAGE=ghcr.io/awfixers-stuff/bot
BOT_IMAGE_TAG=latest

# Or use specific version
BOT_IMAGE_TAG=v1.0.0
```

### Pull and verify

```bash
# Pull latest image
docker pull ghcr.io/awfixers-stuff/bot:latest

# Verify image
docker images ghcr.io/awfixers-stuff/bot

# Check image details
docker inspect ghcr.io/awfixers-stuff/bot:latest
```

## Advanced Configuration

### Custom image registry

```env
# Custom registry
BOT_IMAGE=my-registry.com/bot
BOT_IMAGE_TAG=v1.0.0

# Local build
BOT_IMAGE=bot:local
BOT_IMAGE_TAG=latest
```

### Production .env

```env
# Restart policy for postgres and consistency
RESTART_POLICY=unless-stopped

# Optional
DEBUG=false
LOG_LEVEL=INFO
MAX_STARTUP_ATTEMPTS=5
STARTUP_DELAY=10
```

### Database port mapping

Expose PostgreSQL port to host:

```env
POSTGRES_PORT=5432
```

Access from host: `postgresql://botuser:password@localhost:5432/botdb`

## Security Features

The `bot` service (production profile) applies:

### Non-root user

The container runs as `nonroot` (UID/GID 1001):

```bash
docker compose --profile production exec bot whoami
# nonroot
```

### Read-only root filesystem

```yaml
read_only: true
tmpfs:
  - /tmp:size=100m
  - /var/tmp:size=50m
```

### Security options

```yaml
security_opt:
  - no-new-privileges:true
```

### Base image

Uses `python:3.13.11-slim` with pinned digest, minimal packages, and regular security updates.

## Related documentation

- **[Docker Installation](../selfhost/install/docker.md)** - Initial setup
- **[Docker Operations](../selfhost/manage/docker.md)** - Service management
- **[Building Docker Images](../developer/guides/docker-images.md)** - Custom image builds
