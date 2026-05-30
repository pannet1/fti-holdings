Markdown

# Software Development Methodologies for Agentic Workflows

## 1. Introduction to Agentic Workflow Architecture

When moving from standard AI prompting to **Agentic Workflows**—where autonomous AI agents reason, plan, use tools, and loop through execution iteratively—traditional software development methodologies like standard **Agile (Scrum)** or **Waterfall** fall short.

The industry is rapidly shifting toward **Spec-Driven Development (SDD)** paired with **Vertical Slice Architecture** as the framework for agentic workflows.

---

## 2. Spec-Driven Development (SDD) vs Traditional Agile

In an agentic workflow, ad-hoc, conversational instructions are a liability. Different developers giving vague prompts to an AI lead to highly unpredictable, fragmented code. **Spec-Driven Development** solves this by using strict, machine-readable specifications to drive what agents produce.

Instead of writing code, humans focus heavily on writing and locking down the specifications (like OpenAPI/Swagger definitions, DB schemas in Mermaid syntax, or Markdown files detailing acceptance criteria).

### Why it fits Agents perfectly

* **Deterministic Orchestration:** The overall workflow remains deterministic (e.g., pulling a ticket -> reading spec -> writing code -> running linters -> running test suites). The agent only handles the creative execution inside a tightly sandboxed step.
* **Tight Automated Feedback Loops (Evals):** Agents excel when they can fail fast and auto-correct. In SDD, an agent can take a specification, generate code, run it against automated test suites and linters, read the error logs, and iterate *completely out of the human loop* until the code satisfies the spec.
* **No Room for Hallucination:** Because the entry constraints (inputs, expected types, strict boundaries) are clearly defined in a file like `AGENTS.md` or `instructions.md`, the AI's cognitive load is dropped drastically, minimizing hallucinations.

### Methodology Comparison

| Feature/Metric | Agile / Scrum | Spec-Driven Development (SDD) |
| :--- | :--- | :--- |
| **Primary Artifact** | User Stories (written for humans) | Machine-readable Specs (OpenAPI, Markdown Schemas) |
| **Execution Speed** | Limited by human typing & context-switching | Near-instant parallel exploration by agents |
| **Feedback Loop** | Code Review / QA cycles (hours to days) | Local Evals, Linters, and Unit Tests (seconds) |
| **Human Role** | Implementation & manual testing | Writing specs, architecture, and final PR review |

### The Perfect Agentic Pipeline Structure

When setting up an agentic software factory, the workflow follows this sequence:

1. **Human Spec Definition:** The human defines a concrete spec file (e.g., input structures, database changes, and rigorous acceptance criteria) and locks down an `AGENTS.md` system prompt file defining the project rules.
2. **Agent Planning & Breakdown:** The primary coding agent analyzes the specification, breaks down the implementation into atomic sub-tasks, and maps out the files it needs to create or modify.
3. **Autonomous Code Generation:** The agent writes the code within its designated feature workspace. It interacts strictly with direct tools or APIs rather than loose, conversational inputs.
4. **Deterministic Evaluation Gates:** An orchestration engine hooks into the repository, running compilers, linters, and unit tests. If the build fails, the error logs are fed back to the agent to auto-correct. Human intervention is skipped entirely during these loops.
5. **Human-in-the-Loop Review:** Once all evaluation gates pass cleanly, the engine automatically commits the code and opens a Pull Request (PR). Humans step back into the loop solely to perform final high-level code review and merge.

---

## 3. Vertical Slice Architecture

Vertical Slice Architecture organizes code by **features/business actions** rather than technical layers. Every file needed for a single endpoint or feature sits inside one self-contained directory.

### Core Architectural Rules

* **Locality of Context:** The agent doesn't need to read or scan the entire workspace. It focuses on a single folder containing the specific feature block.
* **Additive Actions Over Destructive Actions:** It is significantly safer for an agent to add an entirely new feature slice (additive) than to modify broad, shared layers (destructive) which risks breaking unrelated parts of the codebase.
* **Feature vs Actor:** An **Actor** represents *who* is doing it (User, Admin). A **Feature** represents *what* they are doing (`RegisterUser`, `UploadPayment`). Organize directories by **Actions (Verbs) and Domains (Nouns)**, not the people pulling the triggers. Handle the Actor purely through authorization logic *inside* that feature to avoid duplication.

---

## 4. Full-Stack Unified Monorepo Layout

Below is the blueprint for a unified repository containing a **Vue.js 3** frontend application and a **Python/SQLite/Jinja** backend application.

