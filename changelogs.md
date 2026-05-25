# Changelogs

## 2026-05-25

### Saved review decisions

1. Added stable `decision_key` values and editable `review_status` fields to generated review CSV rows.
2. Added `save-decisions` so approved and rejected review rows can be saved to `data/review-decisions.json`.
3. Updated `analyze` to load saved decisions by default.
4. Approved category moves are queued in future plans even when `--include-category-moves` is not used.
5. Rejected category moves are skipped in future plans.
6. Added `decide` so one category suggestion can be approved or rejected by `decision_key`.
7. Added tests for decision import and planner behavior.
8. Removed the completed saved decision and review status items from `future-upgrades.md`.

### Review and planning controls

1. Added analyze filters for duplicate cleanup, deleted video cleanup, playlist merges, and category suggestions.
2. Added grouped move review output at `data/playlist-move-review.md`.
3. Added weighted negative keyword support for category rules.
4. Added `validate-config` to catch rule structure and preference errors before analyze.
5. Added automatic rollback snapshots before confirmed live apply.
6. Added collapsed review groups in the local web UI for large suggested move and overlap datasets.
7. Added source and target playlist allowlists and blocklists for category suggestions.
8. Added optional HTML report export at `data/playlist-report.html`.
9. Added `plan-summary` for compact action counts, quota estimate, decision counts, and output paths.
10. Added tests for filters, config validation, negative keyword behavior, move review output, rollback snapshots, UI command routing, playlist filters, HTML export, and plan summaries.
11. Removed the completed filter, confirmation, move review, rollback, negative keyword, config validation, UI scale, playlist filter, HTML report, and plan summary items from `future-upgrades.md`.

### Quota safe apply runs

1. Added `--max-quota-cost` to `apply` so large plans can be previewed and applied in smaller quota bounded chunks.
2. Added clear `quotaExceeded` handling around YouTube API calls so the CLI reports partial progress instead of dumping the raw Google exception.
3. Updated apply recovery guidance to tell users not to rerun an old plan after a partial apply.
4. Added CLI tests for quota chunk selection and apply preview output.

### Quota documentation

1. Documented that YouTube Data API quota resets at midnight Pacific Time.
2. Documented that playlist item insert, update, and delete operations each cost 50 quota units.
3. Added guidance for chunking large reorganizations, re-exporting after every live chunk, and avoiding API key or project rotation as a quota workaround.
4. Updated the upgrade tracking files so shipped quota work is in `completed-upgrades.md` and only the remaining hard ceiling behavior stays in `future-upgrades.md`.

## 2026-05-21

### Liked video self image review

1. Added export support for the YouTube liked videos playlist when it is available on the authenticated account.
2. Added configurable liked video self image review rules to `config/playlist-rules.json`.
3. Added review only liked video flags with scores and reasons to the generated plan, markdown report, and CSV review export.

### CI workflow hardening

1. Updated the workflow to `actions/checkout@v5` and `actions/setup-python@v6` to avoid the Node 20 deprecation warning shown by GitHub Actions.
2. Added persisted CI log files for `ruff`, `pytest`, and coverage badge generation so failed runs keep the command output as artifacts.
3. Expanded the GitHub job summary to include the broken step plus a tail of the failing command output.
4. Set `asyncio_default_fixture_loop_scope = function` in `pytest.ini` so the test suite runs without the pytest asyncio scope warning.

### UI review improvements

1. Added grouped suggested move tables by source and target playlist in the local web UI.
2. Added grouped overlap review tables in the local web UI.
3. Added inline filtering for move and overlap review rows.
4. Added one click download links for the report, review CSV, and plan JSON.

### CI failure summaries

1. Updated the CI workflow so lint and test steps can complete their status reporting before the job fails.
2. Added a GitHub step summary section that calls out the exact broken step directly.
3. Kept the job failing when required steps do not pass so branch protection still works.

### Local web UI

1. Added a simple localhost web UI that wraps the existing CLI workflow for non terminal users.
2. Added UI actions for authentication, export, analyze, apply preview, and confirmed live apply.
3. Added file viewing links for the generated plan, report, review CSV, and config file.

### Coverage reporting

1. Added coverage reporting to CI with terminal, XML, and HTML outputs.
2. Added a badge generator script that builds `badges/coverage.svg` from `coverage.xml`.
3. Added coverage artifact uploads and default branch badge publishing in GitHub Actions.
4. Enabled pip caching in the CI workflow.

### Quality and CI

1. Added automated tests for rule loading, rule matching, planner decisions, and dry run apply preview behavior.
2. Added `pytest.ini` so the test suite runs predictably from the repo root.
3. Added a GitHub Actions workflow in `.github/workflows/ci.yml` to run `ruff` and `pytest` on push and pull request.
4. Added `pytest` and `ruff` to project dependencies for repeatable local and CI validation.

### Planner configuration

1. Added config sections for `privacy_defaults`, `keep_rules`, and `playlist_merge_preferences`.
2. Updated duplicate keep selection to respect configured preferred playlist titles and privacy order.
3. Updated category move planning to use configured default privacy when creating missing playlists.
4. Updated merge target selection to respect configured merge preferences.

### Rule configuration and matching

1. Replaced hardcoded category rules with config driven rules loaded from `config/playlist-rules.json`.
2. Added JSON and YAML rule loading support.
3. Added playlist title normalization and alias support so near duplicate playlists such as `RV` and `RVing` can merge.
4. Added token alias support for plural and shorthand title normalization.

### Review outputs

1. Added confidence scores, confidence labels, and detailed reasons to suggested category moves.
2. Added `data/playlist-review.csv` for Excel friendly review.
3. Added rules config path tracking to the generated plan and markdown report.
4. Expanded the markdown review report to include confidence details for reorganization suggestions.

### Repo hygiene

1. Updated ignore rules so `future-upgrades.md` is not committed.
2. Verified `token.json` is already ignored and not tracked.
3. Added `prompts/` to ignore rules to prevent prompt files from future commits.
4. Updated dependency pins to avoid resolver conflicts by requiring `pydantic>=2.11.0,<3` and `rich>=14.2.0,<15`.
5. Bumped `pandas` to `2.2.3` so dependency installs on Python 3.13 can use prebuilt wheels.
6. Fixed OAuth refresh handling to recover from `invalid_scope` by forcing clean reauth and by validating token scope coverage before reuse.

### Analyzer and planning

1. Added a safer analysis flow that separates default cleanup actions from broader reorganization suggestions.
2. Added duplicate playlist title merge planning.
3. Added overlap review output for playlist compaction candidates.
4. Added category move suggestion review output without auto queueing those moves by default.
5. Added markdown report generation to make review easier before any live apply.

### Apply flow

1. Kept `apply` as dry run by default.
2. Added support for applying duplicate playlist merges.
3. Added quota cost estimation that covers the expanded action set.
4. Added preview output for the expanded plan types.

### API and repo structure

1. Added playlist delete support in the YouTube API wrapper.
2. Added `data/.gitkeep` so the data folder can stay in the repo without committing exports.
3. Tightened `.gitignore` for secrets and generated export or report files.

### Documentation

1. Rewrote `README.md` for novice users.
2. Documented first time setup, Google credential setup, safe review workflow, and optional aggressive reorganization mode.
3. Added project tracking files for changelog, future upgrades, and completed upgrades.
4. Documented the rule config file, local lint and test commands, and the GitHub Actions CI workflow.
5. Documented the optional local web UI and coverage badge workflow.
6. Refreshed the README so it reflects the full current product surface instead of the earlier incremental state.
