# Codex Project Factory V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an installable Codex plugin for explicit, resumable software-project delivery, with a deterministic Git Delivery Gate between full acceptance and `DONE`.

**Architecture:** Markdown Skills provide the workflow contract and specialist responsibilities. A dependency-free Python module under `scripts/` owns Git facts, state transitions, secret scanning, commit planning, dry-run behavior, and safe Push checks. Project evidence remains in the target repository under `docs/` and `workflow/`.

**Tech Stack:** Codex plugin manifest, Markdown Skills, Python 3 standard library, Git CLI, assert-based tests.

---

### Task 1: Scaffold the installable plugin

**Files:**
- Create: `.codex-plugin/plugin.json`
- Create: `README.md`
- Create: `AGENTS.md`
- Create: `.gitignore`
- Create: `skills/README.md`

- [ ] **Step 1: Write the plugin manifest**

Create `.codex-plugin/plugin.json` with the package identity and entry-point description:

```json
{
  "name": "codex-project-factory",
  "version": "1.0.0",
  "description": "Explicit, resumable software-project workflow with a verified Git Delivery Gate.",
  "skills": ["skills"]
}
```

- [ ] **Step 2: Add repository navigation and safe defaults**

`AGENTS.md` must point to the main Skill, workflow state, requirements, architecture, acceptance, and Git Delivery documents. `.gitignore` must include `.superpowers/`, `references/repos/`, runtime logs, environment files, dependency directories, and build outputs without ignoring source files.

- [ ] **Step 3: Document installation and trigger behavior**

`README.md` must state that the plugin is opt-in, starts only from “使用项目工作流” or `/project-factory`, resumes from `workflow/state.json`, requires an existing Git repository for Git Delivery, and uses `确认需求` as the freeze confirmation.

- [ ] **Step 4: Verify the scaffold**

Run:

```powershell
Get-Content .codex-plugin/plugin.json | ConvertFrom-Json
Test-Path AGENTS.md
Test-Path README.md
```

Expected: JSON parses and both paths return `True`.

### Task 2: Implement the workflow state and Git facts core

**Files:**
- Create: `scripts/project_factory.py`
- Create: `scripts/state_schema.json`
- Test: `scripts/test_project_factory.py`

- [ ] **Step 1: Define the state contract**

`state_schema.json` documents the top-level `phase`, `status`, `requirementsFrozen`, `completedModules`, `failedGate`, `retryCount`, `lastGoodCommit`, and nested `gitDelivery` fields: `repositoryDetected`, `remoteDetected`, `securityScan`, `commitPlan`, `commitsCompleted`, `finalTest`, `remoteVerify`, `push`, `branch`, and `head`.

- [ ] **Step 2: Add state helpers**

Implement these standard-library functions in `scripts/project_factory.py`:

```python
def load_state(path: Path) -> dict: ...
def save_state(path: Path, state: dict) -> None: ...
def update_state(path: Path, **changes) -> dict: ...
```

`load_state` returns a new default state when the file is absent, rejects malformed JSON, and preserves unknown fields. `save_state` writes UTF-8 JSON through a sibling temporary file and replaces the target atomically. `update_state` performs a shallow top-level update and records `updatedAt` in UTC.

- [ ] **Step 3: Add safe Git command wrappers**

Implement:

```python
class GitError(RuntimeError): ...
def run_git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]: ...
def inspect_repository(repo: Path) -> dict: ...
```

`inspect_repository` uses `git rev-parse --is-inside-work-tree`, `git status --short`, `git branch --show-current`, and `git remote -v`; it returns `repositoryDetected`, `remoteDetected`, `branch`, `status`, and parsed remotes. It never runs a command from a reference repository.

- [ ] **Step 4: Write focused tests first**

In `scripts/test_project_factory.py`, use `tempfile.TemporaryDirectory()` and `subprocess.run` to assert missing-state defaults, atomic state round-trip, malformed-state rejection, non-repository detection, and repository/remote detection.

- [ ] **Step 5: Run the core tests**

Run:

```powershell
python scripts/test_project_factory.py
```

Expected: all assertions pass with exit code `0`.

### Task 3: Implement Git Delivery Gate operations

**Files:**
- Modify: `scripts/project_factory.py`
- Create: `scripts/git_delivery.py`
- Test: `scripts/test_git_delivery.py`

- [ ] **Step 1: Define delivery result values**

Use string constants for `READY`, `BLOCKED`, `WAITING_FOR_REPOSITORY`, `WAITING_FOR_GIT_REMOTE`, `WAITING_FOR_GIT_AUTH`, `PUSH_FAILED`, `FAILED_VALIDATION`, `NEEDS_HUMAN_DECISION`, `PASS`, and `USER_SKIPPED`. Keep the state shape from Task 2 as the only persisted schema.

