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
