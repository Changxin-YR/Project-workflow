---
name: requirements-freeze
description: Produce the immutable product requirements and wait for the exact user confirmation.
---

# Requirements Freeze

Combine the analysis and interview records into `docs/requirements/REQUIREMENTS_FROZEN.md` with goal, users, scope, non-functional requirements, technical limits, permissions, business rules, UI/deployment expectations, explicit exclusions, and testable acceptance criteria. Set `requirementsFrozen` only after the user replies exactly `确认需求`; otherwise remain in `WAITING_FOR_USER`. After freezing, never silently edit this file.

