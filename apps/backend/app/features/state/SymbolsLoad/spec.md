# SymbolsLoad — Symbol Configuration Loader Spec

## Overview

Loads instrument symbol configurations from `factory/symbols.yml` into a dictionary for strategy use.

## Flow

1. Read `factory/symbols.yml` via `toolkit.fileutils`
2. Return dictionary of symbol configs keyed by base name
3. If file missing or empty, return empty dict

## Dependencies

- `toolkit.fileutils` for YAML parsing
- `apps/backend/factory/symbols.yml` as data source

## Code Standards

All code must use type annotations per PEP 484 (function signatures + module-level variables).
