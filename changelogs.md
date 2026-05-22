# Changelogs

## 2026-05-21

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
