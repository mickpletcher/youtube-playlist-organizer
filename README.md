# YouTube Playlist Organizer

This tool helps you clean up and reorganize your YouTube playlists.

It does three main jobs:

1. Exports your current playlists and videos so you can inspect them locally.
2. Builds a cleanup plan and a review report.
3. Applies changes to YouTube only when you explicitly approve them.

If you are new to Python, APIs, or command line tools, start at **Quick Start** and follow the steps in order.

## Project Tracking Files

These files track project history and next steps:

1. `changelogs.md`
2. `future-upgrades.md`
3. `completed-upgrades.md`

## What This Tool Is Good For

Use this tool if you have a lot of saved playlists and want to:

1. Remove duplicate videos that are saved in more than one playlist.
2. Remove entries for deleted videos.
3. Merge duplicate playlists that have the same title.
4. Review suggestions for broader reorganization before doing anything live.

This tool is built to be cautious.

By default:

1. `analyze` creates files for review.
2. `apply` only previews the plan.
3. Nothing changes on YouTube until you run `apply --confirm APPLY`.

## What This Tool Does Not Do

1. It does not change YouTube automatically.
2. It does not undo changes after they are applied.
3. It does not guarantee that every suggested reorganization is correct.
4. It does not auto queue broad category moves unless you explicitly opt in.

## Quick Start

If you want the shortest path, do this:

```powershell
pip install -r requirements.txt
python -m src.cli auth
python -m src.cli export
python -m src.cli analyze
python -m src.cli apply
```

Then review these two files:

1. `data/playlist-report.md`
2. `data/playlist-plan.json`

If the preview looks correct, request write access and apply:

```powershell
python -m src.cli auth --write WRITE
python -m src.cli apply --confirm APPLY
```

## Before You Start

You need these things:

1. Python 3.11 or newer installed on your computer.
2. A Google account that owns the YouTube playlists you want to manage.
3. A Google Cloud project with the YouTube Data API v3 enabled.
4. An OAuth desktop credentials file named `client_secret.json` in the repo root.

## Folder Overview

These are the files and folders most users need to care about:

```text
youtube-playlist-organizer/
|   .env.example
|   client_secret.json          <- you add this
|   token.json                  <- created after auth
|   README.md
|   requirements.txt
|
+---data
|       playlist-plan.json      <- machine readable action plan
|       playlist-report.md      <- human readable review report
|       playlist_items.csv      <- exported video list
|       playlists.csv           <- exported playlist list
|       playlists.json          <- full export used by analyze
|
\---src
        cli.py                  <- main command line entry point
```

## First Time Setup

### 1. Open a terminal in this repo

Examples:

```powershell
cd "C:\Users\mick0\OneDrive\Documents\Code & Dev\GitHub\youtube-playlist-organizer"
```

### 2. Install Python packages

Run:

```powershell
pip install -r requirements.txt
```

If this fails, check that Python and `pip` are installed and available in your terminal.

### 3. Create Google API credentials

You need `client_secret.json` from Google.

Do this:

