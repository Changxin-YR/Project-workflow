---
name: git-delivery
description: Safely deliver a fully accepted project through repository detection, security checks, segmented commits, verification, and Push.
---

# Git Delivery

This Skill runs only after Full Acceptance. Read `AGENTS.md`, `workflow/state.json`, acceptance evidence, and the active commit plan. Run the executable core from the plugin root:

```powershell
python scripts/git_delivery.py inspect --repo <target>
python scripts/git_delivery.py scan --repo <target>
python scripts/git_delivery.py deliver --repo <target> --state <target>/workflow/state.json --evidence <target>/workflow/final-evidence.json --dry-run
```

## Gate sequence

1. Require Full Acceptance, Build, core Unit/Integration/E2E, 100% core coverage, P0/P1 zero, and no blocking security issue.
2. Detect repository, worktree status, branch, and `origin`.
3. Enter `WAITING_FOR_REPOSITORY` when no Git repository exists; preserve state and wait for a user-created GitHub repository URL.
4. Enter `WAITING_FOR_GIT_REMOTE` when Git exists without `origin`; preserve state and wait for a URL.
5. Validate the remote owner, repository, branch, and history. Ambiguous, malformed, conflicting, or unexpected targets require `NEEDS_HUMAN_DECISION`.
6. Scan all candidate changes for environment files, credentials, keys, certificates, dumps, logs, backups, dependencies, and build output. Redact values; any finding blocks staging.
7. Exclude `references/repos/` and maintain only necessary `.gitignore` entries. Check third-party license facts before including copied source.
8. Write `workflow/git-commit-plan.md`, mapping `FILE -> MODULE -> FEATURE -> COMMIT GROUP`. Group by logical capability and use the existing message convention; otherwise use a clear `feat`, `fix`, `test`, `docs`, `chore`, `build`, `ci`, `perf`, or `security` message.
9. For each group, inspect status and diff, stage explicit paths, inspect the cached diff, scan again, and commit. Never default to `git add .` and never use reset, force Push, destructive clean, history deletion, or shared-history rewriting.
10. Verify history and clean status, run project-defined Build/Lint/Type Check/Unit/Integration/E2E after commits, then verify the remote.
11. Push only when security scan, commit plan, history, final tests, remote verification, and all acceptance gates pass. Use `git push -u origin <branch>` only without an upstream.
12. After Push, verify local and remote HEAD and persist repository URL, branch, HEAD, last commit, commit count, and result. Set `DONE` only after `GIT_DELIVERY=PASS`.

## Recovery

On interruption, inspect `workflow/state.json`, `git status`, `git log`, and remote state. Do not repeat a commit already present in history. Map authentication errors to `WAITING_FOR_GIT_AUTH`, transient network errors to `PUSH_FAILED`, and final test failures to `FAILED_VALIDATION`; preserve local commits and resume from the recorded stage. Use `--dry-run` for repeatable tests without Commit or Push.

