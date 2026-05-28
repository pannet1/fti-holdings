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
import difflib
import json
import os
import random
import string
import subprocess
import sys
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = REPO_ROOT / ".agents"
FEATURES_DIR = REPO_ROOT / "apps" / "backend" / "app" / "features"
FEATURES_CONFIG = AGENTS_DIR / "features.json"
RUNNER = AGENTS_DIR / "runner.py"
PERSONAS_DIR = AGENTS_DIR / "personas"
MODEL_CONFIG = AGENTS_DIR / "model_config.json"


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

ZEN_URL = "https://opencode.ai/zen/v1/chat/completions"


def _zen_session_id() -> str:
    alphabet = string.ascii_uppercase + string.ascii_lowercase + string.digits + "-_"
    return "ses_" + "".join(random.choices(alphabet, k=26))


ZEN_FALLBACKS = [
    "deepseek-v4-flash-free",
    "nemotron-3-super-free",
]


def _zen_api_key() -> str:
    return os.environ.get("OPENCODE_ZEN_KEY", "public")


def _zen_model() -> str:
    if MODEL_CONFIG.exists():
        try:
            cfg = json.loads(MODEL_CONFIG.read_text())
            return cfg.get("model", ZEN_FALLBACKS[0])
        except Exception:
            pass
    return ZEN_FALLBACKS[0]


def generate_spec_with_ai(domain: str, action: str, prompt: str) -> str | None:
    root_spec = REPO_ROOT / "SPEC.md"
    arch_blueprint = root_spec.read_text() if root_spec.exists() else ""

    system_prompt = (
        "You are a spec writer for a software project. "
        "Generate a structured feature specification in markdown.\n\n"
        "Here is the project's architectural blueprint:\n"
        + arch_blueprint +
        "\n\nUse this exact format for the feature spec:\n"
        "  # <Action> — <Domain> Feature\n"
        "  ## Overview\n"
        "  <description>\n"
        "  ## Input / Output\n"
        "  | Direction | Format | Description |\n"
        "  |-----------|--------|-------------|\n"
        "  | Input | <...> | <...> |\n"
        "  | Output | <...> | <...> |\n"
        "  ## Business Logic Constraints\n"
        "  * <rules>\n"
        "  ## Error Cases\n"
        "  | Condition | Error | Message |\n"
        "  |-----------|-------|-------------|\n"
        "  | <when> | <type> | <message> |\n"
        "  ## Dependencies\n"
        "  * <libraries, config>\n"
        "  ## Code Standards\n"
        "  All code must use type annotations per PEP 484.\n\n"
        "Output ONLY the markdown spec — no preamble, no explanation."
    )
    project_id = str(uuid.uuid4())
    api_key = _zen_api_key()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "x-opencode-project": project_id,
        "x-opencode-session": _zen_session_id(),
        "x-opencode-request": str(uuid.uuid4()),
        "x-opencode-client": "python-script",
        "User-Agent": "opencode/1.15.4",
    }
    payload = {
        "model": _zen_model(),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Feature: {action}\nDomain: {domain or '(none)'}\n\nDescription:\n{prompt}"},
        ],
        "max_tokens": 2048,
        "temperature": 0.3,
    }
    return _zen_chat(headers, payload)


