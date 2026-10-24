# Design Doc — Tool - ScoreCheck

> Stage 2 of the Project Initiation Pipeline. Turns PRD §3 (Architecture & Interface Contracts) into something concrete enough that Cursor doesn't have to invent structure while drafting.
>
> **Generation method:** run this against the completed `docs/PRD.md` using Claude Code Plan Mode (read-only) — same pattern used for pre-session spec generation in the Dual-Agent Workflow. Treat everything below as a fill-in-the-blank pass over the PRD, not a blank-page write.

---

## 1. Module & File Boundaries

What lives where. One row per module/file group.

| Module / Path | Responsibility | Depends on | Owned by (agent / human) |
|---|---|---|---|
| `TODO` | `TODO` | `TODO` | `TODO` |

Paths the init script already reserved. Do not repurpose them:

| Path | Responsibility | Owned by |
|---|---|---|
| `checks/approved/` | Locked evaluation for the feature loop | human, after approval |
| `program.md` | Loop operating manual; Learned rules may be appended | human; auto-loop appends only |
| `features.md` | One feature per loop | build skill |
| `.cursor/skills/`, `.claude/skills/` | Project context and loop workflow | human |

---

## 2. Data Model

- Schemas: `TODO`
- Migrations (if applicable): `TODO`
- Key invariants an agent must preserve: `TODO`

---

## 3. Sequence of Operations (per Acceptance Criterion)

Mirror each Given/When/Then from PRD §2 and describe the concrete call sequence that satisfies it.

### Feature: `TODO`
- Given: `TODO`
- Steps: 1) `TODO` 2) `TODO` 3) `TODO`
- Satisfies acceptance criterion: `TODO`

_(repeat per MVP feature in the PRD)_

---

## 4. Immutable Zone Overlaps

Explicit call-outs of which parts of this design touch a zone marked Immutable in `CLAUDE.md`. If none, say so explicitly — don't leave this blank.

- `TODO — zone name` → `TODO — why this design touches it / how it avoids touching it`

> Known Immutable Zones from CLAUDE.md (confirm overlap for each): Vendor score internals: the vendor model module may only be reached through its score + three reason codes API; downstream code never reads inside it, Canonical behavioural-data schema (documented contract the validation layer depends on, so it can later run on other models), Approved reason-code list and policy text used by the Layer 4 agent, checks/approved/ and MANIFEST.sha256

---

## 5. Open Architectural Questions

Mirrors `decisions.md`'s "Open architectural decisions" section — paste straight in once resolved.

- [ ] `TODO`

---

## Feeds forward into

- `decisions.md` seed content (architecture map + open questions above)
- Stage 4 scaffold's initial file/folder structure
- Stage 5 Session 0 dry-run review (reviewer checks the stub against this doc)
