---
name: project-context
description: Persistent knowledge for this project — purpose, architecture, conventions, constraints, and non-goals. Use when deciding where code lives, what the system must not do, or whether a change fits the architecture.
---

# Project context

Load this when a change depends on project facts. Leave it unloaded for work that does not.

## What to read

- [references/project.md](references/project.md) — facts seeded at init and updated as the project changes

## Keep it current

When architecture, conventions, dependencies, or non-goals change, update `references/project.md` in the same session. Add any new section to its contents list.

## Leave evaluation alone

Feature success is defined by the locked checks in `checks/approved/`, not by this skill.
