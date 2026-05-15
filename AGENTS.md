# AGENTS.md

**Bot** is an all-in-one open source Discord bot for the [AWFixer Enterprising Inc](https://github.com/awfixers-stuff/bot) community.

**Stack:** Python 3.13.2+ • discord.py • PostgreSQL • SQLModel • uv • Docker

> ## Branch and Pull Request Requirement
>
> **All changes — including AI-generated changes — MUST be made in a new feature branch and submitted as a pull request.**
>
> Direct commits to `main` are strictly prohibited. Every change follows this lifecycle:
> **Create branch → Develop → Commit → Push → Open PR → Review → Merge → Delete branch**
>
> Branch naming: `<type>/<short-description>` (e.g., `feat/add-auth`, `fix/memory-leak`, `docs/update-readme`).
> See [branch naming conventions](docs/content/developer/best-practices/branch-naming.md) for all types.

## Quick reference

| Task | Command |
|------|---------|
| Install deps | `uv sync` |
| Config examples | `uv run config generate` |
| DB + migrate | `uv run db init` / `uv run db dev` |
| Quality | `uv run dev all` |
| Tests | `uv run test quick` / `uv run test all` |
| Run bot | `uv run bot start` |

## Agent rules and patterns

All project rules and agent instructions live in `.agents/`.

| File | Contents |
|------|----------|
| [.agents/setup.md](.agents/setup.md) | Setup, tech stack, and repository layout |
| [.agents/commands.md](.agents/commands.md) | CLI commands reference (dev, test, db, docs) |
| [.agents/workflow.md](.agents/workflow.md) | Workflow, Docker Compose, commits, PRs |
| [.agents/patterns.md](.agents/patterns.md) | Code standards, architecture, and domain patterns |

## Resources

- **Docs:** <https://github.com/awfixers-stuff/bot
- **Issues:** <https://github.com/awfixers-stuff/bot/issues>
- **Discord:** <https://discord.gg/gpmSjcjQxg>
- **Repo:** <https://github.com/awfixers-stuff/bot>
