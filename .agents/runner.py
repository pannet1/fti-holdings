"""
Runner Engine — generic sub-agent executor.

Pipes persona + spec.md + existing code to the Zen API,
extracts Python code blocks from the response, writes them to disk,
and runs pytest in an auto-correction loop.

Usage:
    python .agents/runner.py \
        --persona .agents/personas/backend_agent.md \
        --target apps/backend/app/features/broker/AuthenticateBroker/ \
        --task "Implement the feature per spec.md" \
        --api

    python .agents/runner.py \
        --persona .agents/personas/qa_agent.md \
        --target apps/backend/app/features/strategy/RunRatchetStrategy/ \
        --error /tmp/pytest_errors.txt \
        --api
"""

import argparse
import json
import random
import re
import string
import subprocess
import sys
import urllib.request
import uuid
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = REPO_ROOT / ".agents"
MODEL_CONFIG = AGENTS_DIR / "model_config.json"
MAX_QA_LOOPS = 3

ZEN_URL = "https://opencode.ai/zen/v1/chat/completions"

ZEN_FALLBACKS = [
    "deepseek-v4-flash-free",
    "nemotron-3-super-free",
    "minimax-m2.5-free",
    "qwen3.6-plus-free",
]


def _zen_session_id() -> str:
    alphabet = string.ascii_uppercase + string.ascii_lowercase + string.digits + "-_"
    return "ses_" + "".join(random.choices(alphabet, k=26))


def _zen_model() -> str:
    if MODEL_CONFIG.exists():
        try:
            cfg = json.loads(MODEL_CONFIG.read_text())
            return cfg.get("model", ZEN_FALLBACKS[0])
        except Exception:
            pass
    return ZEN_FALLBACKS[0]


def _zen_chat(prompt: str) -> str | None:
    fallbacks = ZEN_FALLBACKS[:]
    selected = _zen_model()
    if selected in fallbacks:
        fallbacks.remove(selected)
    fallbacks.insert(0, selected)

    project_id = str(uuid.uuid4())
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer public",
        "x-opencode-project": project_id,
        "x-opencode-session": _zen_session_id(),
        "x-opencode-request": str(uuid.uuid4()),
        "x-opencode-client": "python-script",
        "User-Agent": "opencode/1.15.4",
    }

    for model in fallbacks:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4096,
            "temperature": 0.3,
        }
        data = json.dumps(payload).encode()
        req = urllib.request.Request(ZEN_URL, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 401:
                print(f"[Runner] Model '{model}' unavailable (free tier ended). Trying next...", file=sys.stderr)
                continue
            print(f"[Runner] Zen API error ({model}): {e}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"[Runner] Zen API error ({model}): {e}", file=sys.stderr)
            return None

        content = body["choices"][0]["message"]["content"].strip()
        if not content and model != fallbacks[-1]:
            print(f"[Runner] Model '{model}' returned empty response. Trying next...", file=sys.stderr)
            continue
        if model != selected:
            MODEL_CONFIG.write_text(json.dumps({"model": model}) + "\n")
            print(f"[Runner] Fallback: model config updated to '{model}'", file=sys.stderr)
        return content

    print("[Runner] No working model found. Run ./.agents/select_model.py to pick one.", file=sys.stderr)
    return None


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


def call_llm(prompt: str) -> str:
    response = _zen_chat(prompt)
    if response is None:
        print(f"[Runner] LLM call failed.", file=sys.stderr)
        sys.exit(1)
    return response


def extract_code_blocks(text: str) -> dict[str, str]:
    files: dict[str, str] = {}

    # Pattern 1: ### filename\n```python ... ```
    pattern1 = re.compile(
        r'^###\s+(\S+)\s*\n```python\n(.*?)```',
        re.MULTILINE | re.DOTALL
    )
    for match in pattern1.finditer(text):
        fname = match.group(1)
        code = match.group(2).strip()
        if fname and code:
            files[fname] = code

    # Pattern 2: ## `path/to/filename` ... ```python ... ```
    pattern2 = re.compile(
        r'^##\s+`[^`]+/(\S+)`\s*\n.*?```python\n(.*?)```',
        re.MULTILINE | re.DOTALL
    )
    for match in pattern2.finditer(text):
        fname = match.group(1)
        code = match.group(2).strip()
        if fname and code and fname not in files:
            files[fname] = code

    # Pattern 3: any ```python ... ``` block preceded by a filename somewhere nearby
    if not files:
        blocks = re.split(r'```(?:python)?\n', text)
        for i in range(1, len(blocks), 2):
            code = blocks[i].strip()
            if code.endswith("```"):
                code = code[:-3].strip()
            if not code:
                continue
            before = blocks[i - 1]
            candidates = re.findall(r'(\w+\.py)', before)
            if candidates:
                files[candidates[-1]] = code

    return files


def write_code_blocks(files: dict[str, str], target: Path) -> list[Path]:
    written: list[Path] = []
    expected = {"Schema.py", "Handler.py", "Controller.py", "Tests.py"}
    produced = set()

    for fname, code in files.items():
        path = target / fname
        write_file(path, code + "\n")
        written.append(path)
        produced.add(fname)

    # Delete files the AI intentionally omitted from the slice
    for fname in expected:
        if fname not in produced:
            path = target / fname
            if path.exists():
                path.unlink()
                written.append(path)
                print(f"[Runner] Deleted {fname} (absent from AI output)")

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
    print(f"[Runner] Calling LLM (Backend Agent)...")
    response = call_llm(prompt)
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
        qa_response = call_llm(qa_prompt)
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