- [ ] **Step 2: Implement prerequisite and remote gates**

Implement:

```python
def prerequisites_passed(evidence: dict) -> bool: ...
def classify_repository(repo: Path) -> str: ...
def validate_remote(remotes: list[dict], target: str = "origin") -> dict: ...
```

`prerequisites_passed` requires full acceptance, build, unit, integration, E2E, coverage, zero P0/P1, and no blocking security issue. `classify_repository` returns the three repository cases. `validate_remote` rejects missing, malformed, ambiguous, or non-origin targets with a human-decision result.

- [ ] **Step 3: Implement secret and generated-file scanning**

Implement:

```python
SECRET_NAMES = {...}
def scan_paths(repo: Path, paths: Iterable[Path]) -> dict: ...
def scan_worktree(repo: Path) -> dict: ...
```

Scan tracked and untracked candidate files for environment files, private-key markers, token/password names, certificates, dumps, logs, backups, dependency folders, and build output. Return redacted findings containing only relative paths and rule names. Never include matched secret values in output.

- [ ] **Step 4: Implement logical commit planning**

Implement:

```python
def build_commit_plan(repo: Path, files: list[Path], manifest: dict | None = None) -> list[dict]: ...
def write_commit_plan(path: Path, plan: list[dict]) -> None: ...
```

Group files by explicit module/feature mappings when provided, otherwise use conservative path categories (`database`, `auth`, `core`, `api`, `ui`, `agent`, `tests`, `docs`, `infra`). Emit Commit ID, message, purpose, files, dependencies, and risk. Never stage files automatically while planning.

- [ ] **Step 5: Implement safe segmented commit and verification**

Implement:

```python
def commit_group(repo: Path, group: dict, dry_run: bool = False) -> dict: ...
def verify_history(repo: Path) -> dict: ...
def final_test_gate(evidence: dict) -> bool: ...
```

`commit_group` stages only listed files, checks the staged diff, blocks dangerous Git commands, and commits only after a passing secret scan. Dry run returns the exact planned commands without mutating the repository. `verify_history` confirms no unexpected untracked files and captures HEAD/log details. `final_test_gate` blocks Push when any configured final check fails.

- [ ] **Step 6: Implement remote verification, Push, and recovery**

Implement:

```python
def push(repo: Path, remote: str = "origin", branch: str | None = None, dry_run: bool = False) -> dict: ...
def resume_git_delivery(repo: Path, state: dict) -> dict: ...
```

Verify URL, owner, repository name, branch, and upstream before Push. Use `git push -u origin <branch>` only when no upstream exists. Map authentication errors to `WAITING_FOR_GIT_AUTH`, transient network failures to `PUSH_FAILED`, and history conflicts to `NEEDS_HUMAN_DECISION`. Resume from local history and state without repeating completed commits.

- [ ] **Step 7: Add the executable Git Delivery CLI**

`scripts/git_delivery.py` must expose `inspect`, `scan`, `plan`, `verify`, and `deliver` subcommands with `--repo`, `--state`, `--dry-run`, and `--evidence` options. JSON output is machine-readable and secrets are redacted. `deliver` refuses to Push unless every gate is `PASS`.

- [ ] **Step 8: Test all delivery cases**

`scripts/test_git_delivery.py` must assert the ten required cases: existing Git with origin, existing Git without origin, no Git, secret blocking, final-test blocking, abnormal remote, waiting-state recovery, interrupted commit recovery, Push failure preservation, and existing-history protection. Add idempotent rerun and dry-run assertions.

- [ ] **Step 9: Run the delivery tests**

Run:

```powershell
python scripts/test_git_delivery.py
```

Expected: all assertions pass and no test performs a real remote Push.

### Task 4: Add the specialist Skills

**Files:**
- Create: `skills/requirement-parser/SKILL.md`
- Create: `skills/requirement-interviewer/SKILL.md`
- Create: `skills/requirements-freeze/SKILL.md`
- Create: `skills/github-reference-miner/SKILL.md`
- Create: `skills/reference-synthesizer/SKILL.md`
- Create: `skills/solution-architect/SKILL.md`
- Create: `skills/plan-reviewer/SKILL.md`
- Create: `skills/implementation-agent/SKILL.md`
- Create: `skills/module-reviewer/SKILL.md`
- Create: `skills/full-project-auditor/SKILL.md`
- Create: `skills/release-manager/SKILL.md`
- Create: `skills/git-delivery/SKILL.md`

