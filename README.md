# YouTube Playlist Organizer

![Coverage Badge](badges/coverage.svg)

This project helps you clean up and reorganize your YouTube playlists.

It supports both:

1. A terminal workflow
2. A simple local web UI for non terminal users

The tool is designed to be cautious.

By default:

1. It exports your playlist data locally.
2. It builds a review plan.
3. It previews changes before anything is applied.
4. It requires explicit confirmation before live YouTube writes.

## What It Can Do

This project can:

1. Detect duplicate videos across playlists
2. Detect deleted video entries
3. Merge playlists with duplicate or aliased titles
4. Suggest broader reorganization moves without auto applying them by default
5. Export review files for terminal, Markdown, JSON, and Excel style review
6. Run through a local web UI if you do not want to use the terminal

## Safety Model

This project does not change YouTube automatically.

Safe behavior by default:

1. `export` only downloads data
2. `analyze` only writes local review files
3. `apply` is a dry run unless you type `APPLY`

Important:

1. There is no built in undo
2. Suggested category moves are review only unless you explicitly include them in the apply plan
3. You should always review the generated files before a live apply

## Project Tracking Files

These root files track project state:

1. `changelogs.md`
2. `future-upgrades.md`
3. `completed-upgrades.md`

## Quick Start

If you want the shortest working path:

```powershell
pip install -r requirements.txt
python -m src.cli auth
python -m src.cli export
python -m src.cli analyze
python -m src.cli apply
```

Then review:

1. `data/playlist-report.md`
2. `data/playlist-plan.json`
3. `data/playlist-review.csv`

If the preview looks correct:

```powershell
python -m src.cli auth --write WRITE
python -m src.cli apply --confirm APPLY
```

## Requirements

You need:

1. Python 3.11 or newer
2. A Google account that owns the playlists
3. A Google Cloud project with YouTube Data API v3 enabled
4. OAuth desktop credentials saved as `client_secret.json`

## Repo Layout

```text
youtube-playlist-organizer/
|   .env.example
|   client_secret.json
|   token.json
|   README.md
|   requirements.txt
|   pytest.ini
|
+---badges
|       coverage.svg
|
+---config
|       playlist-rules.json
|
+---data
|       playlist-plan.json
|       playlist-report.md
|       playlist-review.csv
|       playlist_items.csv
|       playlists.csv
|       playlists.json
|
+---scripts
|       generate_coverage_badge.py
|
+---src
|   |   cli.py
|   |
|   +---analysis
|   +---api
|   +---auth
|   +---export
|   +---models
|   \---webui
|
+---tests
|
\---.github
    \---workflows
            ci.yml
```

## First Time Setup

### 1. Open the repo

Example:

```powershell
cd "C:\Users\mick0\OneDrive\Documents\Code & Dev\GitHub\youtube-playlist-organizer"
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Create Google credentials

You need `client_secret.json`.

Steps:

1. Open [Google Cloud Console](https://console.cloud.google.com)
2. Create or select a project
3. Open **APIs & Services**
4. Open **Library**
5. Enable **YouTube Data API v3**
6. Open **OAuth consent screen** or **Google Auth Platform**
7. Create the consent screen
8. Add your Google account as a test user
9. Create an OAuth client
10. Choose **Desktop app**
11. Download the JSON
12. Save it in the repo root as `client_secret.json`

If you skip the test user step, Google may block the auth flow.

### 4. Optional `.env`

If you want local overrides:

```powershell
Copy-Item .env.example .env
```

Default values:

```env
CLIENT_SECRET_FILE=client_secret.json
TOKEN_FILE=token.json
```

## Main Workflow

The normal order is:

1. Authenticate
2. Export
3. Analyze
4. Review
5. Preview apply
6. Apply only if correct

### Step 1. Authenticate read only

```powershell
python -m src.cli auth
```

This:

1. Opens the browser auth flow
2. Requests read only access
3. Saves `token.json`

Read only access is enough for:

1. `list`
2. `export`
3. `analyze`
4. `apply` preview
5. `ui` until you choose live apply

### Step 2. Optional playlist list

```powershell
python -m src.cli list
```

This is just a quick terminal check that auth is working and playlists are visible.

### Step 3. Export playlists

```powershell
python -m src.cli export
```

This writes:

1. `data/playlists.json`
2. `data/playlists.csv`
3. `data/playlist_items.csv`

Use cases:

1. `playlists.json` is the main analysis input
2. `playlists.csv` is a simple playlist summary
3. `playlist_items.csv` is a flat per item export

### Step 4. Analyze playlists

```powershell
python -m src.cli analyze
```

This:

1. Reads `data/playlists.json`
2. Detects duplicate videos
3. Detects deleted entries
4. Detects duplicate or aliased playlist titles for merge review
5. Generates suggested category moves
6. Writes review artifacts

Files written:

1. `data/playlist-plan.json`
2. `data/playlist-report.md`
3. `data/playlist-review.csv`

### Step 4a. Review the rule config

The current behavior is driven by:

`config/playlist-rules.json`

This config currently controls:

1. `privacy_defaults`
2. `keep_rules`
3. `playlist_merge_preferences`
4. `playlist_aliases`
5. `token_aliases`
6. `category_rules`

That means you can change:

1. Default privacy for created playlists
2. Which playlist titles are preferred when duplicates are kept
3. Privacy preference order for duplicate keep decisions
4. Merge behavior for aliased playlist names
5. Category matching rules

YAML is also supported:

```powershell
python -m src.cli analyze --rules-config config/playlist-rules.yaml
```

### Step 5. Review the outputs

Read these before any live apply:

1. `data/playlist-report.md`
2. `data/playlist-plan.json`
3. `data/playlist-review.csv`

What each is for:

1. `playlist-report.md` is the human readable review summary
2. `playlist-plan.json` is the machine readable plan used by `apply`
3. `playlist-review.csv` is the spreadsheet friendly review export

### Step 6. Preview apply

```powershell
python -m src.cli apply
```

This is still a dry run.

It:

1. Reads the plan
2. Shows action counts
3. Estimates quota cost
4. Prints a preview table
5. Makes no live changes

### Step 7. Authenticate write access

Only do this when you are ready for live YouTube writes.

```powershell
python -m src.cli auth --write WRITE
```

If write access still fails:

1. Delete `token.json`
2. Run the write auth command again

### Step 8. Apply for real

```powershell
python -m src.cli apply --confirm APPLY
```

This can:

1. Remove duplicate playlist items
2. Remove deleted entries
3. Merge duplicate or aliased playlists
4. Optionally move videos into more specific playlists if you included category moves in the plan

## Local Web UI

If you do not want to use the terminal, start the local web UI:

```powershell
python -m src.cli ui
```

Default URL:

`http://127.0.0.1:8765`

