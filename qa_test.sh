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
ALL_PASS_NAMES=""
ALL_FAIL_NAMES=""

GLOBAL_PASS=0
GLOBAL_FAIL=0

while IFS=$'\t' read -r name domain; do
    test_rel="$FEATURES_REL/$domain/$name/Tests.py"
    test_abs="$BACKEND_DIR/$test_rel"
    if [ ! -f "$test_abs" ]; then
        continue
    fi
    TOTAL=$((TOTAL + 1))
    echo "  [$domain/$name]"
    output=$(uv run --directory "$BACKEND_DIR" python -m pytest "$test_rel" -v 2>&1) || true
    while IFS= read -r line; do
        case "$line" in
            *" PASSED"*)
                testname="${line%% PASSED*}"
                testname="${testname##*::}"
                echo "    PASS  $testname"
                GLOBAL_PASS=$((GLOBAL_PASS + 1))
                ALL_PASS_NAMES="$ALL_PASS_NAMES      $domain/$name :: $testname"$'\n'
                ;;
            *" FAILED"*)
                testname="${line%% FAILED*}"
                testname="${testname##*::}"
                echo "    FAIL  $testname"
                GLOBAL_FAIL=$((GLOBAL_FAIL + 1))
                ALL_FAIL_NAMES="$ALL_FAIL_NAMES      $domain/$name :: $testname"$'\n'
                ;;
        esac
    done <<< "$output"
    echo ""
done < <(python3 -c "
import json
with open('$FEATURES_JSON') as f:
    data = json.load(f)
for name, domain in data['known_features'].items():
    print(f'{name}\t{domain}')
")

echo "=========================================="
echo " All Tests"
echo "=========================================="
echo ""
echo "  Passing:"
echo -n "$ALL_PASS_NAMES"
echo ""
echo "  Failing:"
if [ -z "$ALL_FAIL_NAMES" ]; then
    echo "    (none)"
else
    echo -n "$ALL_FAIL_NAMES"
fi
echo ""
echo "=========================================="
echo " Summary: $GLOBAL_PASS passed, $GLOBAL_FAIL failed, $TOTAL feature slices"
echo "=========================================="
