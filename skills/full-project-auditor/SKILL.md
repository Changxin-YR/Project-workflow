---
name: full-project-auditor
description: Run the complete project acceptance from a clean-enough environment.
---

# Full Project Auditor

Read frozen requirements, architecture, module reports, and the acceptance matrix. Verify dependency installation, startup, build, migrations, static checks, Unit/Integration/E2E, core and error flows, permissions, validation, logging, data consistency, responsive UI, deployment instructions, environment templates, secrets, and licenses. Write `docs/acceptance/final-report.md` and the requirement-to-code-to-test matrix. Set `FULL_ACCEPTANCE=PASS` only with 100% core coverage, P0/P1 zero, and no blocking security issue.

