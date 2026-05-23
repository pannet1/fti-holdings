# SeedConfig — Default Configuration Templates

## Overview

Provides seed/template configuration files for first-time setup. When `data/` is empty, `LoadSettings` copies these templates so the user fills them in.

## Files

- `auth.yaml` — empty credential template
- `settings.yml` — default runtime settings
- `symbols.yml` — default instrument symbol list

## Dependencies

- LoadSettingsHandler (copies templates to data/ on first run)
- LoadSymbolsHandler (reads symbols.yml directly)
