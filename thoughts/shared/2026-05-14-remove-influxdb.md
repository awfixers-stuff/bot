# Plan: Remove InfluxDB

**Date:** 2026-05-14
**Status:** Draft

## Overview

Remove all InfluxDB-related code, configuration, and dependencies from Tux.
InfluxDB is a time-series database used only for optional analytics dashboards (guild stats,
snippet counts, AFK counts, case counts). It has zero impact on bot functionality.

## Files to Change

### 1. Delete: `src/tux/modules/features/influxdblogger.py`
- Entire file — the `InfluxLogger` cog (207 lines)
- No other file imports this module or references `InfluxLogger`

### 2. Edit: `pyproject.toml`
- Remove `"influxdb-client>=1.48.0"` from `[project]` dependencies (line 19)
- Remove `"types-influxdb-client>=1.45.0.20241221"` from `[dependency-groups] types` (line 138)

### 3. Edit: `src/tux/shared/config/models.py`
- Remove three fields from the `ExternalServices` model:
  - `INFLUXDB_TOKEN` (lines 429-436)
  - `INFLUXDB_URL` (lines 437-444)
  - `INFLUXDB_ORG` (lines 445-452)

### 4. Edit: `src/tux/core/logging.py`
- Remove `"influxdb_client"` from `INTERCEPTED_LIBRARIES` list (line 62)
- Remove `"influxdb_client": logging.NOTSET` from `THIRD_PARTY_LOG_LEVELS` dict (line 136)

### 5. Edit: `.env.example`
- Remove the three INFLUXDB environment variables:
  - `EXTERNAL_SERVICES__INFLUXDB_TOKEN=...`
  - `EXTERNAL_SERVICES__INFLUXDB_URL=...`
  - `EXTERNAL_SERVICES__INFLUXDB_ORG=...`

## What Will NOT Change

- `src/tux/shared/config/models.py` — all other fields in `ExternalServices` remain (Sentry, GitHub, Mailcow, Wolfram)
- `uv.lock` — will be updated automatically by `uv sync` (no manual edit needed)
- `influxdb-client` package remains cachable in uv's cache but won't be installed since it's removed from pyproject.toml
- No tests are affected — there are zero InfluxDB-related tests in the repo

## Verification Steps

1. `uv sync` — ensure no errors resolving dependencies after removing influxdb-client
2. `uv run dev all` — run linting (ruff) and type checking (basedpyright)
3. `uv run test all` — ensure all existing tests still pass

## Post-Merge Cleanup

- `rm -rf .venv` + `uv sync` on each developer machine to fully remove the influxdb-client package from local virtualenvs
