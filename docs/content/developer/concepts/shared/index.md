---
title: Shared
tags:
  - developer-guide
  - concepts
  - shared
icon: lucide/share-2
---

# Shared

!!! warning "Work in progress"
    This section is a work in progress. Please help us by contributing to the documentation.

This section contains concepts that are shared across the codebase.

## Code layout

The `src/bot/shared/` package holds cross-cutting utilities:

- **`exceptions/`** — Bot-specific exception hierarchy; import public types from
  `bot.shared.exceptions` (not a single `exceptions.py` module).
- **`asyncio_gather.py`** — Helpers for interpreting results from
  `asyncio.gather(..., return_exceptions=True)`.
- **`config/`** — Pydantic settings and configuration models.
- **`constants.py`** — Shared constants.

Database-layer helpers that pair with gather patterns live under
`src/bot/database/gather_results.py`. For usage patterns, see
[Error handling best practices](../../best-practices/error-handling.md).

<!-- AUTO_INDEX_START -->
