#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
uv run --directory "$ROOT/apps/backend" python -c "
from app.features.state.GenerateReport.Controller import generate_report
print(generate_report(data_dir='$ROOT/data', paper=True))
"