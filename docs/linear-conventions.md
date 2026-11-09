# Linear conventions — ScoreCheck

Applies to the ScoreCheck project in Linear (team JOS). Adopted 8 Nov 2026; the audit marker is JOS-130.

**The repo is the source of truth.** Linear is for navigation, status, and the audit trail. Where Linear and the repo disagree, the repo wins.

## What goes where

| Place | Holds | Never holds |
|---|---|---|
| Project overview | Two or three sentences on what ScoreCheck is, the repo link, the hard boundaries, and a link to the "How this project is organised" document | Dated status, results, changelog |
| Milestones | One per feature. A target date when known. An empty or one-line description. Progress comes from their issues | Specs, constants, findings, status narrative |
| Feature issue | One per feature. A one-line outcome, links to the spec (the `features.md` section, `checks/approved/feature-NNN.md`, `docs/choices/feature-NNN.md`), and a "Done when" checklist | Results, history, copied requirements |
| Sub-issues | Created when a feature starts: product questions, checks (draft and lock), and build. Only when the feature needs that split | Pre-made placeholders for features that have not started |
| Relations | The `blocks` chain between features in build order | — |
| Labels | `Feature` on feature issues. `Bug` and `Improvement` as named | — |
| Project updates | One dated update per merged feature or blocking event, with health set: the findings in a few lines and the PR link. **The only place for results and status narrative** | Specs |
| Documents | "How this project is organised" (short, points here) and "Testing requirements" | Status documents |
| Repo only | Specs, check text, constants and pins, engineering choices, round logs, full result figures | — |

## Who updates Linear, and when

- **Status moves through GitHub.** Put the issue key in the branch name or the PR title (for example, `JOS-28`), so a linked PR moves the issue. An agent sets a feature issue to In Progress by hand only when work starts before a PR exists. A merged PR with the key in its title closes the issue, so a PR that finishes only part of an issue leaves the key out of the title and says "Part of JOS-NNN" in the body.
- **After a merge,** post one project update (findings plus the PR link). Do not edit descriptions to report status.
- **One fact, one place.** Link to it; never copy the same fact into a second Linear item.
- **Linear edits are mechanical.** Agents delegate them to a Haiku subagent.
- **Destructive edits need the user's OK.** That covers deleting text, milestones, documents, or issues. Copy the content into a project update or the repo first.
- **New conventions** change this file in a PR. The Linear document only summarises it.
