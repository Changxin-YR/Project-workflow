---
name: requirement-parser
description: Extract a structured software-project brief from the user's raw idea.
---

# Requirement Parser

Read only the user input and existing project context. Write `docs/requirements/00-user-input.md` and `docs/requirements/01-requirement-analysis.md` with product goal, users, scope, features, technical keywords, explicit requirements, ambiguities, contradictions, risks, and acceptance candidates. Do not ask questions or implement code. Return `REQUIREMENT_INTERVIEW` with an ordered P0/P1/P2 question list.

