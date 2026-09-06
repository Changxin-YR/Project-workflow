---
name: project-factory
description: Run the opt-in, resumable software-project production workflow when the user says 使用项目工作流 or /project-factory.
---

# Project Factory

Activate only when the user explicitly says `使用项目工作流` or `/project-factory`. For ordinary requests, do nothing.

## Facts first

Work in the current target repository. Read `AGENTS.md`, then `workflow/state.json`, the active plan, frozen requirements, relevant architecture notes, and the latest acceptance evidence. Treat Git state and workflow state as facts; do not use chat history as a state source.

If no state exists, create the template directories and an `INIT` state. If state exists, resume its phase and do not repeat completed work.

## Lifecycle

Run the specialist Skill for each phase in order:

```text
INIT -> REQUIREMENT_ANALYSIS -> REQUIREMENT_INTERVIEW -> WAITING_FOR_USER
-> REQUIREMENT_FROZEN -> REFERENCE_RESEARCH -> ARCHITECTURE -> PLAN_REVIEW
-> IMPLEMENTATION -> MODULE_ACCEPTANCE -> FULL_ACCEPTANCE
-> RELEASE_PREPARATION -> GIT_DELIVERY -> FINAL_DELIVERY -> DONE
```

Persist phase, status, evidence, retry count, failure gate, and last good state after every phase. Keep `REQUIREMENTS_FROZEN.md`, security rules, permission rules, acceptance criteria, and architecture decisions immutable after freeze unless the user explicitly changes them.

## Human gates

Pause only for the exact freeze reply `确认需求`, missing P0/P1 product decisions, credentials, remote repository creation, dangerous Git actions, ambiguous remotes, or other `NEEDS_HUMAN_DECISION` conditions. P2 details use a stated default and appear in the final confirmation.

## Delivery gate

Do not set `DONE` after Full Acceptance alone. Full Acceptance, Build, core Unit/Integration/E2E, 100% core requirement coverage, zero P0/P1 bugs, security scan, commit plan, history verification, final tests, remote verification, and Push must all pass. Delegate Git work to `git-delivery/SKILL.md` and invoke `scripts/git_delivery.py`; never let an implementation phase Push.

## Failure and recovery

Record a failure report with expected/actual results, reproduction, evidence, likely root cause, owner, files, and fix. After the configured repeated-failure threshold, enter root-cause analysis instead of blind retries. On resume, reconcile state with `git status`, `git log`, remote facts, and persisted evidence before continuing.

