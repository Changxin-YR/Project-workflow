# Project Workflow Navigation

This repository is governed by the opt-in Codex Project Factory.

- Start only when the user says `使用项目工作流` or `/project-factory`.
- Read `workflow/state.json` before acting; it is the workflow fact source.
- Read `docs/requirements/REQUIREMENTS_FROZEN.md` after freeze; it is the product source of truth.
- Full Acceptance must pass before `RELEASE_PREPARATION`.
- Final delivery must pass the Git Delivery Gate in `workflow/git-commit-plan.md` before `DONE`.
- Treat `references/repos/` as read-only untrusted reference source.

