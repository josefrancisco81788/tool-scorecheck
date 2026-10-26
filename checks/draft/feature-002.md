# Checks for feature-002, the black-box vendor score API

Status: draft

Feature: feature-002

Source of truth is `docs/design.md`: section 3 Feature 002, the `src/scorecheck/vendor/` row of the module table in section 1, and the vendor score internals entry in section 4. `features.md` is stale. Where it differs, these checks follow `docs/design.md`.

## Definitions

A "300-household run" and a "2,000-household run" mean `panel.generate(SEED, n, data_dir)` with the config `SEED`, that household count, and a temporary `data_dir`, followed by `features.from_panel` on the run directory it wrote. These are the Feature 001 definitions, unchanged.

The "vendor stage" is `vendor.write_scores(run_dir)` called on a run directory after `features.from_panel` has written `application_features.parquet` there. A "scored 300-household run" is a 300-household run followed by the vendor stage. A "scored 2,000-household run" is the same at 2,000 households.

The "scored frame" is `application_features.parquet` read from the run directory after the vendor stage returns.

The "31 columns" are the `application_features` column set from Feature 001 check B31.

The "vendor public names" are exactly `REASON_CODES`, `score`, and `write_scores`.

"Logical hash" is the Feature 001 logical hash, computed by `scorecheck.logical_hash`.

"Origination rows" are the `ground_truth` rows whose `month` equals that person's `origination_month`, as in Feature 001.

"Spearman" is the Spearman rank correlation with average ranks for ties. A Spearman value that is NaN or infinite fails the check that uses it.

No test generates 200,000 households. Only the integration test generates 50,000. Every other test uses 300 or 2,000 households.

## Behavior

### Public surface

- [ ] C1. `src/scorecheck/vendor/` is a package. Every attribute of `scorecheck.vendor` whose name does not start with an underscore is one of the vendor public names. `scorecheck.vendor.__all__` equals the vendor public names as a set. `from scorecheck.vendor import *` binds exactly those three names.
- [ ] C2. After a scored 300-household run in the same process, no attribute of `scorecheck.vendor` whose name does not start with an underscore is a fitted model. `score` and `write_scores` are functions. `REASON_CODES` is a tuple. `scorecheck` itself binds no attribute named like a booster, a model, or a vendor internal: every attribute of `scorecheck` whose name does not start with an underscore is a submodule of `scorecheck`.
- [ ] C3. No `.py` file under `src/scorecheck/` outside `src/scorecheck/vendor/` matches the pattern `vendor\._|from scorecheck\.vendor import[^\n]*\b_|from scorecheck\.vendor\._`. Code outside the vendor package reaches it only through the vendor public names.
- [ ] C4. `vendor.REASON_CODES == ("RC1", "RC2", "RC3")`.

### `vendor.score`

- [ ] C5. On a scored 300-household run, for every `person_id` in `person`, `vendor.score(run_dir, person_id)` returns a tuple of length 4. Element 0 is an instance of `float`, is finite, and is between 0 and 1 inclusive. Elements 1, 2, and 3 are each a `str` in `vendor.REASON_CODES`, and the three are pairwise distinct.
- [ ] C6. On a scored 300-household run, the reason-code triples (elements 1 to 3, in order) take at least 2 distinct values across persons.
- [ ] C7. On a 300-household run, `vendor.score(run_dir, person_id)` with a `person_id` absent from `person` raises `KeyError`.
- [ ] C8. On a 300-household run, `vendor.score(run_dir, person_id)` returns the same tuple for every `person_id` before and after the vendor stage on that run. Scores do not feed back into the vendor.
- [ ] C9. Higher scores mean lower risk, the same orientation as `EXT_SOURCE_*` on Home Credit. On the scored frame of a 2,000-household run, Spearman(`external_score_1`, `default_label`) is finite and < 0.
- [ ] C28. The vendor may train on the same persons it scores. It fits on the run directory passed to `vendor.score` or `vendor.write_scores`, and scores every person in that run, including the persons it trained on. Scores are in-sample. This feature locks no holdout, no separate vendor population, and no out-of-time split. Feature 004 owns holdout and refit. A reviewer confirms that no file this feature adds or changes calls the vendor score out-of-sample.

### Vendor stage and `application_features`