1. Go to [Google Cloud Console](https://console.cloud.google.com).
2. Create a project or select an existing project.
3. Open **APIs & Services**.
4. Open **Library**.
5. Enable **YouTube Data API v3**.
6. Open **OAuth consent screen** or **Google Auth Platform**.
7. Create a consent screen.
8. Add your Google account as a test user.
9. Create an OAuth client.
10. Choose **Desktop app**.
11. Download the JSON file.
12. Rename it to `client_secret.json` if needed.
13. Place it in the root of this repo.

If you skip the test user step, Google may block the login flow.

### 4. Optional local config

You usually do not need this step, but it is available.

If you want a local `.env` file:

```powershell
Copy-Item .env.example .env
```

Default values:

```env
CLIENT_SECRET_FILE=client_secret.json
TOKEN_FILE=token.json
```

## Main Workflow

This is the normal order:

1. Authenticate
2. Export
3. Analyze
4. Review
5. Preview
6. Apply only if the plan is correct

### Step 1. Authenticate in read only mode

Run:

```powershell
python -m src.cli auth
```

What this does:

1. Opens a browser login flow.
2. Lets you approve read only access to your YouTube account.
3. Saves a local `token.json` file.

Read only mode is enough for:

1. `list`
2. `export`
3. `analyze`
4. `apply` preview mode

### Step 2. List your playlists

This step is optional, but useful as a quick check.

Run:

```powershell
python -m src.cli list
```

What this does:

1. Connects to YouTube.
2. Lists your playlists in the terminal.
3. Shows the playlist names and counts.

### Step 3. Export your playlists

Run:

```powershell
python -m src.cli export
```

What this does:

1. Downloads all your playlists.
2. Downloads all playlist items.
3. Saves the results into the `data` folder.

Files created:

1. `data/playlists.json`
2. `data/playlists.csv`
3. `data/playlist_items.csv`

What each file is for:

1. `playlists.json` is the main input for analysis.
2. `playlists.csv` is a simple spreadsheet style playlist summary.
3. `playlist_items.csv` is a flat list of all playlist items.

### Step 4. Analyze your playlists

Run:

```powershell
python -m src.cli analyze
```

What this does:

1. Reads `data/playlists.json`.
2. Finds duplicate videos across playlists.
3. Finds deleted video entries.
4. Finds duplicate titled playlists that can be merged.
5. Generates review only reorganization suggestions.
6. Writes output files for review.

Files created:

1. `data/playlist-plan.json`
2. `data/playlist-report.md`

What each file is for:

1. `playlist-plan.json` is the action plan used by `apply`.
2. `playlist-report.md` is the review document meant for humans.

### Step 5. Review the proposed changes

This is the most important safety step.

Open and read:

1. `data/playlist-report.md`
2. `data/playlist-plan.json`

The report explains:

1. What the safe plan will do automatically.
2. Which broader reorganization ideas are only suggestions.
3. Which playlist pairs may need manual review because they overlap.

Important:

1. The default plan is conservative.
2. Broad category moves are not included in the apply plan unless you opt in.

### Step 6. Preview the apply plan in the terminal

Run:

```powershell
python -m src.cli apply
```

This is still a dry run.

What it does:

1. Loads `data/playlist-plan.json`.
2. Shows how many actions are planned.
3. Estimates quota cost.
4. Prints a preview table.
5. Makes no live changes.

If the output is wrong, stop here and do not apply.

### Step 7. Authenticate with write access

Only do this when you are ready to make live changes.

Run:

```powershell
python -m src.cli auth --write WRITE
```

What this does:

1. Requests YouTube write access.
2. Replaces or refreshes the local token so apply can make changes.

If it still behaves like read only access:

1. Delete `token.json`
2. Run `python -m src.cli auth --write WRITE` again

### Step 8. Apply the plan for real

Run:

```powershell
python -m src.cli apply --confirm APPLY
```

This is the command that makes live YouTube changes.

It can:

1. Remove duplicate playlist items.
2. Remove deleted video entries.
3. Merge playlists with the same title.

## Optional Aggressive Reorganization Mode

By default, broad category based moves are review only.

If you want the tool to include those moves in the apply plan, run:

```powershell
python -m src.cli analyze --include-category-moves
```

Use this only after reviewing the report and deciding the suggestions are good enough.

When enabled, the apply plan may also include:

1. `move_to_playlist`
2. `create_playlist`

That means the tool may:

1. Move videos from broad playlists into more specific ones.
2. Create destination playlists if they do not exist.

## Safe Default Behavior

If you run the normal workflow without extra flags:

1. `analyze` creates a safe plan.
2. Suggested category moves stay in the report only.
3. `apply` previews only.
4. `apply --confirm APPLY` performs only the safe plan actions.

## Command Reference

### `auth`

Read only auth:

```powershell
python -m src.cli auth
```

Write auth:

```powershell
python -m src.cli auth --write WRITE
```

### `list`

```powershell
python -m src.cli list
```

### `export`

```powershell
python -m src.cli export
```

Custom output directory:

```powershell
python -m src.cli export --output-dir data
```

### `analyze`

Default safe analysis:

```powershell
python -m src.cli analyze
```

Include category moves:

```powershell
python -m src.cli analyze --include-category-moves
```

Custom input and output files:

```powershell
python -m src.cli analyze --input-json data/playlists.json --plan-output data/playlist-plan.json --report-output data/playlist-report.md
```

### `apply`

Preview only:

```powershell
python -m src.cli apply
```

Real apply:

```powershell
python -m src.cli apply --confirm APPLY
```

## What Gets Written To Disk

Local auth files:

1. `client_secret.json`
2. `token.json`

Export and analysis files:

1. `data/playlists.json`
2. `data/playlists.csv`
3. `data/playlist_items.csv`
4. `data/playlist-plan.json`
5. `data/playlist-report.md`

## Understanding the Output Files

### `data/playlists.json`

Full exported playlist data.

Use it when:

1. You want the raw source data.
2. You want to re run analysis without exporting again.

### `data/playlists.csv`

One row per playlist.

Use it when:

1. You want a simple summary.
2. You want to sort playlists in Excel.

### `data/playlist_items.csv`

One row per playlist item.

Use it when:

1. You want a flat spreadsheet of every saved video.
2. You want to inspect titles, playlist names, and positions.

### `data/playlist-plan.json`

Machine readable action plan.

This is the file `apply` uses.

### `data/playlist-report.md`

Human readable review report.

This is the file you should read before applying changes.

## Current Action Types

Default safe actions:

1. `remove_duplicate`
2. `remove_deleted`
3. `merge_playlist`

Optional actions when category moves are enabled:

1. `move_to_playlist`
2. `create_playlist`

## Quota and Cost Notes

The YouTube Data API uses quota units.

This matters because very large cleanup plans can hit the daily quota limit.

Typical costs:

1. `playlists.list` costs 1 unit.
2. `playlistItems.list` costs 1 unit.
3. `playlistItems.insert` costs 50 units.
4. `playlistItems.delete` costs 50 units.
5. `playlists.insert` costs 50 units.
6. `playlists.delete` costs 50 units.

Practical meaning:

1. Removing one playlist item costs 50 units.
2. Moving one video usually costs about 100 units.
3. Deleting one merged duplicate playlist costs 50 units.

Always run the dry run preview first so you can see the estimated quota cost.

## Safety Rules

Follow these rules every time:

1. Export before analyzing.
2. Analyze before applying.
3. Read `data/playlist-report.md`.
4. Run `python -m src.cli apply` before any real apply.
5. Do not run `apply --confirm APPLY` unless the plan looks correct.

There is no built in undo.

## Common Problems

### Problem: `Not found: client_secret.json`

Cause:

The Google OAuth credentials file is missing.

Fix:

1. Download the desktop OAuth credentials JSON from Google Cloud.
2. Save it as `client_secret.json` in the repo root.

### Problem: Google says the app is blocked or unverified

Cause:

Your Google account is not listed as a test user in the Google Cloud project.

Fix:

1. Open the OAuth consent screen settings.
2. Add your Google account as a test user.
3. Run auth again.

### Problem: `apply` fails because the token is read only

Cause:

You authenticated in read only mode first.

Fix:

1. Delete `token.json`
2. Run `python -m src.cli auth --write WRITE`

### Problem: `ModuleNotFoundError`

Cause:

Required Python packages are not installed.

Fix:

```powershell
pip install -r requirements.txt
```

### Problem: `quotaExceeded`

Cause:

The YouTube API daily quota was exhausted.

Fix:

1. Stop the run.
2. Wait for quota reset.
3. Export again.
4. Analyze again.
5. Review again.

## Example Beginner Workflow

If you want a plain checklist, use this:

1. Put `client_secret.json` in the repo root.
2. Run `pip install -r requirements.txt`
3. Run `python -m src.cli auth`
4. Run `python -m src.cli export`
5. Run `python -m src.cli analyze`
6. Open `data/playlist-report.md`
7. Run `python -m src.cli apply`
8. If the preview looks right, run `python -m src.cli auth --write WRITE`
9. Run `python -m src.cli apply --confirm APPLY`

## License

MIT. See [LICENSE](LICENSE).
