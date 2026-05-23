#!/usr/bin/env python3
"""
Orchestrator Agent — Top of Hierarchy.

Entry point for human requests. Prints the EXACT command to run next
at every step. The Human copies and pastes each command.

Usage:
    ./.agents/orchestrator.py feature/CandleManager
    ./.agents/orchestrator.py feature/CandleManager --prompt drafts/my_prompt.md
    ./.agents/orchestrator.py implement/CandleManager
    ./.agents/orchestrator.py modify/RatchetStrategyRun
    ./.agents/orchestrator.py bugfix/RatchetStrategyRun
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = REPO_ROOT / ".agents"
FEATURES_DIR = REPO_ROOT / "apps" / "backend" / "app" / "features"
RUNNER = AGENTS_DIR / "runner.py"
PERSONAS_DIR = AGENTS_DIR / "personas"

KNOWN_FEATURES = {
    "BrokerAuthenticate": "broker",
    "CandleManager": "common",
    "QuotesFetch": "market",
    "OrderManager": "order",
    "HoldingsTracker": "state",
    "TradesJournal": "state",
    "TradeSettingsLoad": "state",
    "RunStateTrack": "state",
    "SymbolsLoad": "state",
    "RatchetStrategyRun": "strategy",
}

DOMAIN_KEYWORDS = {
    "auth": ("broker", "BrokerAuthenticate"),
    "candle": ("common", "CandleManager"),
    "quote": ("market", "QuotesFetch"),
    "order": ("order", "OrderManager"),
    "holding": ("state", "HoldingsTracker"),
    "trade": ("state", "TradesJournal"),
    "settings": ("state", "TradeSettingsLoad"),
    "ratchet": ("strategy", "RatchetStrategyRun"),
}

SPEC_TEMPLATE = """\
# {action} — {domain_title} Feature

## Overview

{overview}

## Input / Output

| Direction | Format | Description |
|-----------|--------|-------------|
| Input | `dict` with fields... | <!-- list fields --> |
| Output | `dict` with status key | `{{"status": "ok", ...}}` |

## Business Logic Constraints

* <!-- list invariants, rules, edge cases -->

## Error Cases

| Condition | Error | Message |
|-----------|-------|---------|
| <!-- when --> | <!-- exception type --> | <!-- message --> |

## Dependencies

* <!-- libraries, other features, config files -->

## Code Standards

All code must use type annotations per PEP 484 (function signatures + module-level variables).
"""

DEFAULT_OVERVIEW = "<!-- Orchestrator: describe what this feature does, why it exists. -->"

CODE_TEMPLATES = {
    "Schema.py": """\
from pydantic import BaseModel


class {action}Schema(BaseModel):
    pass
""",
    "Handler.py": """\
import logging

logger = logging.getLogger(__name__)


class {action}Handler:

    def execute(self, **kwargs) -> dict:
        logger.info("{action}.execute called")
        return {{"status": "ok"}}
""",
    "Controller.py": """\
import logging

from .Schema import {action}Schema
from .Handler import {action}Handler

logger = logging.getLogger(__name__)


class {action}Controller:

    def handle(self, request: dict) -> dict:
        schema = {action}Schema(**request)
        handler = {action}Handler()
        return handler.execute(**schema.model_dump())
""",
    "Tests.py": """\
import pytest

from .Handler import {action}Handler


class Test{action}Handler:

    def test_execute_returns_ok(self):
        handler = {action}Handler()
        result = handler.execute()
        assert result["status"] == "ok"