- [ ] C10. On a scored 300-household run, `external_score_1` on the scored frame is non-null on every row and equals element 0 of `vendor.score(run_dir, person_id)` for that row's `person_id` within an absolute tolerance of 1e-12. `external_score_2` and `external_score_3` are null on every row.
- [ ] C11. On a scored 300-household run, the scored frame's column set equals the 31 columns exactly. No `ground_truth` column other than `person_id` appears in it, so `ability`, `willingness`, `vendor_signal`, `region_month_shock`, and `post_origination_shock` are absent.
- [ ] C12. On a 300-household run, the logical hash of `application_features` with `external_score_1` dropped is the same before and after the vendor stage. The vendor stage changes no column other than `external_score_1`.
- [ ] C13. On a 300-household run, after the vendor stage the run directory holds exactly the eight Parquet files of the Feature 001 tables and `run_config.json`, and no other file or directory. The parent of the run directory has the same entries as before the stage, and the hashes of those entries other than the run directory are unchanged. The test records the relative path and SHA-256 of every file under the repository, including ignored files. The vendor stage runs with `PYTHONDONTWRITEBYTECODE=1`. After the stage, the repository map and the `sys.prefix` map recorded in `pytest_configure` match exactly, except files inside the run directory when the run directory is inside the repository, and except a `.pyc` that unmarshals as a code object compiled from the neighboring tracked `.py` source. The vendor writes no model file to disk outside its process.
- [ ] C14. On a 300-household run, running the vendor stage twice gives equal logical hashes of the scored frame.
- [ ] C15. `vendor.write_scores(run_dir)` returns the frame it wrote. Its logical hash equals the logical hash of the scored frame.

### Ground truth stays inside the vendor

- [ ] C16. `src/scorecheck/cli.py` does not contain the text `ground_truth` or `GROUND_TRUTH`. `vendor.score` and `vendor.write_scores` take a run directory, and `vendor.score` also takes a `person_id`. Neither takes a frame or a ground-truth column. No `.py` file under `src/scorecheck/` contains the text `vendor_signal` unless it is under `src/scorecheck/vendor/` or `src/scorecheck/panel/`, or is `src/scorecheck/schema.py` or `src/scorecheck/config.py`. Outside the generator and the schema, only the vendor reads `vendor_signal`.
- [ ] C17. On a 300-household run, the test records, in `pytest_configure` before test modules are imported, the relative path and SHA-256 of every file under the repository and under `sys.prefix`. Before the first round, that map may differ only by a `.pyc` that unmarshals as a code object compiled from the neighboring tracked `.py` source, or by a path under `.pytest_cache` that pytest itself creates (`CACHEDIR.TAG`, `README.md`, `.gitignore`, or `v/cache/`). `COVERAGE_FILE` is the empty directory for that round. A `.coverage` file under the repository or under `sys.prefix` that is new or changed since `pytest_configure` fails. A new or changed file under `.venv`, under `sys.prefix`, or under an `*.egg-info` directory fails. A `.pyc` that does not unmarshal as that code object fails. Each round, including the unedited baseline and the control, lives under one temporary root created for this test alone. That root's parent contains only that root. The root contains one directory for the round, and that directory's only child is a copy of the nine files named in C13. The copied files include that round's edit. The parent process must not call `vendor.score` or `vendor.write_scores` for that round. The process current directory is the copy. The process environment is a new map that keeps only the variables required to launch Python. `USERPROFILE`, `HOME`, `APPDATA`, `LOCALAPPDATA`, `TMPDIR`, `TEMP`, and `TMP` are one fresh empty directory that is not inside the temporary root. `HOMEDRIVE` and `HOMEPATH` are set so that `Path.home()` is that empty directory. Any other variable whose value is an existing directory under the real user profile is set to that same empty directory. That process calls `vendor.write_scores` on the copy, then `vendor.score` for every `person_id`, and returns the logical hash of the copy's scored frame and the reason-code triple for each `person_id` in ascending `person_id` order. The round fails if the empty directory is non-empty when the process returns. The round fails if a walk of the temporary root, or a listing of its parent, differs from the walk taken before the process, except that `application_features.parquet` inside the copy may change. `panel.generate` runs in a new interpreter that has not imported `scorecheck.vendor`. The parent copies that output and then replaces the seed field in `run_config.json`. No other byte in the nine files differs from that output. No cell in the nine files equals the generating seed. The parent generates this run with a 64-bit seed drawn in that interpreter, other than `config.SEED`. Trying the integers from 0 through 100000 does not find it. That seed is not written into the copied `run_config.json`, is not in the child environment, and does not remain in the source run, which is deleted before the child starts. `panel.generate` with `config.SEED` and 300 households does not reproduce the copied `ground_truth`. `PYTHONDONTWRITEBYTECODE` is `1`. The child is started with an import hook that fails the round if `scorecheck.panel` is imported or `panel.generate` is called. The round fails if the repository hash map or the `sys.prefix` hash map differs from the pre-round map, and the pre-round map itself must already satisfy the `pytest_configure` comparison above. For an edited numeric cell, the new value is `int.from_bytes(hashlib.sha256(f"{column}|{person_id}|{month}".encode("utf-8")).digest()[:4], "big")`. Each edited round fails if the edited column's multiset of values is unchanged. The invariance rounds are:
  - `ability`, `willingness`, and `vendor_signal`, each replaced with the per-cell value on `ground_truth` rows with `month` greater than that person's `origination_month`
  - `region_month_shock` and `post_origination_shock`, each flipped on `ground_truth` rows with `month` greater than that person's `origination_month`
  - `true_default` set to 1 on every `ground_truth` row with `month` greater than that person's `origination_month`. This round also fails unless the sum of `true_default` on those rows increases.
  - `topup_amount`, `wallet_inflow`, and `wallet_outflow`, each replaced with the per-cell value on `month_behaviour` rows with `month` greater than or equal to that person's `origination_month`
  - `electricity_state` rewritten on `month_behaviour` rows with `month` greater than or equal to that person's `origination_month`. `on_time` becomes `unpaid_past_30d`, and every other state becomes `on_time`.

  Each invariance round leaves the logical hash of the scored frame and the ordered reason-code triples equal to the baseline. The control round replaces `vendor_signal` with the per-cell value on `ground_truth` rows with `month` less than or equal to that person's `origination_month`. The control round must change the logical hash of the scored frame. The vendor reads `vendor_signal` on `ground_truth` rows at or before that person's `origination_month`, inside `src/scorecheck/vendor/` only. Edits after origination, to `vendor_signal` or any other column above, must not change the hash or the reason-code triples.