```text
my-app-monorepo/
│
├── frontend/                             # VUE.JS FRONTEND APPLICATION
│   ├── src/
│   │   ├── features/
│   │   │   ├── auth/                     # Grouped by Business Sub-domain
│   │   │   │   ├── login/
│   │   │   │   │   ├── LoginPage.vue     # Route entry / View Page (Controller-like)
│   │   │   │   │   ├── LoginForm.vue     # Lightweight visual presentation component
│   │   │   │   │   ├── useLogin.ts       # Composable (state, validation, API network logic)
│   │   │   │   │   └── LoginTests.spec.ts
│   │   │   │   └── forgot-password/
│   │   │   │       ├── ForgotPasswordPage.vue
│   │   │   │       └── useForgotPassword.ts
│   │   │   └── payments/
│   │   │       └── upload-payment/
│   │   │           ├── UploadPaymentPage.vue
│   │   │           └── useUploadPayment.ts # Makes API calls to /api/payments/upload
│   │   └── shared/                       # Global design system & layout primitives only
│   │       ├── components/               # BaseButton.vue, BaseInput.vue (Zero business logic)
│   │       └── router/                   # Lazy loads main page components from features
│   └── package.json
│
├── backend/                              # PYTHON BACKEND APPLICATION
│   ├── src/
│   │   ├── features/
│   │   │   ├── users/                    # User Profile sub-domain
│   │   │   │   └── LoginUser/
│   │   │   │       ├── LoginUserController.py    # HTTP endpoint routing reception
│   │   │   │       └── LoginUserHandler.py       # Core execution worker / business brains
│   │   │   └── payments/                 # Payments sub-domain
│   │   │       └── UploadPayment/
│   │   │           ├── UploadPaymentController.py
│   │   │           ├── UploadPaymentHandler.py
│   │   │           ├── UploadPaymentRequestSchema.py # Input schema validator (The Bouncer)
│   │   │           ├── UploadPaymentTests.py
│   │   │           └── templates/                # Feature-contained Jinja templates
│   │   │               └── receipt_email.html
│   │   └── shared/                       # Common utilities
│   │       ├── Database.py               # Shared DB connection context
│   │       ├── Models.py                 # Bare DB Table schemas (SQLAlchemy/Tortoise)
│   │       └── templates/                # Shared layout primitives
│   │           └── base_email_layout.html # Global header/footer template
│   ├── main.py
│   └── requirements.txt
│
└── AGENTS.md                             # THE AGENTIC ENGINE CONSTITUTION

5. Multi-Agent Orchestration Framework

Instead of assigning equal responsibility to all agents (which creates race conditions and code divergence), use a Hierarchical Model:

    Orchestrator Agent (The Brain): Owns the global map of the codebase and Git branching strategy. Decides whether a human's request is a New Feature (allocates new folder, creates empty boilerplate) or a Modification (locates target folder). Injects project constraints automatically before calling sub-agents.

    Backend Sub-Agent: Write-locked strictly to individual backend feature folders. Writes pure server logic, local unit tests (Happy Path), and schema matching.

    Frontend Sub-Agent: Locked strictly to frontend feature slices. Writes pure Vue 3 logic and layouts.

    QA / Evaluation Agent: Acts as an autonomous quality gate. Operates sequentially in a state-driven loop after code-writing agents complete their work. Runs local feature tests, global regression test suites, and linters. It can generate adversarial/edge-case test files on the fly to challenge backend verification.

6. Project Refactoring Strategy

When a project is already close to completion under a traditional layered model, do not execute a sweeping global refactor. The risk of breaking hidden imports and creating loop chaos for your agents is extremely high.

Instead, execute a "Fix it Forward" hybrid paradigm:

    Leave legacy directories (controllers/, models/) completely alone.

    Scaffold any remaining new capabilities inside a clean, isolated features/ directory following the Vertical Slice structure.

    Point your central routing file to catch endpoints from both structures simultaneously. Use this safe sandbox to test your agent configuration before migrating to clean-slate repositories.

7. Gemini CLI Prompt to Scaffold Architecture

Use this exact prompt format to ensure the AI generates the clean architecture without hallucinating flat files:
Plaintext

You are the Orchestrator Agent for an existing Python/SQLite backend structured using Vertical Slice Architecture. 

---
[TARGET TASK]: Create a new feature slice named "DownloadReceipt" under the payments domain.
---

Your task is to act as the Software Architect. Do not write the full business logic yet. Follow these rules strictly:
1. Slices must maximize internal cohesion and minimize external coupling.
2. Group files by business context, not technical layers.
3. Use strict naming suffixes: *Controller.py, *Handler.py, *RequestSchema.py, *Tests.py.
4. If the feature requires a Jinja template, place it inside a nested 'templates/' folder within that specific slice directory.

Execute your response in two clear stages using XML blocks:

<STAGE_1_PLAN>
Review the request and output a precise ASCII file tree showing exactly what folders and files need to be created.
</STAGE_1_PLAN>

<STAGE_2_SHELL>
Output a single, continuous bash script block using 'mkdir -p' and 'cat << 'EOF'' syntax to generate all the empty boilerplate files with initial structures (imports, class definitions, and basic routing setups). Ensure the paths match the existing backend directory framework exactly.
</STAGE_2_SHELL>

Begin your execution now.
