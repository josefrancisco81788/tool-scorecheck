# Checks — <feature-id>: <feature name>

Status: draft

Feature: <feature-id>

## Behavior

- [ ] <observable outcome from the requirement>

## Executable tests

Every automated test that will prove the checks above, named before any product code exists. The feature builder writes these first and may not weaken them.

Test command: `<command run from the project root, or "none yet: the feature creates it">`

| Test | File | What it asserts | Proves check |
|---|---|---|---|
| <test name> | <tests/...> | <input, expected outcome, and any tolerance as a number> | <Behavior item> |

Required kinds, per `docs/testing-standards.md`: unit, golden dataset (fixed input and expected output in `tests/fixtures/golden/`) and eval case (`tests/evals/`). Mark a kind "not applicable" only with a reason the human approves, for example "eval case: not applicable, output is deterministic".

## Integration

- [ ] The feature is connected to the rest of the app in the same change that makes the behavior checks pass (saved, displayed, or callable — whichever the feature claims).

## Regression

- [ ] Existing places that already perform this job follow the new behavior. Write "none" if the feature changes nothing that already exists.

## Completeness

- [ ] A person can perform the user-facing action the feature describes. A passing rule in isolation does not satisfy this check.