### Policy text stays out

- [ ] C18. `explain.draft` called with any arguments raises `RuntimeError`. `src/scorecheck/explain/` holds `__init__.py` and no other `.py` file, and `src/scorecheck/explain/policy/` does not exist.
- [ ] C19. No file under `src/scorecheck/vendor/` maps a reason code to a sentence. A reviewer confirms that each of `RC1`, `RC2`, and `RC3` appears in the vendor package only as a bare token, with no adverse-action wording beside it.

### Scope

- [ ] C20. On a scored 300-household run, no file name in the run directory and no column name in the scored frame matches the case-insensitive pattern `firm|msme|business|enterprise|company`.
- [ ] C21. No file under `src/scorecheck/vendor/`, no line of `python -m scorecheck` stdout, and no line `README.md` gains in this feature matches the case-insensitive pattern `kayana|\bmaya\b|trusting social|creditbpo|\bglobe\b|\bsmart\b|\bdito\b|gcash`.
- [ ] C22. A reviewer confirms that no file this feature adds or changes claims an in-house model beats the vendor, or calls the vendor score good or bad. The vendor is described as simulated.

### Reproducibility

- [ ] C23. Two scored 300-household runs with the same seed, each in its own process, one with `PYTHONHASHSEED=0` and one with `PYTHONHASHSEED=1`, each writing to a distinct output directory, give equal logical hashes of the scored frame.
- [ ] C24. A scored 300-household run with seed `SEED + 1` gives a different logical hash of the scored frame from the `SEED` run.
- [ ] C25. `tests/fixtures/golden/vendor.json` holds the seed, the household count 300, the logical hash of the scored frame, and the `vendor.score` tuple for the five lowest `person_id` values. A fresh scored run with that seed and count matches the hash exactly and each stored score within an absolute tolerance of 1e-12, with reason codes equal. The test fails, and does not skip, when the fixture is missing.

### CLI

