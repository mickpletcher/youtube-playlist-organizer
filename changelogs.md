# Changelogs

## 2026-05-21

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
