#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
FEATURES_JSON=".agents/features.json"
BACKEND_DIR="apps/backend"
FEATURES_REL="app/features"

echo "=========================================="
echo " QA Test Runner — Full Feature Regression"
echo "=========================================="
echo ""

TOTAL=0
PASSED=0
FAILED=0
FAILED_NAMES=""

while IFS=$'\t' read -r name domain; do
    test_rel="$FEATURES_REL/$domain/$name/Tests.py"
    test_abs="$BACKEND_DIR/$test_rel"
    if [ ! -f "$test_abs" ]; then
        continue
    fi
    TOTAL=$((TOTAL + 1))
    printf "  %-30s " "$domain/$name"
    output=$(uv run --directory "$BACKEND_DIR" python -m pytest "$test_rel" -q 2>&1) && {
        echo "PASS"
        PASSED=$((PASSED + 1))
    } || {
        last=$(echo "$output" | tail -1)
        echo "FAIL ($last)"
        FAILED=$((FAILED + 1))
        FAILED_NAMES="$FAILED_NAMES    $domain/$name ($last)"$'\n'
    }
done < <(python3 -c "
import json
with open('$FEATURES_JSON') as f:
    data = json.load(f)
for name, domain in data['known_features'].items():
    print(f'{name}\t{domain}')
")

echo ""
echo "=========================================="
echo " Summary: $PASSED/$TOTAL passed"
if [ "$FAILED" -gt 0 ]; then
    echo " Failures:"
    echo -n "$FAILED_NAMES"
fi
echo "=========================================="
echo ""

echo ""
echo "--- Full Suite Regression (all features) ---"
full_output=$(uv run --directory "$BACKEND_DIR" python -m pytest "$FEATURES_REL" -q 2>&1) || true
full_total=$(echo "$full_output" | tail -1 | grep -oP '\d+(?= passed)' || echo "0")
full_failed=$(echo "$full_output" | tail -1 | grep -oP '\d+(?= failed)' || echo "0")
echo "  Total: $full_total passed, $full_failed failed"
echo ""
