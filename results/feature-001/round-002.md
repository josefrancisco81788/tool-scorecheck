# feature-001 — round 002

Status: kept

## Attempt

Three defects from review of round 001, fixed together in one commit on `feature/001-panel`:

1. Origination label. `_truth.realise_default` accumulated the default event from month 1, and the label is `true_default` on the origination row. A person who originated later had more months of hazard before applying, so `history_months` predicted the label. The event is now masked off for every month strictly before that person's `origination_month` (through `is_pre_origination`), then accumulated. The origination month and later months still absorb. `post_origination_shock` and the row `features.from_panel` reads are unchanged.
2. Delinquency draws. `delinquency_count_30`, `_60`, and `_90` called `Generator.poisson` with a lambda that depends on the person's pre-origination electricity. NumPy's Poisson sampler consumes a variable number of uniforms, so one person's late rate shifted every later person's count. `_application._poisson` now draws exactly one uniform per person from the same named stream and inverts the Poisson CDF in a loop that draws nothing more. The constant-lambda `poisson` calls are untouched, and the `build` docstring ("the number of draws depends only on the person set") is now true.
3. Run publish. `panel.generate` rejects `bool` for `n_households` the way it rejects `bool` for `seed`, and coerces with `int()` before any directory is created, so `np.int64` never reaches `RunConfig.to_json`. `rundir.write_run` removes the staging directory when staging or the JSON write fails. A previous run is renamed to a sibling backup, the stage is renamed onto the final name, and only then is the backup deleted. If that rename fails, the backup is put back.

`Tuning.default_intercept` was not retuned. The 2,000-household driver tests still clear the 30-default floor (50 origination defaults among 3,494 persons in the probe below).

## Checks

- B1 to B52 and the round-001 integration checks: pass, through the full suite below
- B44, golden fixture: pass after regenerating `tests/fixtures/golden/panel.json` with `scripts/write_golden_panel.py`. Only the `ground_truth` and `application_features` hashes changed. `CHANGELOG.md` has a line saying why.

`verify_checks.py`: pass, before product code and again after the golden regeneration.

## Test run

Command: `.venv\Scripts\python.exe -m pytest -q --tb=line`

Before regenerating the golden fixture:

```text
......................................F................................. [ 72%]
...........................                                              [100%]
================================== FAILURES ===================================
E   AssertionError: assert {'household':...f94e965', ...} == {'household':...f94e965', ...}
      Omitting 6 identical items, use -vv to show
      Differing items:
      {'ground_truth': '35ec8a43...'} != {'ground_truth': '5b8a7142...'}
      {'application_features': 'd2ee9e03...'} != {'application_features': '1696515f...'}
FAILED tests/unit/test_golden_panel.py::test_golden_panel - AssertionError: a...
1 failed, 98 passed in 71.90s (0:01:11)
```

After regenerating it:

```text
........................................................................ [ 72%]
...........................                                              [100%]
99 passed in 41.06s
Locked checks verified (1 file(s)).
```

### Delinquency isolation script (not a locked check)

Builds a 300-household panel, copies the run directory, sets every pre-origination `electricity_state` of person 1 to `unpaid_past_30d`, reruns `features.from_panel` on the copy, and compares. It asserts the people whose `delinquency_count_30` or `_60` changed are a subset of those whose own late rate changed, and those whose `_90` changed are a subset of those whose disconnect count changed. The last line before the verdict replays `Generator.poisson` on the same two lambda vectors for contrast.

```text
persons: 515  person 1 pre-origination rows edited: 14
late rate changed for: [1]  (0.143 -> 1.000)
delinquency_count_30 changed for: [1]  (0 -> 1)
delinquency_count_60 changed for: []
delinquency_count_90 changed for: [1]  (disconnect count changed for [1])
for contrast, Generator.poisson on the same lambdas would change 16 persons
PASS
```

### Origination and publish probe (not a locked check)

```text
pre-origination true_default ones: 0 of 30720
origination defaults: 50 of 3494
corr(origination_month, label): -0.029
np.int64 run_config: 300
bool rejected: n_households must be an int, got bool | dir created: False
after json failure, dir listing unchanged: True | old run intact: True
after replace failure, dir listing unchanged: True | old run restored: True
```

The 2,000-household panel has no default before origination. The label no longer rises with origination month (correlation -0.029). The two failure cases patch `RunConfig.to_json` and the stage-to-final `os.replace` to raise. In both, the data directory listing is unchanged afterwards and the earlier run is still readable.

## Failure

Only the golden hash test failed, as expected, because the ground truth and features changed. It passed after the fixture was regenerated.

Failure type: regression

## What changed

- `src/scorecheck/panel/_truth.py`: `realise_default` takes the grid and masks pre-origination events before accumulating
- `src/scorecheck/panel/__init__.py`: passes the grid, and validates and coerces `n_households`
- `src/scorecheck/features/_application.py`: `_poisson`, one uniform per person and CDF inversion, for the three delinquency counts
- `src/scorecheck/rundir.py`: `write_run` cleans up the stage on failure and swaps through a backup sibling
- `tests/fixtures/golden/panel.json` and `CHANGELOG.md`

## Why kept or undone

Kept. All 99 tests pass, the locked checks verify, and the probes show each defect is gone in the real run artifact. The label no longer depends on how long a person waited to apply. One person's electricity history no longer moves anyone else's delinquency counts. A failed publish leaves the earlier run in place.

## Lesson

Round 001's checks did not catch either the label leak or the cross-person draw coupling, because both produce plausible distributions. Possible rule, pending human confirmation: any draw whose parameter depends on behaviour must consume a fixed number of uniforms per row, and any label read at a cut must be built only from events at or after that cut.
