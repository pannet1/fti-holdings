"""
Audit Python files for code standard violations.

Usage: python3 .agents/audit_standards.py <directory>
Scans all *.py files in the given directory tree.
Returns exit 0 if clean, 1 if violations found; violations printed to stdout.
"""
import ast
import re
import sys
from pathlib import Path


def audit_file(path: Path) -> list[str]:
    violations: list[str] = []
    text = path.read_text()
    lines = text.splitlines()

    # Gate 0a: comments (skip shebang, encoding, noqa)
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#") and "noqa" not in stripped and "# -*-" not in stripped and "#!/" not in stripped:
            violations.append(f"{path.name}:{i}: comment found")
            break

    # Gate 0b: print() (not inside logger calls)
    if "print(" in text:
        for i, line in enumerate(lines, 1):
            s = line.strip()
            if "print(" in s and "logger" not in s and not s.startswith("#"):
                violations.append(f"{path.name}:{i}: print() found")

    # Gate 1a + 1b: type annotations via AST
    try:
        tree = ast.parse(text)
    except SyntaxError:
        violations.append(f"{path.name}: syntax error")
        return violations

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fn = node.name
            if fn.startswith("test_"):
                continue
            has_return = node.returns is not None
            if not has_return:
                violations.append(f"{path.name}: {fn} missing return type")

            # Check params for Optional
            for arg in node.args.args + node.args.kwonlyargs:
                if arg.annotation is None:
                    continue
                # Default None but annotation is not Optional[T]
                for default in node.args.defaults + node.args.kw_defaults:
                    if default is None or isinstance(default, ast.Constant) and default.value is None:
                        pass
                # Check default None with non-Optional annotation
                defaults_map = {}
                all_args = node.args.args + node.args.kwonlyargs
                all_defaults = list(node.args.defaults) + list(node.args.kw_defaults or [])
                # Map defaults to args (right-aligned for positional)
                for a, d in zip(reversed(all_args), reversed(all_defaults)):
                    if isinstance(d, ast.Constant) and d.value is None and a.arg in [x.arg for x in all_args]:
                        arg_name = a.arg
                        ann = a.annotation
                        if ann and isinstance(ann, ast.Name) and ann.id != "Optional":
                            violations.append(f"{path.name}: {fn} param {arg_name} has bare {ann.id} = None (use Optional)")
                        elif ann and isinstance(ann, ast.Subscript):
                            pass  # Optional[T] is a Subscript
                        elif ann and isinstance(ann, ast.Attribute):
                            path_str = ast.dump(ann)
                            if ann.attr not in ("Optional", "None"):
                                violations.append(f"{path.name}: {fn} param {arg_name} has bare {ann.attr} = None (use Optional)")

    return violations


def main() -> int:
    target = Path(sys.argv[1])
    if not target.is_dir():
        print(f"Not a directory: {target}", file=sys.stderr)
        return 1

    any_violations = False
    seen: set[str] = set()
    for py_file in sorted(target.rglob("*.py")):
        if "__pycache__" in str(py_file):
            continue
        rel = py_file.relative_to(target)
        violations = audit_file(py_file)
        for v in violations:
            # Deduplicate
            key = f"{rel}:{v.split(':')[1]}"
            if key in seen:
                continue
            seen.add(key)
            print(f"    {rel}: {v.split(': ')[-1]}")
            any_violations = True

    return 1 if any_violations else 0


if __name__ == "__main__":
    sys.exit(main())
