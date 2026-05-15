---
title: Reference
icon: lucide/book-open
---

# Reference

Complete reference documentation for Bot, including CLI commands, environment variables, configuration options, and technical specifications.

## Quick Reference

### [CLI Reference](cli.md)

Complete command-line interface reference for all Bot commands:

- **Bot Commands** - Start bot, version information
- **Database Commands** - Migration management, health checks, sequence fixes
- **Testing Commands** - Test execution, coverage reports
- **Development Commands** - Code quality checks, formatting, linting
- **Configuration Commands** - Generate and validate configuration

### [Environment Variables](env.md)

Auto-generated reference for all environment variables and configuration options:

- **Top-level Variables** - BOT_TOKEN, database settings, logging
- **BotInfo** - Bot name, prefix, activities
- **BotIntents** - Discord gateway intents configuration
- **UserIds** - Bot owner and sysadmin IDs
- **StatusRoles** - Status role mappings
- **XP Configuration** - Leveling system settings
- **External Services** - Sentry, GitHub, InfluxDB, and more

<Tip>
  The environment variables reference is automatically generated from the Config model. To update it, run:
  ```bash
  uv run config generate --format markdown
  ```
</Tip>

## Technical References

### [Docker Production Deployment](docker-production.md)

Reference guide for deploying Bot in production using Docker:

- Production profile configuration
- Security features and hardening
- Image tagging and versioning
- Advanced configuration options

### [Versioning System](versioning.md)

Semantic Versioning implementation and release process:

- Version detection and priority
- Git tagging conventions
- Docker image versioning
- Pre-release and build metadata

### [Coverage](coverage.md)

Test coverage information and reporting.

### [Style Guide](style-guide.md)

Code style and formatting guidelines.

### [SBOM](sbom.md)

Software Bill of Materials reference.

### [Renovate](renovate.md)

Renovate bot configuration reference.

### [Listings](listings.md)

Directory listings and structure reference.

## API Reference

### [Source Code Reference](src/bot/)

Auto-generated API documentation from source code.

## Related Documentation

- **[User Guide](../user/index.md)** - User-facing command documentation
- **[Admin Guide](../admin/index.md)** - Administrative configuration and setup
- **[Self-Hosting Guide](../selfhost/index.md)** - Self-hosting installation and management
- **[Developer Guide](../developer/index.md)** - Development setup and contribution guides