def _zen_chat(headers: dict, payload: dict) -> str | None:
    fallbacks = ZEN_FALLBACKS[:]
    selected = payload["model"]
    if selected in fallbacks:
        fallbacks.remove(selected)
    fallbacks.insert(0, selected)

    for model in fallbacks:
        payload["model"] = model
        data = json.dumps(payload).encode()
        req = urllib.request.Request(ZEN_URL, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 401:
                print(f"[Orchestrator] Model '{model}' unavailable (free tier ended). Trying next...", file=sys.stderr)
                continue
            print(f"[Orchestrator] Zen API error ({model}): {e}", file=sys.stderr)
            continue
        except Exception as e:
            print(f"[Orchestrator] Zen API error ({model}): {e}", file=sys.stderr)
            continue

        try:
            msg = body["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as e:
            print(f"[Orchestrator] Model '{model}' returned unexpected response: {e}", file=sys.stderr)
            continue
        content = (msg.get("content") or msg.get("reasoning_content") or "").strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3].strip()
        if not content and model != fallbacks[-1]:
            print(f"[Orchestrator] Model '{model}' returned empty response. Trying next...", file=sys.stderr)
            continue
        if model != selected:
            MODEL_CONFIG.write_text(json.dumps({"model": model}) + "\n")
            print(f"[Orchestrator] Fallback: model config updated to '{model}'", file=sys.stderr)
        return content

    print("[Orchestrator] No working model found. Run ./.agents/select_model.py to pick one.", file=sys.stderr)
    return None


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
from typing import Any, Dict

logger = logging.getLogger(__name__)


class {action}Handler:

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        logger.info("{action}.execute called")
        return {{"status": "ok"}}
""",
    "Controller.py": """\
import logging
from typing import Any, Dict

from .Handler import {action}Handler

logger = logging.getLogger(__name__)


class {action}Controller:

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        handler = {action}Handler()
        return handler.execute(**request)
""",
    "Tests.py": """\
import pytest

from .Handler import {action}Handler


class Test{action}Handler:

    def test_execute_returns_ok(self) -> None:
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
        if lower == key or lower == action.lower():
            return domain, action
    # filesystem fallback: exact-match existing features
    for domain_dir in FEATURES_DIR.iterdir():
        if not domain_dir.is_dir() or domain_dir.name.startswith("_"):
            continue
        for feature_dir in domain_dir.iterdir():
            if not feature_dir.is_dir() or feature_dir.name.startswith("_"):
                continue
            if feature_dir.name.lower() == lower:
                return domain_dir.name, feature_dir.name
    return "", name


def resolve_feature(request_feature: str) -> Optional[Path]:
    feature_dir = find_feature_dir(request_feature)
    if feature_dir:
        return feature_dir
    return _fuzzy_suggest(request_feature)


def _fuzzy_suggest(request_feature: str) -> Optional[Path]:
    candidates: dict[str, Path] = {}
    for domain_dir in FEATURES_DIR.iterdir():
        if not domain_dir.is_dir() or domain_dir.name.startswith("_"):
            continue
        for entry in domain_dir.iterdir():
            if entry.is_dir() and not entry.name.startswith("_"):
                candidates[entry.name] = entry

    matches = difflib.get_close_matches(request_feature, list(candidates.keys()), n=3, cutoff=0.6)
    if not matches:
        return None

    print(f"[Orchestrator] No exact match for '{request_feature}'. Did you mean:")
    for i, m in enumerate(matches, 1):
        print(f"  {i}. {m}")
    print(f"  n. No, cancel")
    choice = input(f"Enter choice [1-{len(matches)} or n]: ").strip().lower()
    if choice == "n":
        return None
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(matches):
            return candidates[matches[idx]]
    except ValueError:
        pass
    return None


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

    # Filesystem scan: exact-match subdirectories OR flat feature domain dirs
    for domain_dir in FEATURES_DIR.iterdir():
        if not domain_dir.is_dir() or domain_dir.name.startswith("_"):
            continue
        # Check if domain dir itself is a flat feature matching the request
        if domain_dir.name.lower() == lower:
            if (domain_dir / "Handler.py").exists():
                return domain_dir
        # Check subdirectory features
        for entry in domain_dir.iterdir():
            if entry.is_dir() and not entry.name.startswith("_"):
                if entry.name.lower() == lower:
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


def branch_exists(name: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", name],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    return result.returncode == 0


def check_branch(action: str, prefix: str = "feature") -> str:
    branch = current_branch()

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
        if branch_exists(target):
            print(f"[Orchestrator] Branch '{target}' exists. Switching to it.")
            subprocess.run(["git", "checkout", target], cwd=str(REPO_ROOT))
        else:
            print(f"[Orchestrator] Creating branch: {target}")
            subprocess.run(["git", "checkout", "-b", target], cwd=str(REPO_ROOT), check=True)
        return target
    elif branch == "(unknown)":
        pass
    return branch


def scaffold_new_feature(domain: str, action: str, overview: str = "", no_controller: bool = False) -> Path:
    slice_dir = FEATURES_DIR / domain / action if domain else FEATURES_DIR / action
    slice_dir.mkdir(parents=True, exist_ok=True)

    if overview:
        ai_spec = generate_spec_with_ai(domain, action, overview)
        if ai_spec:
            (slice_dir / "spec.md").write_text(ai_spec)
        else:
            overview_text = format_spec_overview(overview)
            spec = SPEC_TEMPLATE.format(
                domain_title=domain.title() if domain else action,
                action=action,
                overview=overview_text,
            ).rstrip("\n")
            (slice_dir / "spec.md").write_text(spec)
            print("[Orchestrator] Zen API unavailable — using template spec.md", file=sys.stderr)
    else:
        spec = SPEC_TEMPLATE.format(
            domain_title=domain.title() if domain else action,
            action=action,
            overview=DEFAULT_OVERVIEW,
        ).rstrip("\n")
        (slice_dir / "spec.md").write_text(spec)

    for fname, template in CODE_TEMPLATES.items():
        if no_controller and fname == "Controller.py":
            continue
        content = template.format(action=action).lstrip("\n")
        (slice_dir / fname).write_text(content)

    (slice_dir / "__init__.py").touch()

    label = f"{domain}/{action}" if domain else action
    note = " (no controller)" if no_controller else ""
    print(f"\nScaffolded new feature: {label}{note}\n")
    return slice_dir


def amend_spec(feature_dir: Path, heading: str, branch_prefix: str, feature_name: str = "") -> None:
    display = feature_name or feature_dir.name
    print(f"\n{'='*60}\n{heading} for {display}")
    print(f"Spec amended. Run implement when ready:\n")
    print(f"  ./.agents/orchestrator.py implement/{display}")
    print("=" * 60)


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


def _rewrite_spec_with_ai(feature_dir: Path, change_prompt: str, section: str) -> bool:
    spec_path = feature_dir / "spec.md"
    existing = spec_path.read_text() if spec_path.exists() else ""
    heading = section.replace(" Request", "").replace(" Resolution", "")

    amendment = (
        f"\n## {heading}\n\n"
        f"{change_prompt}\n\n"
        "### Constraints\n"
        "* <!-- added by modification -->\n"
    )
    if existing:
        spec_path.write_text(existing + amendment)
    else:
        spec_path.write_text(amendment)
    print(f"[Orchestrator] spec.md amended with structured '{heading}' section")
    return True


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


def register_feature_in_json(feature_name: str, domain: str) -> None:
    features = load_features_config()
    known = features.setdefault("known_features", {})
    if feature_name not in known:
        known[feature_name] = domain
        keyword = feature_name.lower().replace("feature", "").replace("handler", "").replace("controller", "")
        keywords = features.setdefault("domain_keywords", {})
        if keyword and keyword not in keywords:
            keywords[keyword] = [domain, feature_name]
        with open(FEATURES_CONFIG, "w") as f:
            json.dump(features, f, indent=2)
        print(f"[Orchestrator] Registered '{feature_name}' -> '{domain}' in features.json")


def unregister_feature_from_json(feature_name: str, feature_dir: Optional[Path] = None) -> None:
    features = load_features_config()
    known = features.get("known_features", {})
    keywords = features.get("domain_keywords", {})

    # Match by name first, then by dir basename
    candidates = [feature_name]
    if feature_dir:
        candidates.append(feature_dir.name)
    removed = False
    for name in candidates:
        if name in known:
            del known[name]
            removed = True
            # Also remove any keyword pointing to this feature
            stale = [k for k, v in keywords.items() if len(v) >= 2 and v[1] == name]
            for k in stale:
                del keywords[k]
    if removed:
        features["known_features"] = known
        features["domain_keywords"] = keywords
        with open(FEATURES_CONFIG, "w") as f:
            json.dump(features, f, indent=2)
        print(f"[Orchestrator] Unregistered '{feature_name}' from features.json")
    return removed


def orchestrate(request: str, prompt_content: str = "", no_controller: bool = False) -> None:
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
        description = resolve_change_prompt(rest, prompt_content, action, "feature")
        domain = KNOWN_FEATURES.get(action, "")
        if not domain:
            for _key, (_dom, _act) in DOMAIN_KEYWORDS.items():
                if _key in action.lower() or _act.lower() == action.lower():
                    domain = _dom
                    break
        check_branch(action, "feature")
        scaffold_new_feature(domain, action, description, no_controller=no_controller)
        if domain:
            register_feature_in_json(action, domain)
        print("=" * 60)
        print("THEN RUN:")
        print(f"  ./.agents/orchestrator.py implement/{action}")
        print("=" * 60)
        return

    # --- implement X: run backend agent ---
    if prefix == "implement":
        user_feature_name = action or rest
        feature_dir = resolve_feature(user_feature_name)
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
            domain = feature_dir.parent.name if feature_dir.parent != FEATURES_DIR else ""
            register_feature_in_json(feature_dir.name, domain)
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
        feature_dir = resolve_feature(feature_name)
        if not feature_dir:
            print(f"[Orchestrator] Feature not found: {feature_name}")
            return
        change_prompt = resolve_change_prompt(rest, prompt_content, feature_name, "modify")
        _rewrite_spec_with_ai(feature_dir, change_prompt, "Modification Request")
        check_branch(feature_name, "modify")
        amend_spec(
            feature_dir,
            heading="CONTRACT AMENDMENT",
            branch_prefix="modify",
            feature_name=feature_name,
        )
        return

    # --- bugfix/X: defect documentation ---
    if prefix == "bugfix":
        feature_name = action or rest
        feature_dir = resolve_feature(feature_name)
        if not feature_dir:
            print(f"[Orchestrator] Feature not found: {feature_name}")
            return
        change_prompt = resolve_change_prompt(rest, prompt_content, feature_name, "bugfix")
        _rewrite_spec_with_ai(feature_dir, change_prompt, "Defect Resolution")
        check_branch(feature_name, "bugfix")
        amend_spec(
            feature_dir,
            heading="DEFECT DOCUMENTATION",
            branch_prefix="bugfix",
            feature_name=feature_name,
        )
        return

    if prefix == "delete":
        feature_name = action or rest
        feature_dir = resolve_feature(feature_name)
        branch = current_branch()
        target_branches = [f"feature/{feature_name}", f"modify/{feature_name}", f"bugfix/{feature_name}"]
        on_target = branch in target_branches
        found_any = False

        if feature_dir and feature_dir.exists():
            import shutil
            shutil.rmtree(feature_dir)
            print(f"[Orchestrator] Deleted feature directory: {feature_dir}")
            found_any = True

        unregister_feature_from_json(feature_name, feature_dir)

        subprocess.run(["git", "stash"], cwd=str(REPO_ROOT), capture_output=True)
        if on_target:
            subprocess.run(["git", "checkout", "main"], cwd=str(REPO_ROOT))
            subprocess.run(["git", "branch", "-D", branch], cwd=str(REPO_ROOT))
            print(f"[Orchestrator] Deleted branch: {branch}")
            found_any = True
        else:
            for tb in target_branches:
                if branch_exists(tb):
                    subprocess.run(["git", "branch", "-D", tb], cwd=str(REPO_ROOT))
                    print(f"[Orchestrator] Deleted branch: {tb}")
                    found_any = True

        if not found_any:
            print(f"[Orchestrator] Nothing to delete: feature '{feature_name}' not found.")

        return

    if prefix == "merge":
        feature_name = action or rest
        if not feature_name:
            branch = current_branch()
            for br_prefix in ("feature/", "modify/", "bugfix/"):
                if branch.startswith(br_prefix):
                    feature_name = branch[len(br_prefix):]
                    break
        if not feature_name:
            print("[Orchestrator] No feature name given and cannot infer from current branch.")
            return
        feature_dir = find_feature_dir(feature_name)
        if not feature_dir or not feature_dir.exists():
            print(f"[Orchestrator] Feature not found: {feature_name}")
            return
        branch = current_branch()
        if branch == "main":
            for br_prefix in ("feature/", "modify/", "bugfix/"):
                candidate = br_prefix + feature_name
                if branch_exists(candidate):
                    branch = candidate
                    print(f"[Orchestrator] Checking out {branch}...")
                    subprocess.run(["git", "checkout", branch],
                                   capture_output=True, cwd=str(REPO_ROOT))
                    break
            if branch == "main":
                print(f"[Orchestrator] No branch found for '{feature_name}'.")
                return
        if branch.startswith("bugfix/"):
            commit_type = "fix"
        else:
            commit_type = "feat"
        print(f"[Orchestrator] Staging {feature_dir}...")
        r1 = subprocess.run(["git", "add", str(feature_dir)], capture_output=True, text=True, cwd=str(REPO_ROOT))
        if r1.returncode != 0:
            print(f"[Orchestrator] git add failed: {r1.stderr.strip()}")
            return
        msg_body = f"{commit_type}: {feature_name}"
        print(f"[Orchestrator] Committing: {msg_body}")
        r2 = subprocess.run(["git", "commit", "-m", msg_body], capture_output=True, text=True, cwd=str(REPO_ROOT))
        if r2.returncode != 0:
            combined = r2.stdout + r2.stderr
            if "nothing to commit" in combined:
                print("[Orchestrator] Nothing to commit — already up to date.")
            else:
                print(f"[Orchestrator] git commit failed: {r2.stderr.strip()}")
                return
        print(r2.stdout.strip())
        print(f"[Orchestrator] Pushing {branch}...")
        r3 = subprocess.run(["git", "push", "origin", branch], capture_output=True, text=True, cwd=str(REPO_ROOT))
        if r3.returncode != 0:
            print(f"[Orchestrator] git push failed: {r3.stderr.strip()}")
            return
        print(r3.stdout.strip())
        print(f"[Orchestrator] Merging {branch} into main...")
        r4 = subprocess.run(["git", "checkout", "main"], capture_output=True, text=True, cwd=str(REPO_ROOT))
        if r4.returncode != 0:
            print(f"[Orchestrator] git checkout main failed: {r4.stderr.strip()}")
            return
        r5 = subprocess.run(["git", "merge", branch], capture_output=True, text=True, cwd=str(REPO_ROOT))
        if r5.returncode != 0:
            print(f"[Orchestrator] git merge failed: {r5.stderr.strip()}")
            return
        print(r5.stdout.strip())
        r6 = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True, cwd=str(REPO_ROOT))
        if r6.returncode != 0:
            print(f"[Orchestrator] git push main failed: {r6.stderr.strip()}")
            return
        print(f"[Orchestrator] Deleting remote branch {branch}...")
        subprocess.run(["git", "push", "origin", "--delete", branch],
                       capture_output=True, cwd=str(REPO_ROOT))
        print(f"[Orchestrator] Deleting local branch {branch}...")
        subprocess.run(["git", "branch", "-D", branch],
                       capture_output=True, cwd=str(REPO_ROOT))
        print(f"[Orchestrator] Done. {feature_name} merged to main.")
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
    parser.add_argument(
        "--model", "-m",
        help="Override Zen API model for this run (e.g. --model claude-sonnet-4-5)",
    )
    parser.add_argument(
        "--no-controller", action="store_true",
        help="Skip Controller.py generation (for background workers)",
    )
    args = parser.parse_args()
    if args.model:
        MODEL_CONFIG.write_text(json.dumps({"model": args.model}) + "\n")
        print(f"[Orchestrator] Model set to: {args.model}\n")
    if not args.command:
        parser.print_help()
        print()
        print("Commands:")
        print('  scaffold  ./.agents/orchestrator.py feature/ManageCandle')
        print('  scaffold  ./.agents/orchestrator.py feature/ManageCandle --prompt drafts/my_prompt.md')
        print('  implement ./.agents/orchestrator.py implement/ManageCandle')
        print('  modify    ./.agents/orchestrator.py modify/RunRatchetStrategy')
        print('  bugfix    ./.agents/orchestrator.py bugfix/RunRatchetStrategy')
        print('  merge     ./.agents/orchestrator.py merge/ManageCandle')
        print('  delete    ./.agents/orchestrator.py delete/HelloWorld')
        sys.exit(1)
    return args


if __name__ == "__main__":
    args = parse_args()
    request = " ".join(args.command)
    prompt_content = ""
    if args.prompt:
        path = Path(args.prompt)
        if path.suffix == ".md" and path.exists():
            prompt_content = path.read_text().strip()
        else:
            prompt_content = args.prompt.strip()
    orchestrate(request, prompt_content, no_controller=args.no_controller)
