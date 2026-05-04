# YouTubePlaylistOrganizer

An API-driven CLI tool for analyzing, cleaning, and reorganizing YouTube playlists using the YouTube Data API v3 and Google OAuth2. Designed for safety: all operations default to dry-run mode and require explicit confirmation before any changes are applied.

---

## Features

- Authenticate with a Google account via OAuth2
- Retrieve all playlists and their items from the authenticated user's account
- Export playlist data to JSON and CSV for offline analysis
- Detect duplicate videos across playlists
- Identify inefficiencies such as oversized or redundant playlists
- Perform AI-assisted categorization of videos by topic or theme
- Generate a human-readable reorganization plan before touching any data
- Apply changes only after explicit user confirmation
- Dry-run mode enabled by default on all mutating commands

---

## How It Works

1. **Authenticate** - The tool opens a browser-based OAuth2 consent flow and stores a token locally for subsequent runs.
2. **Fetch** - All playlists and their items are retrieved from the YouTube Data API v3 and cached locally.
3. **Export** - Raw data is written to JSON and CSV files for inspection or backup.
4. **Analyze** - The tool scans for duplicates, overlapping content, and grouping opportunities. AI-assisted categorization assigns topics to videos based on metadata.
5. **Plan** - A reorganization plan is generated and written to `playlist-plan.json`. No changes are made at this stage.
6. **Review** - The user inspects the plan. The CLI displays a summary in the terminal.
7. **Apply** - The user explicitly confirms execution. The tool applies changes to YouTube via API calls.

---

## Project Structure

```text
youtube-playlist-organizer/
├── src/
│   ├── auth/
│   │   └── oauth.py            # OAuth2 flow and token management
│   ├── api/
│   │   └── youtube.py          # YouTube Data API v3 client wrapper
│   ├── models/
│   │   └── playlist.py         # Pydantic data models
│   ├── analysis/
│   │   ├── duplicates.py       # Duplicate detection logic
│   │   ├── categorizer.py      # AI-assisted video categorization
│   │   └── planner.py          # Reorganization plan generation
│   ├── export/
│   │   └── exporter.py         # JSON and CSV export handlers
│   └── cli.py                  # Typer CLI entry point
├── data/
│   ├── playlists.json          # Cached raw playlist data
│   ├── playlists.csv           # CSV export
│   └── playlist-plan.json      # Generated reorganization plan
├── tests/
│   └── ...
├── .env.example
├── client_secret.json          # Google OAuth credentials (not committed)
├── token.json                  # Stored OAuth token (not committed)
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Create a Google Cloud Project

1. Go to [https://console.cloud.google.com](https://console.cloud.google.com).
2. Create a new project or select an existing one.
3. Navigate to **APIs & Services > Library**.

### 2. Enable the YouTube Data API v3

1. Search for **YouTube Data API v3** in the API Library.
2. Click **Enable**.

### 3. Create OAuth 2.0 Credentials

1. Go to **APIs & Services > Credentials**.
2. Click **Create Credentials > OAuth client ID**.
3. Set application type to **Desktop app**.
4. Download the JSON file and rename it to `client_secret.json`.
5. Place `client_secret.json` in the project root. Do not commit this file.

### 4. Install Dependencies

Requires Python 3.12.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Copy the example file and fill in values:

```bash
cp .env.example .env
```

`.env.example`:

```env
GOOGLE_CLIENT_SECRET_FILE=client_secret.json
TOKEN_FILE=token.json
DATA_DIR=data/
LOG_LEVEL=INFO
```

---

## Required OAuth Scopes

The following scopes must be authorized during the OAuth consent flow:

| Scope | Purpose |
| --- | --- |
| `https://www.googleapis.com/auth/youtube.readonly` | Read playlists and playlist items |
| `https://www.googleapis.com/auth/youtube` | Create, update, and delete playlists and items |

The readonly scope is sufficient for export and analysis. The full `youtube` scope is required for any write operations.

---

## Usage

### Authenticate

Initiates the OAuth2 browser flow and stores a token locally.

```bash
python -m src.cli auth
```

The token is saved to `token.json`. Subsequent commands use this token automatically until it expires or is revoked.

### List Playlists

```bash
python -m src.cli list
```

Sample output:

```text
ID                    Title                    Videos
PLxxxxxxxxxxxxxx      Road Cycling             47
PLyyyyyyyyyyyyyy      Tech Talks 2024          13
PLzzzzzzzzzzzzzz      Untitled Playlist         2
```

### Export Playlist Data

Export all playlist data to JSON and CSV:

```bash
python -m src.cli export
```

Output files:

```text
data/playlists.json
data/playlists.csv
```

Export a single playlist by ID:

```bash
python -m src.cli export --playlist-id PLxxxxxxxxxxxxxx
```

### Analyze Playlists

Scan for duplicates, overlapping videos, and categorization opportunities:

```bash
python -m src.cli analyze
```

Output includes:

- Duplicate video entries across playlists
- Playlists with more than 200 items (YouTube reorder quota risk)
- Suggested category groupings based on video metadata

### Generate a Reorganization Plan

Produces a `playlist-plan.json` file describing all proposed changes. No writes occur at this step.

```bash
python -m src.cli plan
```

Sample `playlist-plan.json` structure:

```json
{
  "generated_at": "2026-05-03T09:15:00Z",
  "actions": [
    {
      "action": "move",
      "video_id": "dQw4w9WgXcQ",
      "from_playlist": "PLxxxxxxxxxxxxxx",
      "to_playlist": "PLnew_cycling"
    },
    {
      "action": "delete_duplicate",
      "video_id": "abc123",
      "playlist": "PLyyyyyyyyyyyyyy"
    },
    {
      "action": "create_playlist",
      "title": "AI & Machine Learning",
      "description": "Auto-generated from categorization"
    }
  ]
}
```

### Apply Changes

Applies the plan in `playlist-plan.json` to the YouTube account. Dry-run mode is active by default.

Preview what will happen without making changes:

```bash
python -m src.cli apply
```

Execute for real:

```bash
python -m src.cli apply --confirm
```

---

## Safety Model

All mutating commands (`apply`) default to `--dry-run` mode. Without the `--confirm` flag, the tool will print every action it would take but make no API calls that modify data.

There is no undo. The YouTube Data API does not support batch rollbacks. Before running `apply --confirm`, review `playlist-plan.json` and verify the export in `data/playlists.json` represents your current state.

Recommended workflow:

1. Run `export` to create a backup snapshot.
2. Run `analyze` to identify issues.
3. Run `plan` to generate the change set.
4. Review `playlist-plan.json` manually.
5. Run `apply --confirm` only when satisfied with the plan.

---

## API Quota Considerations

The YouTube Data API v3 allocates 10,000 units per day by default.

| Operation | Cost per call |
| --- | --- |
| `playlists.list` | 1 unit |
| `playlistItems.list` | 1 unit |
| `playlistItems.insert` | 50 units |
| `playlistItems.delete` | 50 units |
| `playlists.insert` | 50 units |
| `playlists.delete` | 50 units |

**Reorder operations are expensive.** The YouTube API has no native reorder endpoint. Moving a video requires deleting the item and reinserting it at the target position, costing 100 units per move. A plan that moves 100 videos will consume the entire daily quota.

To request a quota increase, visit **APIs & Services > Quotas** in the Google Cloud Console and submit an increase request with a justification.

---

## Tech Stack

| Component | Library |
| --- | --- |
| Language | Python 3.12 |
| YouTube API | google-api-python-client |
| Authentication | google-auth-oauthlib |
| CLI interface | typer |
| Data processing | pandas |
| Data models | pydantic |
| Terminal output | rich |
| Environment config | python-dotenv |

---

## Roadmap

- [ ] Interactive TUI for reviewing and editing the plan before applying
- [ ] Incremental sync to avoid re-fetching unchanged playlists
- [ ] Webhook or scheduled mode for automated weekly cleanup
- [ ] Support for playlist privacy settings (public, unlisted, private)
- [ ] Multi-account support via named profiles
- [ ] Optional integration with a local LLM for offline categorization
- [ ] HTML report export of analysis results

---

## Use Cases

**Cleaning up a backlog of unsorted videos**
You have 500+ saved videos spread across a handful of catch-all playlists. Run `analyze` to detect logical groupings, generate a plan, and let the tool split them into organized playlists.

**Removing duplicates before sharing a playlist**
Before sharing a playlist publicly, run `analyze` to identify any duplicate entries added over time, review the plan, and apply the cleanup.

**Auditing a large channel's content library**
Export all playlist data to CSV and import into a spreadsheet for manual review alongside the tool's analysis output.

**Scheduled playlist hygiene**
Run `analyze` and `export` on a schedule to monitor playlist growth and flag playlists that are approaching the quota-risk threshold.

---

## Contributing

1. Fork the repository and create a feature branch from `main`.
2. Follow existing code structure. New capabilities belong in the appropriate `src/` subdirectory.
3. Add tests for any new logic under `tests/`.
4. Run the test suite before submitting a pull request.

   ```bash
   pytest tests/
   ```

5. Open a pull request with a clear description of what changed and why. Reference any related issues.

Bug reports and feature requests are welcome via GitHub Issues.

---

## License

MIT License. See [LICENSE](LICENSE) for full text.
