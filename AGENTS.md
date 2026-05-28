# AGENTS.md — Agentic Workflow Constitution

**Stack**: Python (FastAPI) | **Paradigm**: Spec-Driven Development + Vertical Slice Architecture

## 1. Agent Hierarchy & Roles

### Orchestrator Agent (The Brain) — TOP OF HIERARCHY

Sole entry point for human requests. Decomposes work, dispatches to sub-agents. Sub-agents never talk to each other — only the Orchestrator talks to the human.

Decision: NEW FEATURE → dispatch Backend, MODIFICATION → dispatch Backend, BUG FIX → dispatch Backend, DEPLOYMENT → dispatch Deploy Agent.

**Rules**:
- Only the Orchestrator talks to the human. Sub-agents cannot.
- Read the relevant spec docs before dispatching
- Decompose work into atomic sub-tasks using the Task tool
- Never write code directly — decompose and dispatch only
- All sub-agent results flow back to the Orchestrator before returning to human
- All work is done in a new feature branch named by the Orchestrator
- SPEC.md must explicitly state that all code must use type annotations (PEP 484)
- Ensure sub-agents complete all tasks fully before accepting results. If a sub-agent dies or returns partial output, re-dispatch it with the remaining work. Do not proceed to the next pipeline stage until the current stage is fully delivered.

---

### Backend Sub-Agent (Reports to Orchestrator)

Write-locked to individual feature slices. Read specs, write only to target feature dir, enforce Code Standards (Section 3).



### QA / Evaluation Agent (Reports to Orchestrator)

**Responsibility**: Quality gate. Reviews code against spec.md. Analyzes tracebacks passed by the Human. Never executes commands on the local machine.

**Pipeline**:
```
[Code Agent completes] → [Human runs tests] → [Human passes results to QA Agent via --error] →
  1. Spec compliance check (does code match spec?)
  2. Analyze test failure traceback
  3. Generate edge-case tests for uncovered paths
  4. Output fixed code blocks
  5. Report pass/fail → loop back to code agent on failure
```

---

### Deploy Agent (Reports to Orchestrator)

**Triggers after `merge/X`.** SSH to server, git pull, restart service, verify via logs.

---

## 2. Agentic Pipeline (Spec → Code → Eval)

### Step 1: Spec Definition (Human + Orchestrator)
Human describes feature → Orchestrator writes structured spec. **Output**: Locked-down acceptance criteria.

### Step 2: Code Generation (Backend Agent)
Reads spec, scaffolds Pydantic schemas/tests, implements logic. **Output**: Feature code + tests.

### Step 3: Evaluation Gates (QA Agent)
Spec compliance check + traceback analysis + edge-case generation. Human executes `uv run pytest`, passes failures to QA Agent via `--error`. Loops to Backend on failure. **Gate passes only when** all checks pass.

### Step 4: Merge to Main (Orchestrator)
Orchestrator runs `merge/X` to push and merge the feature branch directly: `git add → commit → push → checkout main → merge → push main → delete local+remote branch`.

---

## 3. Code Standards (Enforced by Eval Gates)

| Rule | Enforcement | Violation Action |
|------|------------|-----------------|
| **Python version:** `3.10.*` only | `.python-version` + code review | Reject gate |
| **Package manager:** `uv` only | `pyproject.toml` + review | Reject gate |
| **No pip/poetry/conda** | All deps via `uv add` or `uv sync` | Reject gate |
| **No `requirements.txt`** | All deps in `pyproject.toml` only; `uv export`-generated `requirements.txt` permitted for deployment only | Reject gate |
| **Project time library only** | Project-specific rule (see spec) | Reject gate |
| All `.py` files MUST use `from shared.logger import logging_func` (see Logging Pattern below) | Code review | Reject gate |
| Zero comments | Code review by Orchestrator | Reject gate |
| No secrets in git-tracked files | Pre-commit hook + review | Block commit |
| No emojis in text files | Code review | Reject gate |
| Unit tests for every new feature | `pytest` coverage gate | Reject gate |
| **Type annotations everywhere** (PEP 484) for all function signatures and module-level variables | Code review + mypy check | Reject gate |

---

## 4. Logging Pattern (Cross-Project Standard)

All projects use `AsyncLogger` from `toolkit.async_logger` for non-blocking async logging. The setup is done once at import time in `shared/logger.py`:

```python
from toolkit.async_logger import AsyncLogger

def async_logger():
    manager = AsyncLogger(level, log_file, use_journal=True)
    manager.start()
    return manager.get_logger_function()

logging_func = async_logger()          # module-level, runs at import
```

**How every module logs** — every `.py` file MUST use `from shared.logger import logging_func`:

```python
from shared.logger import logging_func
logger = logging_func(__name__)
```

**Why this works**: `AsyncLogger.start()` attaches a `QueueHandler` to Python's root logger. Every logger created via `logging.getLogger(__name__)` inherits the root logger's configuration — all log records flow through `AsyncLogger`'s async queue to files/journal/stdout transparently.

**Enforcement**: The Orchestrator MUST use `from shared.logger import logging_func` in all scaffolded feature templates (Handler.py, Controller.py, standalone scripts). Any new `.py` file added to the project MUST use this pattern — bare `logging.getLogger(__name__)` is no longer permitted.

**Logger init vs settings loader**: The logger reads `settings.yml` directly from disk at import time — it does NOT go through the settings handler. This avoids a circular dependency (logger needs settings, handler needs logger). The settings handler (`LoadTradeSettingsHandler`) is a separate path for the rest of the app. Two readers, one file.

**Log levels**: Python's `logging.Logger.setLevel()` accepts both strings (`"DEBUG"`, `"INFO"`) and integers (`10`, `20`). Both forms are valid in config YAML files.

| DO: | DON'T: |
|-----|--------|
| `from shared.logger import logging_func; logger = logging_func(__name__)` | `print("message")` |
| `logger.info("order placed")` | `logging.getLogger(__name__)` without shared.logger |

---

## 5. Multi-Agent Task Execution Protocol

### Entry Point
```
python .agents/orchestrator.py "<human request>"
```

### Workflow
1. **Human** starts task with natural language description
2. **Human** creates feature branch: `git checkout -b feature/X`
3. **Orchestrator** reads relevant specs, decomposes into atomic steps
4. **Orchestrator** creates task list via Task tool, dispatches to sub-agents
5. **Backend Agent** implements feature in vertical slice, creates tests
6. **QA Agent** runs evaluation gates, feeds failures back to Backend/Frontend Agent
7. **Loop** steps 5-6 until all gates pass (max 3 iterations, then escalate to human)
8. **Orchestrator** commits all work via `merge/X`

### Escalation Rules
- If an agent fails after 3 auto-correction loops → escalate to human
- If spec contradiction is found → escalate to Orchestrator
- If a change touches both backend and deploy → dispatch both in parallel
