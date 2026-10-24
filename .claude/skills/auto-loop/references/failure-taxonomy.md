# Failure taxonomy

Use one label per failed round. The label decides who is allowed to respond.

## Implementation

The requirement was clear and the check is fair. The attempt built the wrong thing.

Response: feature builder fixes the code on the next round.

## Missing requirement

The checks never covered something the user cares about.

Response: stop. The user decides whether to add a check. Do not invent the requirement inside the implementation loop.

## Integration

The measured rule passed, but the feature is not actually connected to the app (nothing saved, nothing shown, nothing callable).

Response: feature builder wires it in. If this happens on more than one feature, auto-loop proposes a Learned rule.

## Regression

The new work breaks or ignores behavior that already existed.

Response: feature builder fixes the existing call sites. Repeated cases become a Learned rule.

## Environment

The code may be fine, but the command, dependency, or machine setup failed.

Response: fix the environment or document the missing dependency in the project-context skill. Do not rewrite working code to route around a local setup gap.

## Evaluation

The check itself is wrong, or `verify_checks.py` fails because approved checks or the manifest changed.

Response: stop. Only the user changes approved checks, then runs `python scripts/refresh_check_manifest.py` and commits. The feature builder does not "fix" this class.
