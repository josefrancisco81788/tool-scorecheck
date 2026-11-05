# Checks — <feature-id>: <feature name>

Status: draft

Feature: <feature-id>

About one page. Plain language. Engineering choices and the test plan live in `docs/choices/<feature-id>.md`, which is not locked.

## Product answers

The human's answers to this feature's product questions, one line each, with the number they chose. Write "none" if the feature raised none.

## Behavior

- [ ] <observable outcome from the requirement, one or two sentences>

## Integration

- [ ] The feature is connected to the rest of the app in the same change that makes the behavior checks pass (saved, displayed, or callable — whichever the feature claims).

## Regression

- [ ] The tests and locked checks of earlier features still pass. Name anything this feature deliberately changes, or write "nothing else changes".

## Completeness

- [ ] A person can perform the user-facing action the feature describes. A passing rule in isolation does not satisfy this check.
