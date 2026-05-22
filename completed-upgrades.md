# Completed Upgrades

## Core workflow

1. Built read only and write capable OAuth authentication commands.
2. Built playlist listing support.
3. Built playlist export to JSON and CSV.
4. Built dry run apply behavior with explicit `--confirm APPLY` required for live changes.

## Cleanup and organization logic

1. Added duplicate video detection across playlists.
2. Added deleted video detection and removal planning.
3. Added duplicate playlist title merge planning.
4. Added broader category move suggestions for review.
5. Added overlap analysis for compaction review.
6. Added config driven category matching through JSON rules with YAML support.
7. Added playlist title normalization and alias support for near duplicate playlist names.
8. Added confidence scores and detailed reasons for category move suggestions.
9. Added review only liked video self image flagging based on configurable keywords and score thresholds.

## Apply implementation

1. Added duplicate playlist item removal.
2. Added deleted video entry removal.
3. Added playlist merge apply support.
4. Added optional category move apply support when category moves are included in the plan.
5. Added playlist creation and playlist deletion support through the API wrapper.

## Documentation and safety

1. Added a human readable markdown review report.
2. Rewrote the README for novice users with step by step instructions.
3. Added stronger `.gitignore` coverage for secrets and generated files.
4. Added `data/.gitkeep` to preserve the expected folder structure.
5. Added a CSV review export for easier sorting and review in Excel.
6. Added `pytest.ini` and documented local test and lint commands.
7. Updated the README to document the rule config file, CI workflow, and spreadsheet review export.
8. Added README documentation for the optional local web UI and coverage badge workflow.
9. Added README documentation for CI failure summaries and richer UI review features.
10. Refreshed the README into a full current state guide covering CLI, UI, config, outputs, tests, CI, and safety behavior.

## Configuration and outputs

1. Added `config/playlist-rules.json` as the shipped rule and alias configuration file.
2. Added support for writing `data/playlist-review.csv` during analyze.
3. Added reporting of confidence labels, confidence scores, and confidence reasons in the review output.
4. Added config sections for privacy defaults, keep rules, and playlist merge preferences.

## Quality and automation

1. Added automated tests for planner behavior, rule matching, and apply preview behavior.
2. Added a GitHub Actions CI workflow to run `ruff` and `pytest` on push and pull request.
3. Added `ruff` and `pytest` to the project dependencies for local and CI validation.
4. Verified the new test suite, linting, and analyze flow locally after the changes.
5. Added coverage reporting, coverage artifact upload, cached dependency installs, and badge publishing in CI.
6. Added CI step summaries that explicitly call out which required step failed.
7. Added CI log capture and summary excerpts so failed runs show the broken step and recent command output directly in the job summary.

## User interfaces

1. Added an optional local web UI for non terminal users.
2. Added UI coverage for auth, export, analyze, apply preview, and confirmed live apply through the existing CLI commands.
3. Added simple UI command builder tests.
4. Added grouped review tables, inline filters, and one click downloads for generated review files.