- [ ] C26. `cli.main([])` with `config.SCALES` set so that `default` maps to 300 households, run in an empty working directory, returns 0. Its stdout lines equal exactly the default banner from Feature 001 B2, then `vendor`, `models`, `experiment`, `report`, `validate`, and `explain`, in that order. `data/processed/<run id>/application_features.parquet` has `external_score_1` non-null on every row. `explain.draft` is not called.
- [ ] C27. `python -m scorecheck` with no flag, in a subprocess with a 600-second timeout and an empty temporary working directory, exits 0. The first stdout line equals the default banner. The stdout lines after the first equal exactly `vendor`, `models`, `experiment`, `report`, `validate`, and `explain`, in that order. Every Feature 001 B47 assertion still holds, including the `vendor` stdout line. `application_features.parquet` in the run directory has `external_score_1` non-null and between 0 and 1 inclusive on every row, and `external_score_2` and `external_score_3` null on every row.

## Executable tests

Every automated test that will prove the checks above, named before any product code exists. The feature builder writes these first and may not weaken them.

Test command: `python -m pytest`, as recorded in `docs/testing-standards.md`. Core-module coverage adds `--cov=scorecheck.vendor`.

| Test | File | What it asserts | Proves check |
|---|---|---|---|
| test_public_names | tests/unit/test_vendor_api.py | Every non-underscore attribute of `scorecheck.vendor` is in {`REASON_CODES`, `score`, `write_scores`}. `__all__` equals that set. `from scorecheck.vendor import *` binds exactly those three. | C1 |
| test_no_booster_in_namespace | tests/unit/test_vendor_api.py | After a scored 300-household run in the same process, `score` and `write_scores` are functions, `REASON_CODES` is a tuple, and no other non-underscore attribute exists on `scorecheck.vendor`. Every non-underscore attribute of `scorecheck` is a submodule of `scorecheck`. | C2 |
| test_no_private_vendor_imports | tests/unit/test_vendor_api.py | Zero `.py` files under `src/scorecheck/` outside `vendor/` match `vendor\._\|from scorecheck\.vendor import[^\n]*\b_\|from scorecheck\.vendor\._`. | C3 |
| test_reason_code_tokens | tests/unit/test_vendor_api.py | `vendor.REASON_CODES == ("RC1", "RC2", "RC3")`. | C4 |
| test_score_shape | tests/unit/test_vendor_score.py | On a scored 300-household run, every person's `vendor.score` result is a 4-tuple. Element 0 is a finite `float` in [0, 1]. Elements 1 to 3 are pairwise distinct members of `REASON_CODES`. | C5 |
| test_reason_codes_vary | tests/unit/test_vendor_score.py | On a scored 300-household run, at least 2 distinct reason-code triples across persons. | C6 |
| test_unknown_person_raises | tests/unit/test_vendor_score.py | On a 300-household run, `vendor.score` with `max(person_id) + 1` raises `KeyError`. | C7 |
| test_score_has_no_feedback | tests/unit/test_vendor_score.py | On a 300-household run, `vendor.score` tuples for every person are equal before and after the vendor stage. | C8 |
| test_score_orientation | tests/unit/test_vendor_score.py | On the scored frame of a 2,000-household run, Spearman(`external_score_1`, `default_label`) is finite and < 0. | C9 |
| test_external_score_written | tests/unit/test_vendor_stage.py | On a scored 300-household run, `external_score_1` is non-null on every row and within 1e-12 of `vendor.score(run_dir, person_id)[0]`. `external_score_2` and `external_score_3` are null on every row. | C10 |
| test_scored_columns | tests/unit/test_vendor_stage.py | On a scored 300-household run, the scored frame's column set equals the 31 columns, and shares no name with `ground_truth` except `person_id`. | C11 |
| test_stage_changes_only_external_score_1 | tests/unit/test_vendor_stage.py | On a 300-household run, the logical hash of `application_features` without `external_score_1` is equal before and after the vendor stage. | C12 |
| test_stage_writes_no_new_file | tests/unit/test_vendor_stage.py | On a 300-household run, after the vendor stage the run directory's entries are exactly the eight Parquet files and `run_config.json`. The parent of the run directory gains no entry, and its other entries keep their hashes. The stage runs with `PYTHONDONTWRITEBYTECODE=1`. The repository map and the `sys.prefix` map from `pytest_configure` match, except files inside the run directory when that directory is inside the repository, and except a `.pyc` that unmarshals as code compiled from the neighboring tracked `.py`. | C13 |
| test_stage_idempotent | tests/unit/test_vendor_stage.py | On a 300-household run, two vendor stages in a row give equal logical hashes of the scored frame. | C14 |
| test_stage_returns_written_frame | tests/unit/test_vendor_stage.py | On a 300-household run, the logical hash of the frame `write_scores` returns equals the logical hash of the scored frame. | C15 |
| test_cli_never_reads_ground_truth | tests/unit/test_vendor_api.py | `src/scorecheck/cli.py` contains neither `ground_truth` nor `GROUND_TRUTH`. `inspect.signature(vendor.score)` has exactly the parameters `run_dir` and `person_id`, and `inspect.signature(vendor.write_scores)` has exactly `run_dir`. Zero `.py` files under `src/scorecheck/` contain `vendor_signal`, other than files under `vendor/` or `panel/`, `schema.py`, and `config.py`. | C16 |
| test_vendor_reads_only_application_time_truth | tests/unit/test_vendor_stage.py | The C17 rounds on a 300-household run. `pytest_configure` snapshots the repository and `sys.prefix` before test imports. Before the first round that snapshot may gain only a `.pyc` that unmarshals as code from the neighboring tracked `.py`, or a pytest cache path (`CACHEDIR.TAG`, `README.md`, `.gitignore`, `v/cache/`). A new or changed `.coverage` file fails. `COVERAGE_FILE` is the empty directory. A new file under `.venv`, `sys.prefix`, or `*.egg-info` fails. The seed is absent from the child environment. `panel.generate` runs in a new interpreter that has not imported `scorecheck.vendor`. The nine copied files are that output with only the `run_config.json` seed field replaced. No cell equals the generating seed. The run is generated with a 64-bit seed other than `config.SEED`, and the integers from 0 through 100000 do not find it. `panel.generate(config.SEED, 300)` does not reproduce the copied `ground_truth`. The source run is deleted before the child starts. One temporary root for the test, and its parent contains only that root. Each round's directory inside the root contains only the copy of the nine files. The parent does not call the vendor for that round. The child environment is a fresh map with `PYTHONDONTWRITEBYTECODE=1`. `USERPROFILE`, `HOME`, `APPDATA`, `LOCALAPPDATA`, and the temp variables are one empty directory outside the root, and `Path.home()` is that directory. An import hook fails the round if `scorecheck.panel` is imported or `panel.generate` is called. The round fails if that directory is non-empty, if the temporary root or its parent changes except `application_features.parquet` in the copy, or if the repository or `sys.prefix` hash map changes. Every invariance round, including `electricity_state`, leaves the scored-frame hash and the ordered reason-code triples equal to the baseline and changes the edited column's multiset. The `true_default` round raises the post-origination `true_default` sum. The control round changes the scored-frame hash. | C17 |
| test_draft_still_raises | tests/unit/test_cli.py | `explain.draft()` and `explain.draft("RC1", score=0.5)` each raise `RuntimeError`. `src/scorecheck/explain/` has `__init__.py` as its only `.py` file and no `policy` directory. | C18 |
| test_no_firm_entities_after_vendor | tests/unit/test_scope.py | On a scored 300-household run, zero run-directory file names and zero scored-frame column names match `firm\|msme\|business\|enterprise\|company`, case-insensitive. | C20 |
| test_no_real_names_in_vendor | tests/unit/test_scope.py | Zero lines in files under `src/scorecheck/vendor/`, and zero stdout lines from the C26 run, match `kayana\|\bmaya\b\|trusting social\|creditbpo\|\bglobe\b\|\bsmart\b\|\bdito\b\|gcash`, case-insensitive. The `README.md` part of C21 is checked by the reviewer on the diff. | C21 |
| test_scored_same_seed_same_hash | tests/unit/test_reproducibility.py | Two subprocess scored runs at 300 households, `PYTHONHASHSEED=0` and `PYTHONHASHSEED=1`, distinct output directories, give equal scored-frame logical hashes. | C23 |
| test_scored_second_seed_differs | tests/unit/test_reproducibility.py | At 300 households, a scored run at `SEED + 1` gives a different scored-frame logical hash from `SEED`. | C24 |
| test_golden_vendor | tests/unit/test_golden_vendor.py | `tests/fixtures/golden/vendor.json` exists with household count 300. A fresh scored run matches the stored scored-frame hash exactly, each stored score within 1e-12, and each stored reason-code triple exactly. A missing fixture fails the test. | C25 |
| test_main_prints_banner_then_stages | tests/unit/test_cli.py | Existing test, updated. `config.SCALES` default set to 300. `cli.main([])` returns 0. Stdout lines equal `[banner, "vendor", "models", "experiment", "report", "validate", "explain"]`. `external_score_1` is non-null on every row of the written `application_features.parquet`. `explain.draft` is patched to fail the test if called. | C26, Completeness |
| test_cli_default_run | tests/integration/test_cli_run.py | Existing test, updated. Same 600-second subprocess run. The stdout lines after the banner equal `["vendor", "models", "experiment", "report", "validate", "explain"]` in order. Every Feature 001 B47 assertion is kept, including the `vendor` line. `external_score_1` is non-null and in [0, 1] on every row. `external_score_2` and `external_score_3` are null on every row. | C27, Completeness |