""",
}


def read_file(path: Path) -> str:
    with open(path) as f:
        return f.read()


def current_branch() -> str:
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        return result.stdout.strip()
    except Exception:
        return "(unknown)"


def read_prompt_file(prompt_path: str) -> str:
    path = REPO_ROOT / prompt_path
    if not path.exists():
        print(f"[Orchestrator] Prompt file not found: {path}", file=sys.stderr)
        sys.exit(1)
    return path.read_text().strip()


def format_spec_overview(overview: str) -> str:
    """Return the overview text, indented for the template."""
    if overview:
        # already a non-empty string from prompt file
        return overview
    return DEFAULT_OVERVIEW


def infer_domain_action(feature_name: str) -> tuple[str, str]:
    name = feature_name.strip()
    if name in KNOWN_FEATURES:
        return KNOWN_FEATURES[name], name
    lower = name.lower()
    for key, (domain, action) in DOMAIN_KEYWORDS.items():
        if key in lower:
            return domain, action
    return "general", name


def find_feature_dir(request_feature: str) -> Optional[Path]:
    lower = request_feature.lower()
    for domain_dir in FEATURES_DIR.iterdir():
        if not domain_dir.is_dir() or domain_dir.name.startswith("_"):
            continue
        for feature_dir in domain_dir.iterdir():
            if not feature_dir.is_dir() or feature_dir.name.startswith("_"):
                continue
            if feature_dir.name.lower() in lower or lower in feature_dir.name.lower():
                return feature_dir
    return None


def check_branch(action: str, prefix: str = "feature") -> None:
    branch = current_branch()
    if branch == "main" or branch.startswith("main"):
        print("=" * 60)
        print("WARNING: You are on the 'main' branch.")
        print(f"Create and switch to a {prefix} branch first:\n")
        print(f"  git checkout -b {prefix}/{action}\n")
        print("Then run this command again.")
        print("=" * 60)
        sys.exit(1)
    elif branch == "(unknown)":
        pass


def scaffold_new_feature(domain: str, action: str, overview: str = "") -> Path:
    slice_dir = FEATURES_DIR / domain / action
    overview_text = format_spec_overview(overview)
    spec = SPEC_TEMPLATE.format(
        domain_title=domain.title(),
        action=action,
        overview=overview_text,
    ).rstrip("\n")
    print(f"\n{'='*60}\nSTEP: Create the feature directory and blank files\n{'='*60}\n")
    print("Run these commands:\n")
    print(f"  mkdir -p {slice_dir}\n")
    print(f"  cat << 'SPECEOF' > {slice_dir / 'spec.md'}\n")
    print(f"{spec}\n")
    print("  SPECEOF\n")
    for fname, template in CODE_TEMPLATES.items():
        content = template.format(action=action).lstrip("\n")
        print(f"  cat << 'EOF' > {slice_dir / fname}")
        print(content)
        print("  EOF")
        print()
    print(f"  touch {slice_dir / '__init__.py'}")
    print()
    print("=" * 60)
    print("NEXT: Open the spec.md file in your editor and fill in the requirements.")
    print(f"      nano {slice_dir / 'spec.md'}")
    print()
    print("THEN RUN:")
    print(f"  ./.agents/orchestrator.py implement/{action}")
    print("=" * 60)
    return slice_dir


def amend_spec(feature_dir: Path, heading: str, instruction: str, revert_msg: str, next_instruction: str, branch_prefix: str) -> None:
    """Print spec amendment docs for modify/bugfix. Shared by both workflows."""
    spec_path = feature_dir / "spec.md"
    existing = read_file(spec_path) if spec_path.exists() else "(no spec.md found)"
    rel_path = spec_path.relative_to(REPO_ROOT)
    print(f"\n{'='*60}\n{heading} for {feature_dir.name}\n{'='*60}\n")
    print(f"Current spec.md at {spec_path}:")
    print(existing)
    print(f"\n{instruction}\n")
    print(f"  cat << 'SPECEOF' > {spec_path}")
    print(existing)
    print("  SPECEOF\n")
    print(f"{'='*60}")
    print("Verify the diff before implementing:")
    print(f"\n  git diff {rel_path}\n")
    print(f"{revert_msg}")
    print(f"  git checkout -- {rel_path}")
    print(f"  ./.agents/orchestrator.py {branch_prefix}/{feature_dir.name} --prompt drafts/clearer_prompt.md\n")
    print(f"{next_instruction}")
    print(f"  nano {spec_path}\n")
    print("THEN RUN:")
    print(f'  ./.agents/orchestrator.py implement/{feature_dir.name}')
    print(f"{'='*60}")


def run_runner(persona_key: str, target: Path, task: str, error_path: Optional[Path] = None) -> bool:
    persona_path = PERSONAS_DIR / f"{persona_key}_agent.md"
    if not persona_path.exists():
        print(f"[Orchestrator] Persona not found: {persona_path}", file=sys.stderr)
        return False

    cmd = [
        sys.executable, str(RUNNER),
        "--persona", str(persona_path),
        "--target", str(target),
        "--task", task,
        "--api",
    ]
    if error_path:
        cmd += ["--error", str(error_path)]

    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    return result.returncode == 0


def orchestrate(request: str, prompt_content: str = "") -> None:
    cmd = request.strip().split(None, 1)
    verb = cmd[0].lower() if cmd else ""
    rest = cmd[1] if len(cmd) > 1 else ""

    # Parse slash-format: feature/X, modify/X, bugfix/X, implement X
    if "/" in verb:
        prefix, action = verb.split("/", 1)
        prefix = prefix.lower()
        action = action.strip()
    else:
        prefix = verb
        action = rest.strip()

    # --- feature/X: scaffold new feature ---
    if prefix == "feature":
        domain, inferred = infer_domain_action(action)
        check_branch(inferred, "feature")
        scaffold_new_feature(domain, inferred, prompt_content)
        return

    # --- implement X: run backend agent ---
    if prefix == "implement":
        feature_name = action or rest
        feature_dir = find_feature_dir(feature_name)
        if not feature_dir:
            print(f"[Orchestrator] Feature not found: {feature_name}.")
            print(f"  First run: ./.agents/orchestrator.py feature/{feature_name}")
            return
        if not (feature_dir / "spec.md").exists():
            print(f"[Orchestrator] No spec.md found.")
            print(f"  First run: ./.agents/orchestrator.py feature/{feature_name}")
            return

        branch = current_branch()
        if branch == "main" or branch.startswith("main"):
            print("=" * 60)
            print("WARNING: You are on 'main'. Switch to a feature branch:")
            print(f"  git checkout -b feature/{feature_dir.name}")
            print("Then run this command again.")
            print("=" * 60)
            return

        # Detect branch type to tailor the runner task prompt and commit message
        if branch.startswith("bugfix/"):
            task = f"Fix bug in {feature_dir.name}: write a failing test that reproduces the defect, then patch Handler.py per the Defect Resolution section in spec.md"
            commit_type = "fix"
        elif branch.startswith("modify/"):
            task = f"Modify {feature_dir.name} per the amended spec.md"
            commit_type = "feat"
        else:
            task = f"Implement {feature_dir.name} per its spec.md"
            commit_type = "feat"

        print(f"[Orchestrator] Generating code for {feature_dir.name}...")
        ok = run_runner("backend", feature_dir, task)
        if ok:
            print(f"\n{'='*60}\nALL TESTS PASSED.\n")
            print("Run these commands to commit and push:\n")
            print(f"  git add {feature_dir}")
            print(f'  git commit -m "{commit_type}: {feature_dir.name}"')
            print(f"  git push origin {branch}\n")
            print("Then open a Pull Request on GitHub:")
            print(f"  https://github.com/pannet1/fti-holdings/pull/new/{branch}")
            print("=" * 60)
        else:
            print(f"\n{'='*60}")
            print("IMPLEMENTATION FAILED. The auto-QA loop exhausted its attempts.")
            print("Copy the error output above and tell the AI:")
            print(f'  "The auto-QA loop failed for {feature_dir.name}. Here is the output: ..."')
            print("=" * 60)
        return

    # --- modify/X: contract amendment ---
    if prefix == "modify":
        feature_name = action or rest
        feature_dir = find_feature_dir(feature_name)
        if not feature_dir:
            print(f"[Orchestrator] Feature not found: {feature_name}")
            return
        check_branch(feature_dir.name, "modify")
        amend_spec(
            feature_dir,
            heading="CONTRACT AMENDMENT",
            instruction="Review and edit the spec.md with your changes, then run these commands to overwrite it with the amended contract:",
            revert_msg="If the AI miswrote the contract, revert and re-run with a clearer prompt:",
            next_instruction="NEXT: Edit the spec.md above with your changes, run the cat command, or edit directly with your editor:",
            branch_prefix="modify",
        )
        return

    # --- bugfix/X: defect documentation ---
    if prefix == "bugfix":
        feature_name = action or rest
        feature_dir = find_feature_dir(feature_name)
        if not feature_dir:
            print(f"[Orchestrator] Feature not found: {feature_name}")
            return
        check_branch(feature_dir.name, "bugfix")
        amend_spec(
            feature_dir,
            heading="DEFECT DOCUMENTATION",
            instruction="Add a 'Defect Resolution' section to the spec.md documenting the broken logic and the specific edge case that must be addressed. Then run these commands to overwrite it with the amended contract:",
            revert_msg="If the AI miswrote the defect documentation, revert and re-run:",
            next_instruction="NEXT: Add the '## Defect Resolution' section to the spec.md above, then run the cat command, or edit directly with your editor:",
            branch_prefix="bugfix",
        )
        return

    if prefix == "deploy":
        print("=" * 60)
        print("Deploy mode: follow DEPLOYMENT.md manually.")
        print("=" * 60)
        return

    print("[Orchestrator] Unknown request.")
    print()
    print("Commands:")
    print('  scaffold  ./.agents/orchestrator.py feature/CandleManager')
    print('  scaffold  ./.agents/orchestrator.py feature/CandleManager --prompt drafts/my_prompt.md')
    print('  implement ./.agents/orchestrator.py implement/CandleManager')
    print('  modify    ./.agents/orchestrator.py modify/RatchetStrategyRun')
    print('  bugfix    ./.agents/orchestrator.py bugfix/RatchetStrategyRun')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Orchestrator Agent — decompose and dispatch feature work.",
        usage="%(prog)s feature/X [--prompt <file>]",
    )
    parser.add_argument(
        "command",
        nargs="*",
        help='e.g. feature/CandleManager / implement/CandleManager / modify/RatchetStrategyRun',
    )
    parser.add_argument(
        "--prompt", "-p",
        help="Path to a prompt file with multi-sentence feature logic (relative to repo root)",
    )
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        print()
        print("Commands:")
        print('  scaffold  ./.agents/orchestrator.py feature/CandleManager')
        print('  scaffold  ./.agents/orchestrator.py feature/CandleManager --prompt drafts/my_prompt.md')
        print('  implement ./.agents/orchestrator.py implement/CandleManager')
        print('  modify    ./.agents/orchestrator.py modify/RatchetStrategyRun')
        print('  bugfix    ./.agents/orchestrator.py bugfix/RatchetStrategyRun')
        sys.exit(1)
    return args


if __name__ == "__main__":
    args = parse_args()
    request = " ".join(args.command)
    prompt_content = read_prompt_file(args.prompt) if args.prompt else ""
    orchestrate(request, prompt_content)
