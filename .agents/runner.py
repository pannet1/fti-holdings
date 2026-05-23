"""
Runner Engine — generic sub-agent executor.

Pipes persona + spec.md + existing code to `opencode run --format json`,
extracts Python code blocks from the response, writes them to disk,
and runs pytest in an auto-correction loop.

Usage:
    python .agents/runner.py \\
        --persona .agents/personas/backend_agent.md \\
        --target apps/backend/app/features/broker/AuthenticateBroker/ \\
        --task "Implement the feature per spec.md" \\
        --api

    python .agents/runner.py \\
        --persona .agents/personas/qa_agent.md \\
        --target apps/backend/app/features/strategy/RunRatchetStrategy/ \\
        --error /tmp/pytest_errors.txt \\
        --api
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
MAX_QA_LOOPS = 3


def read_file(path: Path) -> str:
    with open(path) as f:
        return f.read()


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


def collect_target_files(target: Path) -> dict:
    files = {}
    for fname in ["spec.md", "Schema.py", "Handler.py", "Controller.py", "Tests.py"]:
        path = target / fname
        if path.exists():
            files[fname] = read_file(path)
    return files


def build_prompt(persona: str, target: Path, target_files: dict, task: str, error: str) -> str:
    parts: list[str] = []
    parts.append(persona)
    parts.append("")
    parts.append(f"## Target Directory\n{target}")
    parts.append("")
    spec = target_files.get("spec.md", "")
    if spec:
        parts.append("## Specification (spec.md)\n" + spec)
        parts.append("")
    for fname in ["Schema.py", "Handler.py", "Controller.py", "Tests.py"]:
        content = target_files.get(fname, "")
        if content:
            parts.append(f"## Existing: {fname}\n{content}")
            parts.append("")
    if error:
        parts.append("## Error / Test Failure\n```\n" + error + "\n```")
        parts.append("")
    parts.append("## Task\n" + task)
    parts.append("")
    parts.append(
        "## Output Format\n"
        "For each file you generate or modify, respond with a fenced code block "
        "preceded by a line `### <filename>`.\n"
        "Example:\n"
        "### Handler.py\n"
        "```python\n"
        "...\n"
        "```"
    )
    return "\n".join(parts)


def call_opencode(prompt: str) -> str:
    result = subprocess.run(
        ["opencode", "run", "--format", "json", "--dangerously-skip-permissions"],
        input=prompt,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=600,
    )
    if result.returncode != 0:
        print(f"[Runner] opencode run failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    texts: list[str] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
            if ev.get("type") == "text":
                texts.append(ev["part"]["text"])
        except json.JSONDecodeError:
            continue
    return "".join(texts)


def extract_code_blocks(text: str) -> dict[str, str]:
    files: dict[str, str] = {}
    pattern = re.compile(
        r'^###\s+(\S+)\s*\n'
        r'```python\n'
        r'(.*?)'
        r'```',
        re.MULTILINE | re.DOTALL
    )
    for match in pattern.finditer(text):
        fname = match.group(1)
        code = match.group(2).strip()
        if fname and code:
            files[fname] = code
    return files


def write_code_blocks(files: dict[str, str], target: Path) -> list[Path]:
    written: list[Path] = []
    for fname, code in files.items():
        path = target / fname
        write_file(path, code + "\n")
        written.append(path)
    return written


def run_pytest(test_path: Path) -> tuple[bool, str]:
    result = subprocess.run(
        ["uv", "run", "pytest", str(test_path), "--tb=long", "-v"],
        capture_output=True, text=True, cwd=str(REPO_ROOT / "apps" / "backend"),
        timeout=120,
    )
    passed = result.returncode == 0
    output = result.stdout + "\n" + result.stderr
    return passed, output


def auto_backend(target: Path, prompt: str) -> bool:
    test_file = target / "Tests.py"
    if test_file.exists():
        passed, output = run_pytest(test_file)
        if passed:
            print(f"[Runner] Tests already passing. Skipping opencode call.")
            return True
        print(f"[Runner] Existing tests failing. Will re-implement.")

    print(f"[Runner] Calling opencode (Backend Agent)...")
    response = call_opencode(prompt)
    files = extract_code_blocks(response)
    if not files:
        print(f"[Runner] No code blocks found in LLM response.", file=sys.stderr)
        print(response)
        return False
    written = write_code_blocks(files, target)
    for w in written:
        print(f"[Runner] Wrote {w}")

    test_file = target / "Tests.py"
    if not test_file.exists():
        print(f"[Runner] No Tests.py found at {test_file}, skipping auto-QA.")
        return True

    passed, output = run_pytest(test_file)
    if passed:
        print(f"[Runner] All Tests Passed.")
        return True

    print(f"[Runner] Tests failed. Entering auto-QA loop...")
    qa_persona = Path(__file__).parent / "personas" / "qa_agent.md"
    if not qa_persona.exists():
        print(f"[Runner] QA persona not found at {qa_persona}", file=sys.stderr)
        return False
    qa_text = read_file(qa_persona)

    for attempt in range(1, MAX_QA_LOOPS + 1):
        target_files = collect_target_files(target)
        qa_prompt = build_prompt(qa_text, target, target_files,
                                 f"Fix the {target.name} feature. Tests are failing. Analyze and fix.",
                                 output)
        print(f"[Runner] QA attempt {attempt}/{MAX_QA_LOOPS}...")
        qa_response = call_opencode(qa_prompt)
        fix_files = extract_code_blocks(qa_response)
        if not fix_files:
            print(f"[Runner] No code blocks in QA response.", file=sys.stderr)
            continue
        write_code_blocks(fix_files, target)
        passed, output = run_pytest(test_file)
        if passed:
            print(f"[Runner] All Tests Passed after QA attempt {attempt}.")
            return True
        print(f"[Runner] QA attempt {attempt} still failing.")

    print(f"[Runner] ESCALATE: Auto-QA failed after {MAX_QA_LOOPS} attempts.")
    return False


def run() -> None:
    parser = argparse.ArgumentParser(description="Runner Engine — sub-agent executor")
    parser.add_argument("--persona", required=True, type=Path, help="Path to persona .md file")
    parser.add_argument("--target", required=True, type=Path, help="Path to target feature directory")
    parser.add_argument("--task", default="", help="Task description for the sub-agent")
    parser.add_argument("--error", type=Path, help="Path to error/traceback file (for fix loops)")
    parser.add_argument("--api", action="store_true", help="Auto mode: call opencode, write files, run tests")
    parser.add_argument("--prompt-only", action="store_true", help="Print prompt to stdout only (no API call)")
    args = parser.parse_args()

    if not args.persona.exists():
        print(f"Error: persona not found: {args.persona}", file=sys.stderr)
        sys.exit(1)
    if not args.target.is_dir():
        print(f"Error: target not found: {args.target}", file=sys.stderr)
        sys.exit(1)

    persona = read_file(args.persona)
    target_files = collect_target_files(args.target)
    task = args.task or f"Work on the feature at {args.target}"
    error = ""
    if args.error and args.error.exists():
        error = read_file(args.error)

    prompt = build_prompt(persona, args.target, target_files, task, error)

    if args.prompt_only or not args.api:
        print(prompt)
        return

    ok = auto_backend(args.target, prompt)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    run()
