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
GLOBAL_PASS=0
GLOBAL_FAIL=0
ALL_PASS_NAMES=""
ALL_FAIL_NAMES=""


audit_code_standards() {
    local dir="$1"
    local label="$2"
    local violations=""
    local f fname line stripped
    for f in "$dir"/*.py; do
        [ -f "$f" ] || continue
        fname=$(basename "$f")
        # Gate 0a: comments (skip shebang, encoding, noqa)
        while IFS= read -r line; do
            stripped="$(printf '%s' "$line" | sed 's/^[[:space:]]*//')"
            if [ -z "$stripped" ]; then
                continue
            fi
            case "$stripped" in
                "# noqa"*) ;;
                "# -*-"*) ;;
                "#!"*) ;;
                "#"*)
                    violations="$violations    $label/$fname: comment found"$'\n'
                    break
                    ;;
            esac
        done < "$f"
        # Gate 0b: print() (not inside logger calls)
        if grep -c 'print(' "$f" 2>/dev/null | grep -qv '^0$'; then
            while IFS= read -r line; do
                case "$line" in
                    *"print("*)
                        case "$line" in
                            *"logger."*) ;;
                            *"# print"*) ;;
                            *)
                                violations="$violations    $label/$fname: print() found"$'\n'
                                break
                                ;;
                        esac
                        ;;
                esac
            done < "$f"
        fi
        # Gate 1a: missing return types
        while IFS= read -r line; do
            case "$line" in
                "    def "*)
                    fnbody="${line#*def }"
                    fnname="${fnbody%%(*}"
                    case "$fnname" in
                        test_*) continue ;;
                    esac
                    case "$line" in
                        *"->"*) ;;
                        *)
                            violations="$violations    $label/$fname: $fnname missing return type"$'\n'
                            ;;
                    esac
                    ;;
            esac
        done < "$f"
        # Gate 1b: bare type = None (should be Optional)
        if grep -qE ':\s*(str|int|float|bool|dict|list|Path)\s*=\s*None' "$f" 2>/dev/null; then
            violations="$violations    $label/$fname: bare type = None (should be Optional[...])"$'\n'
        fi
    done
    [ -n "$violations" ] && printf '%s' "$violations" || true
}

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

# Code standards audit via Python AST
AUDIT_SCRIPT=".agents/audit_standards.py"
AUDIT_OUTPUT=$(python3 "$AUDIT_SCRIPT" "$BACKEND_DIR/$FEATURES_REL" 2>&1 || true)
echo "=========================================="
echo " Code Standards Violations"
echo "=========================================="
echo ""
if [ -z "$AUDIT_OUTPUT" ]; then
    echo "  (none)"
else
    echo "$AUDIT_OUTPUT"
fi

echo "=========================================="
echo " All Tests ($GLOBAL_PASS passed, $GLOBAL_FAIL failed)"
echo "=========================================="
echo ""
echo "  Passing:"
if [ -z "$ALL_PASS_NAMES" ]; then
    echo "    (none)"
else
    printf '%s' "$ALL_PASS_NAMES"
fi
echo ""
echo "  Failing:"
if [ -z "$ALL_FAIL_NAMES" ]; then
    echo "    (none)"
else
    printf '%s' "$ALL_FAIL_NAMES"
fi
echo ""
echo "=========================================="
echo " Summary: $GLOBAL_PASS passed, $GLOBAL_FAIL failed, $TOTAL feature slices"
echo "=========================================="