C19, C22, and C28 are reviewer checks on the diff. No test can prove the absence of a claim or of policy wording.

Required kinds, per `docs/testing-standards.md`:

- Unit: the `tests/unit/` rows above. Fixtures that train the vendor are module-scoped so each test file trains at most once per household count. `test_vendor_reads_only_application_time_truth` does not use a scored fixture. Each of its rounds fits only inside that round's process. `pytest_configure` snapshots the repository and `sys.prefix` before imports. A new or changed `.coverage` file, a new file under `.venv` or `sys.prefix`, and a `.pyc` that is not code compiled from the neighboring `.py`, fails that test before the first round. `panel.generate` for this test runs in an interpreter that has not imported `scorecheck.vendor`. The copied run is not regenerable with `config.SEED`, and no copied cell equals the generating seed. The source run is deleted before each child starts.
- Golden dataset: `test_golden_vendor`. The feature builder writes `tests/fixtures/golden/vendor.json` after the other vendor tests pass, with a script beside `scripts/write_golden_panel.py`, and adds a line to `tests/fixtures/golden/CHANGELOG.md`. This commit does not add the fixture.
- Eval case: `tests/evals/test_vendor_ranking.py` records the in-sample AUC of `external_score_1` against `default_label` on a scored 2,000-household run, oriented so that higher score means lower risk, and asserts it is above 0.5. Advisory until v1. It proves no check on its own and is never compared against any challenger.
- Integration: `test_cli_default_run`, in the integration suite. It must still finish inside its 600-second timeout with the vendor stage included.
- Coverage: `src/scorecheck/vendor/` has at least 80% line coverage under the unit suite.