UI features:

1. Read only auth
2. Write auth
3. Export
4. Analyze
5. Apply preview
6. Confirmed live apply
7. Open generated review files
8. Download the plan, report, and review CSV
9. Group suggested moves by source and target playlist
10. Group overlap review into useful sections
11. Inline filtering for move and overlap review rows

Useful options:

```powershell
python -m src.cli ui --port 9000
python -m src.cli ui --no-browser
```

## Optional Aggressive Reorganization Mode

By default, category moves stay out of the apply plan.

If you want them included:

```powershell
python -m src.cli analyze --include-category-moves
```

Use this only after review.

When enabled, the apply plan may include:

1. `move_to_playlist`
2. `create_playlist`

## Safe Default Behavior

If you do not pass extra flags:

1. `analyze` builds a conservative plan
2. Suggested category moves stay in the review outputs
3. `apply` remains preview only
4. `apply --confirm APPLY` only performs the queued safe actions

## Command Reference

### `auth`

```powershell
python -m src.cli auth
python -m src.cli auth --write WRITE
```

### `list`

```powershell
python -m src.cli list
```

### `export`

```powershell
python -m src.cli export
python -m src.cli export --output-dir data
```

### `analyze`

```powershell
python -m src.cli analyze
python -m src.cli analyze --include-category-moves
python -m src.cli analyze --rules-config config/playlist-rules.json
python -m src.cli analyze --input-json data/playlists.json --plan-output data/playlist-plan.json --report-output data/playlist-report.md --review-csv-output data/playlist-review.csv
```

### `apply`

```powershell
python -m src.cli apply
python -m src.cli apply --confirm APPLY
```

### `ui`

```powershell
python -m src.cli ui
```

## Current Output Files

Local auth files:

1. `client_secret.json`
2. `token.json`

Export and review files:

1. `data/playlists.json`
2. `data/playlists.csv`
3. `data/playlist_items.csv`
4. `data/playlist-plan.json`
5. `data/playlist-report.md`
6. `data/playlist-review.csv`

## Current Action Types

Default safe actions:

1. `remove_duplicate`
2. `remove_deleted`
3. `merge_playlist`

Optional actions if category moves are enabled:

1. `move_to_playlist`
2. `create_playlist`

## Tests and CI

Local validation:

```powershell
python -m ruff check src tests scripts
python -m pytest
```

CI currently does all of this:

1. Runs on push
2. Runs on pull request
3. Uses pip caching
4. Runs `ruff`
5. Runs `pytest` with coverage
6. Produces coverage XML and HTML
7. Uploads coverage artifacts
8. Generates `badges/coverage.svg`
9. Publishes the badge on the default branch
10. Writes a CI status summary that names the broken step directly if something fails

## Quota Notes

YouTube Data API quota is the main operational limit.

Typical costs:

1. `playlists.list` costs 1 unit
2. `playlistItems.list` costs 1 unit
3. `playlistItems.insert` costs 50 units
4. `playlistItems.delete` costs 50 units
5. `playlists.insert` costs 50 units
6. `playlists.delete` costs 50 units

Practical meaning:

1. Removing one playlist item costs 50 units
2. Moving one video is usually about 100 units
3. Deleting a merged duplicate playlist costs 50 units

Always preview before live apply.

## Troubleshooting

### Missing `client_secret.json`

Cause:

The OAuth credentials file is missing.

Fix:

1. Download the Google desktop OAuth credentials JSON
2. Save it as `client_secret.json` in the repo root

### Google blocks or warns on auth

Cause:

Your Google account is not a configured test user.

Fix:

1. Open the OAuth consent screen settings
2. Add your Google account as a test user
3. Run auth again

### `apply` still behaves as read only

Cause:

The saved token does not have write scope.

Fix:

1. Delete `token.json`
2. Run `python -m src.cli auth --write WRITE`

### `ModuleNotFoundError`

Cause:

Dependencies are missing.

Fix:

```powershell
pip install -r requirements.txt
```

### `quotaExceeded`

Cause:

The daily YouTube API quota was used up.

Fix:

1. Stop the run
2. Wait for quota reset
3. Export again
4. Analyze again
5. Review again

## Beginner Checklist

If you want the simplest checklist:

1. Put `client_secret.json` in the repo root
2. Run `pip install -r requirements.txt`
3. Run `python -m src.cli auth`
4. Run `python -m src.cli export`
5. Run `python -m src.cli analyze`
6. Read `data/playlist-report.md`
7. Run `python -m src.cli apply`
8. If the preview looks right, run `python -m src.cli auth --write WRITE`
9. Run `python -m src.cli apply --confirm APPLY`

## License

MIT. See [LICENSE](LICENSE).
