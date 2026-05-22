# RunStateTrack — Run State Tracking Spec

## Overview

Manages which strategy configuration files have been executed on a given trading day.

## Flow

1. Read `run.txt` to get set of already-run strategy files
2. Scan `data/` for `.yml`/`.yaml` files (excluding `settings.yml`, `auth.yaml`)
3. Find first un-run strategy file (sorted reverse alphabetical)
4. Append to `run.txt` and return its settings
5. If all strategies run, return empty

## State File

`data/run.txt` — one strategy filename per line, appended as strategies execute.

## Dependencies

- `toolkit.fileutils` for YAML parsing
- `apps/backend/data/` for strategy YAML files

## Code Standards

All code must use type annotations per PEP 484 (function signatures + module-level variables).
