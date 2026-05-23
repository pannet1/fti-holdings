#!/usr/bin/env python3
"""
Orchestrator Agent — Top of Hierarchy.

Entry point for human requests. Prints the EXACT command to run next
at every step. The Human copies and pastes each command.

Usage:
    ./.agents/orchestrator.py feature/ManageCandle
    ./.agents/orchestrator.py feature/ManageCandle --prompt drafts/my_prompt.md
    ./.agents/orchestrator.py implement/ManageCandle
    ./.agents/orchestrator.py modify/RunRatchetStrategy
    ./.agents/orchestrator.py bugfix/RunRatchetStrategy
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = REPO_ROOT / ".agents"
FEATURES_DIR = REPO_ROOT / "apps" / "backend" / "app" / "features"
FEATURES_CONFIG = AGENTS_DIR / "features.json"
RUNNER = AGENTS_DIR / "runner.py"
PERSONAS_DIR = AGENTS_DIR / "personas"


def load_features_config() -> dict[str, Any]:
    if not FEATURES_CONFIG.exists():
        return {"known_features": {}, "domain_keywords": {}}
    with open(FEATURES_CONFIG) as f:
        return json.load(f)

FEATURES_CFG = load_features_config()
KNOWN_FEATURES: dict[str, str] = FEATURES_CFG.get("known_features", {})
DOMAIN_KEYWORDS: dict[str, tuple[str, str]] = {
    k: tuple(v) for k, v in FEATURES_CFG.get("domain_keywords", {}).items()
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
    # filesystem fallback: scan existing features
    for domain_dir in FEATURES_DIR.iterdir():
        if not domain_dir.is_dir() or domain_dir.name.startswith("_"):
            continue
        for feature_dir in domain_dir.iterdir():
            if not feature_dir.is_dir() or feature_dir.name.startswith("_"):
                continue
            if feature_dir.name.lower() == lower:
                return domain_dir.name, feature_dir.name
    return "general", name


def find_feature_dir(request_feature: str) -> Optional[Path]:
    lower = request_feature.lower()

    # Check KNOWN_FEATURES first for flat features (domain == feature dir)
    if request_feature in KNOWN_FEATURES:
        domain = KNOWN_FEATURES[request_feature]
        domain_dir = FEATURES_DIR / domain
        if domain_dir.is_dir():
            # Check if it's a flat feature (Handler.py directly in domain dir)
            if (domain_dir / "Handler.py").exists():
                return domain_dir
            # Otherwise look for a subdirectory
            feature_dir = domain_dir / request_feature
            if feature_dir.is_dir():
                return feature_dir

    # Filesystem scan: match subdirectories OR flat feature domain dirs
    for domain_dir in FEATURES_DIR.iterdir():
        if not domain_dir.is_dir() or domain_dir.name.startswith("_"):
            continue
        # Check if domain dir itself is a flat feature matching the request
        if domain_dir.name.lower() in lower or lower in domain_dir.name.lower():
            if (domain_dir / "Handler.py").exists():
                return domain_dir
        # Check subdirectory features
        for entry in domain_dir.iterdir():
            if entry.is_dir() and not entry.name.startswith("_"):
                if entry.name.lower() in lower or lower in entry.name.lower():
                    return entry
    return None


def unmerged_branches() -> list[str]:
    try:
        result = subprocess.run(
            ["git", "branch", "--no-merged", "main"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        lines = [l.strip() for l in result.stdout.split("\n") if l.strip() and not l.strip().startswith("*")]
        # filter out main itself
        return [l for l in lines if l != "main"]
    except Exception:
        return []


def check_branch(action: str, prefix: str = "feature") -> str:
    branch = current_branch()

    # Case 4: already on a feature/modify/bugfix branch — complete it first
    for p in ("feature/", "modify/", "bugfix/"):
        if branch.startswith(p):
            print("=" * 60)
            print(f"You are already on branch '{branch}'.")
            print("Complete and merge this branch first, then try again.")
            print("=" * 60)
            sys.exit(1)

    if branch == "main" or branch.startswith("main"):
        pending = unmerged_branches()
        if pending:
            print("=" * 60)
            print("BLOCKED: Unmerged branches still exist. Merge them first:")
            for b in pending:
                print(f"  {b}")
            print("=" * 60)
            sys.exit(1)
        target = f"{prefix}/{action}"
        print(f"[Orchestrator] On main with clean slate. Auto-creating branch: {target}")
        subprocess.run(["git", "checkout", "-b", target], cwd=str(REPO_ROOT))
        return target
    elif branch == "(unknown)":
        pass
    return branch


def scaffold_new_feature(domain: str, action: str, overview: str = "") -> Path:
    slice_dir = FEATURES_DIR / domain / action
    slice_dir.mkdir(parents=True, exist_ok=True)

    overview_text = format_spec_overview(overview)
    spec = SPEC_TEMPLATE.format(
        domain_title=domain.title(),
        action=action,
        overview=overview_text,
    ).rstrip("\n")
    (slice_dir / "spec.md").write_text(spec)

    for fname, template in CODE_TEMPLATES.items():
        content = template.format(action=action).lstrip("\n")
        (slice_dir / fname).write_text(content)

    (slice_dir / "__init__.py").touch()

    print(f"\nScaffolded new feature: {domain}/{action}\n")
    return slice_dir


def amend_spec(feature_dir: Path, heading: str, instruction: str, revert_msg: str, next_instruction: str, branch_prefix: str, feature_name: str = "") -> None:
    """Print spec amendment docs for modify/bugfix. Shared by both workflows."""
    display = feature_name or feature_dir.name
    spec_path = feature_dir / "spec.md"
    existing = read_file(spec_path) if spec_path.exists() else "(no spec.md found)"
    rel_path = spec_path.relative_to(REPO_ROOT)
    print(f"\n{'='*60}\n{heading} for {display}\n{'='*60}\n")
    print(f"Current spec.md at {spec_path}:")
    print(existing)
    print(f"\n{instruction}\n")
    print(f"{'='*60}")
    print("Verify the diff before implementing:")
    print(f"\n  git diff {rel_path}\n")
    print(f"{revert_msg}")
    print(f"  git checkout -- {rel_path}")
    print(f"  ./.agents/orchestrator.py {branch_prefix}/{display} --prompt drafts/clearer_prompt.md\n")
    print(f"{next_instruction}")
    print(f"  nano {spec_path}\n")
    print("THEN RUN:")
    print(f'  ./.agents/orchestrator.py implement/{display}')
    print(f"{'='*60}")


def resolve_change_prompt(rest: str, prompt_content: str, feature_name: str, prefix: str) -> str:
    if prompt_content:
        return prompt_content
    if not rest:
        print("=" * 60)
        print(f"ERROR: `{prefix}/{feature_name}` requires a prompt.")
        print()
        print("Options:")
        print(f'  ./.agents/orchestrator.py {prefix}/{feature_name} --prompt path/to/prompt.md')
        print(f'  ./.agents/orchestrator.py {prefix}/{feature_name} "describe your change in words"')
        print(f'  ./.agents/orchestrator.py {prefix}/{feature_name} path/to/prompt.md')
        print("=" * 60)
        sys.exit(1)
    path = Path(rest)
    if path.suffix == ".md":
        resolved = REPO_ROOT / rest
        if not resolved.exists():
            print(f"[Orchestrator] Prompt file not found: {resolved}")
            sys.exit(1)
        return resolved.read_text().strip()
    return rest.strip()


def _write_spec_amendment(feature_dir: Path, section: str, prompt: str) -> None:
    spec_path = feature_dir / "spec.md"
    existing = spec_path.read_text() if spec_path.exists() else ""
    amendment = f"\n## {section}\n\n{prompt}\n"
    if existing:
        spec_path.write_text(existing + amendment)
    else:
        spec_path.write_text(amendment)


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
    verb = cmd[0] if cmd else ""
    rest = cmd[1] if len(cmd) > 1 else ""

    # Parse slash-format: feature/X, modify/X, bugfix/X, implement/X
    # Lowercase only the command prefix, preserve feature name casing
    if "/" in verb:
        raw_prefix, action = verb.split("/", 1)
        prefix = raw_prefix.lower()
        action = action.strip()
    else:
        prefix = verb.lower()
        action = rest.strip()

    # --- feature/X: scaffold new feature ---
    if prefix == "feature":
        domain, inferred = infer_domain_action(action)
        check_branch(inferred, "feature")
        slice_dir = scaffold_new_feature(domain, inferred, prompt_content)
        if prompt_content:
            print(f"\n[Orchestrator] Prompt provided. Immediately implementing {inferred}...\n")
            display = inferred
            branch = current_branch()
            task = f"Implement {display} per its spec.md"
            ok = run_runner("backend", slice_dir, task)
            if ok:
                print(f"\n{'='*60}\nALL TESTS PASSED.\n")
                print("Run these commands to commit and push:\n")
                print(f"  git add {slice_dir}")
                print(f'  git commit -m "feat: implement {inferred}"')
                print(f"  git push origin {branch}\n")
                print("Then open a Pull Request on GitHub:")
                print(f"  https://github.com/pannet1/fti-holdings/pull/new/{branch}")
                print("=" * 60)
            else:
                print(f"\n{'='*60}")
                print("IMPLEMENTATION FAILED. The auto-QA loop exhausted its attempts.")
                print("Copy the error output above and tell the AI:")
                print(f'  "The auto-QA loop failed for {inferred}. Here is the output: ..."')
                print("=" * 60)
        return

    # --- implement X: run backend agent ---
    if prefix == "implement":
        user_feature_name = action or rest
        feature_dir = find_feature_dir(user_feature_name)
        if not feature_dir:
            print(f"[Orchestrator] Feature not found: {user_feature_name}.")
            print(f"  First run: ./.agents/orchestrator.py feature/{user_feature_name}")
            return
        if not (feature_dir / "spec.md").exists():
            print(f"[Orchestrator] No spec.md found.")
            print(f"  First run: ./.agents/orchestrator.py feature/{user_feature_name}")
            return

        # Prefer the KNOWN_FEATURES canonical name if available for display
        display = user_feature_name

        branch = current_branch()
        if branch == "main" or branch.startswith("main"):
            pending = unmerged_branches()
            if pending:
                print("=" * 60)
                print("BLOCKED: Unmerged branches still exist. Merge them first:")
                for b in pending:
                    print(f"  {b}")
                print("=" * 60)
                return
            target = f"feature/{display}"
            print(f"[Orchestrator] On main with clean slate. Auto-creating branch: {target}")
            subprocess.run(["git", "checkout", "-b", target], cwd=str(REPO_ROOT))
            branch = target

        # Detect branch type to tailor the runner task prompt and commit message
        if branch.startswith("bugfix/"):
            task = f"Fix bug in {display}: write a failing test that reproduces the defect, then patch Handler.py per the Defect Resolution section in spec.md"
            commit_type = "fix"
        elif branch.startswith("modify/"):
            task = f"Modify {display} per the amended spec.md"
            commit_type = "feat"
        else:
            task = f"Implement {display} per its spec.md"
            commit_type = "feat"

        print(f"[Orchestrator] Generating code for {display}...")
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
        change_prompt = resolve_change_prompt(rest, prompt_content, feature_name, "modify")
        _write_spec_amendment(feature_dir, "Modification Request", change_prompt)
        check_branch(feature_name, "modify")
        amend_spec(
            feature_dir,
            heading="CONTRACT AMENDMENT",
            instruction="Review and edit the spec.md above with your changes, or edit directly with your editor:",
            revert_msg="If the AI miswrote the contract, revert and re-run with a clearer prompt:",
            next_instruction="NEXT: Edit the spec.md above with your changes, or edit directly with your editor:",
            branch_prefix="modify",
            feature_name=feature_name,
        )
        return

    # --- bugfix/X: defect documentation ---
    if prefix == "bugfix":
        feature_name = action or rest
        feature_dir = find_feature_dir(feature_name)
        if not feature_dir:
            print(f"[Orchestrator] Feature not found: {feature_name}")
            return
        change_prompt = resolve_change_prompt(rest, prompt_content, feature_name, "bugfix")
        _write_spec_amendment(feature_dir, "Defect Resolution", change_prompt)
        check_branch(feature_name, "bugfix")
        amend_spec(
            feature_dir,
            heading="DEFECT DOCUMENTATION",
            instruction="Add a 'Defect Resolution' section to the spec.md documenting the broken logic and the specific edge case that must be addressed.",
            revert_msg="If the AI miswrote the defect documentation, revert and re-run:",
            next_instruction="NEXT: Add the '## Defect Resolution' section to the spec.md above, or edit directly with your editor:",
            branch_prefix="bugfix",
            feature_name=feature_name,
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
    print('  scaffold  ./.agents/orchestrator.py feature/ManageCandle')
    print('  scaffold  ./.agents/orchestrator.py feature/ManageCandle --prompt drafts/my_prompt.md')
    print('  implement ./.agents/orchestrator.py implement/ManageCandle')
    print('  modify    ./.agents/orchestrator.py modify/RunRatchetStrategy')
    print('  bugfix    ./.agents/orchestrator.py bugfix/RunRatchetStrategy')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Orchestrator Agent — decompose and dispatch feature work.",
        usage="%(prog)s feature/X [--prompt <file>]",
    )
    parser.add_argument(
        "command",
        nargs="*",
        help='e.g. feature/ManageCandle / implement/ManageCandle / modify/RunRatchetStrategy',
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
        print('  scaffold  ./.agents/orchestrator.py feature/ManageCandle')
        print('  scaffold  ./.agents/orchestrator.py feature/ManageCandle --prompt drafts/my_prompt.md')
        print('  implement ./.agents/orchestrator.py implement/ManageCandle')
        print('  modify    ./.agents/orchestrator.py modify/RunRatchetStrategy')
        print('  bugfix    ./.agents/orchestrator.py bugfix/RunRatchetStrategy')
        sys.exit(1)
    return args


if __name__ == "__main__":
    args = parse_args()
    request = " ".join(args.command)
    prompt_content = read_prompt_file(args.prompt) if args.prompt else ""
    orchestrate(request, prompt_content)