- [ ] **Step 1: Define each Skill's input, output, and gate**

Each file must name its single responsibility, required files, output files, stop conditions, and the next state. Requirements and acceptance criteria remain immutable after freeze. Skills must read only the progressive-disclosure inputs needed for their phase.

- [ ] **Step 2: Encode the Git Delivery contract**

`skills/git-delivery/SKILL.md` must instruct the agent to invoke `scripts/git_delivery.py`, inspect `workflow/state.json`, refuse reference-repository execution, perform secret scanning before staging, write `workflow/git-commit-plan.md`, use explicit file lists, run final tests after commits, and stop at every waiting or human-decision state.

- [ ] **Step 3: Verify Skill links**

Run:

```powershell
rg -n "workflow/state.json|REQUIREMENTS_FROZEN|git_delivery.py|GIT_DELIVERY|DONE" skills
```

Expected: every phase Skill references its state/evidence boundary, and Git Delivery references the executable core.

### Task 5: Add the project-factory orchestrator and project templates

**Files:**
- Create: `skills/project-factory/SKILL.md`
- Create: `templates/project/AGENTS.md`
- Create: `templates/project/workflow/state.json`
- Create: `templates/project/workflow/progress.md`
- Create: `templates/project/workflow/failures.md`
- Create: `templates/project/workflow/last-good-state.md`
- Create: `templates/project/workflow/git-commit-plan.md`
- Create: `templates/project/docs/requirements/.gitkeep`
- Create: `templates/project/docs/research/.gitkeep`
- Create: `templates/project/docs/architecture/.gitkeep`
- Create: `templates/project/docs/acceptance/module-reports/.gitkeep`
- Create: `templates/project/references/repos/.gitkeep`

- [ ] **Step 1: Encode explicit trigger and resume behavior**

`skills/project-factory/SKILL.md` must activate only for “使用项目工作流” or `/project-factory`, initialize target evidence directories, resume when state exists, and pause only for `确认需求`, unavailable P0/P1 decisions, credentials, remote creation, dangerous Git operations, or other defined human-decision states.

- [ ] **Step 2: Encode the complete lifecycle**

The orchestrator must map each phase to one specialist Skill, require full acceptance before release preparation, require Git Delivery before `DONE`, and return failures to the owning implementation/review gate. It must keep ordinary developer commits separate from final delivery.

- [ ] **Step 3: Add reusable target-project templates**

Templates must be concise navigation and state defaults. They must not contain secrets, copied reference source, or the full design prompt. `workflow/state.json` starts at `INIT` with `requirementsFrozen: false` and a `gitDelivery` object whose statuses are `PENDING`.

- [ ] **Step 4: Verify orchestration references**

Run:

```powershell
rg -n "REQUIREMENT_ANALYSIS|FULL_ACCEPTANCE|GIT_DELIVERY|WAITING_FOR_REPOSITORY|DONE" skills/project-factory templates/project
```

Expected: the lifecycle and waiting states are present exactly once in the orchestrator contract and the template state is valid JSON.

### Task 6: Regression, packaging, and final verification

**Files:**
- Modify: `README.md`
- Modify: `skills/README.md`
- Create: `scripts/test_package.py`
- Create: `docs/acceptance/project-factory-v1.md`

- [ ] **Step 1: Add package self-checks**

`scripts/test_package.py` must parse the manifest and template state, ensure all listed Skills exist, execute both script test files, and verify that no Skill or documentation contains a literal credential pattern.

- [ ] **Step 2: Document actual commands and constraints**

README must include the install location, explicit trigger, target-repository prerequisites, dry-run command, test commands, waiting states, and final report fields.

- [ ] **Step 3: Run all checks**

Run:

```powershell
python scripts/test_project_factory.py
python scripts/test_git_delivery.py
python scripts/test_package.py
```

Expected: exit code `0` for all three commands.

- [ ] **Step 4: Record acceptance evidence**

Write `docs/acceptance/project-factory-v1.md` with the actual command results, implemented files, lifecycle, Git Delivery behavior, security protections, recovery behavior, test results, and known limitations. State clearly that the package repository has no Git commit when `git rev-parse` is unavailable; do not claim a commit or remote Push that did not occur.

- [ ] **Step 5: Inspect the final surface**

Run:

```powershell
rg -n "TBD|TODO|FIXME|password=|token=|BEGIN .*PRIVATE KEY" . -g '!\.superpowers/**'
```

Expected: no placeholders or credential material in the package. Read back the manifest, main Skill, Git Delivery Skill, scripts, and acceptance report before delivery.