## Integration

- [ ] `python -m scorecheck` calls `vendor.write_scores` on the run directory after `features.from_panel` and before it prints the `vendor` line, in the same change that makes the behavior checks pass. The vendor stage runs on every default and full run.
- [ ] The gradient-boosting library the vendor uses is listed in `requirements.txt` and in `pyproject.toml` dependencies, and is configured for single-threaded, seeded, deterministic fitting per `docs/design.md` section 2 Invariants.
- [ ] `README.md` says the default command fills `external_score_1` with a simulated vendor score, and lists the six stage lines in order: `vendor`, `models`, `experiment`, `report`, `validate`, and `explain`. `docs/testing-standards.md` adds `--cov=scorecheck.vendor` to the coverage command.

## Regression

- [ ] Feature 001 check B47 stands in full. This feature does not supersede any B47 clause. The `vendor` stdout line stays, and C26 and C27 keep it in its Feature 001 position after the banner and before `models`. `checks/approved/feature-001.md` is not edited.
- [ ] `features.from_panel` is unchanged. It still leaves `external_score_1`, `external_score_2`, and `external_score_3` null on every row, so the locked B36 test `test_vendor_columns_null` keeps passing unchanged. Feature 001 checks B31 to B39 still pass on the frame it returns. The vendor stage, run after it as a separate step, is what fills `external_score_1`.
- [ ] `test_golden_panel` passes with `tests/fixtures/golden/panel.json` unchanged and no new `CHANGELOG.md` line for it.
- [ ] Every other Feature 001 test passes unchanged.

## Completeness

- [ ] A person runs `python -m scorecheck` from the repo root after `pip install -r requirements.txt`. They see the default banner, then `vendor`, `models`, `experiment`, `report`, `validate`, and `explain`. They open `data/processed/<run id>/application_features.parquet` and find `external_score_1` filled on every row. A passing unit test alone does not satisfy this check.
