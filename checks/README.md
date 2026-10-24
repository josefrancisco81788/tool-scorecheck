# checks

Drafts are editable. Approved checks are the evaluation for the feature loop.

- `draft/` — written by the write-checks skill, revised until a human approves them
- `approved/` — moved here only by `python scripts/lock_checks.py`
- `approved/MANIFEST.sha256` — hashes of the approved check files; `python scripts/verify_checks.py` fails if they change

Do not hand-edit `approved/`. If a locked check is wrong, a human edits it on purpose and then runs `python scripts/refresh_check_manifest.py`.
