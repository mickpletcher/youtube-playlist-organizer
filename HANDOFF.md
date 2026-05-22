# Project Handoff: YouTube Playlist Organizer

This document captures the full state of the project as of session end on 2026-05-04. Use it to continue development in a new session with GitHub Copilot or any other AI assistant.

---

## What This Project Does

A Python CLI tool that connects to the YouTube Data API v3 via OAuth2 and lets the user list, export, analyze, and reorganize their YouTube playlists. Designed safety-first: all write operations default to dry-run and require explicit confirmation.

---

## Current Status

### Completed and working

| Command | Status | Notes |
|---|---|---|
| `python -m src.cli auth` | Working | OAuth2 flow, saves token.json |
| `python -m src.cli list` | Working | Lists all 73 playlists with video counts |
| `python -m src.cli export` | Built, not yet tested | Exports JSON + 2 CSVs to data/ |

### Not yet built

| Command | What it needs |
|---|---|
| `python -m src.cli analyze` | `src/analysis/duplicates.py` — scan items_by_playlist for duplicate video_ids across playlists |
| `python -m src.cli plan` | `src/analysis/planner.py` — generate `data/playlist-plan.json` AND `data/playlist-report.md` |
| `python -m src.cli apply` | Apply plan to YouTube API with `--confirm` flag required for real writes |

---

## Project Structure

```
youtube-playlist-organizer/
├── src/
│   ├── __init__.py
│   ├── cli.py                    # Typer CLI — all commands live here
│   ├── auth/
│   │   ├── __init__.py
│   │   └── oauth.py              # get_credentials(), get_youtube_client()
│   ├── api/
│   │   ├── __init__.py
│   │   └── youtube.py            # get_playlists(), get_playlist_items()
│   ├── models/
│   │   ├── __init__.py
│   │   └── playlist.py           # Playlist, PlaylistItem (Pydantic models)
│   ├── export/
│   │   ├── __init__.py
│   │   └── exporter.py           # export_json(), export_csv()
│   └── analysis/                 # NOT YET CREATED
│       ├── duplicates.py
│       └── planner.py
├── data/                         # Runtime output, gitignored except .gitkeep
│   ├── .gitkeep
│   ├── playlists.json            # Created by export command
│   ├── playlists.csv             # Created by export command
│   ├── playlist_items.csv        # Created by export command
│   ├── playlist-plan.json        # Created by plan command (machine-readable)
│   └── playlist-report.md        # Created by plan command (human-readable review)
├── .env.example
├── requirements.txt
├── README.md
└── HANDOFF.md                    # This file
```

Files that must NOT be committed (already in .gitignore):
- `client_secret.json` — Google OAuth credentials
- `token.json` — stored OAuth token
- `data/playlists.json`
- `data/playlists.csv`
- `data/playlist_items.csv`

---

## All Current Source Files

### `requirements.txt`

```
google-api-python-client==2.118.0
google-auth-oauthlib==1.2.0
google-auth-httplib2==0.2.0
typer==0.12.3
rich==13.7.1
python-dotenv==1.0.1
pydantic==2.6.1
pandas==2.2.1
```

### `src/models/playlist.py`

```python
from pydantic import BaseModel


class Playlist(BaseModel):
    id: str
    title: str
    description: str
    item_count: int
    privacy: str


class PlaylistItem(BaseModel):
    id: str
    video_id: str
    title: str
    position: int
    playlist_id: str
```

### `src/auth/oauth.py`

```python
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES_READONLY = ["https://www.googleapis.com/auth/youtube.readonly"]
SCOPES_WRITE = ["https://www.googleapis.com/auth/youtube"]


def get_credentials(
    client_secret_file: str = "client_secret.json",
    token_file: str = "token.json",
    readonly: bool = True,
) -> Credentials:
    scopes = SCOPES_READONLY if readonly else SCOPES_WRITE
    token_path = Path(token_file)
    creds = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(token_file, scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, scopes)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json())

    return creds


def get_youtube_client(
    client_secret_file: str = "client_secret.json",
    token_file: str = "token.json",
    readonly: bool = True,
):
    creds = get_credentials(client_secret_file, token_file, readonly)
    return build("youtube", "v3", credentials=creds)
```

### `src/api/youtube.py`

```python
from src.models.playlist import Playlist, PlaylistItem


def get_playlists(client) -> list[Playlist]:
    playlists = []
    request = client.playlists().list(
        part="snippet,contentDetails,status",
        mine=True,
        maxResults=50,
    )
    while request:
        response = request.execute()
        for item in response.get("items", []):
            playlists.append(Playlist(
                id=item["id"],
                title=item["snippet"]["title"],
                description=item["snippet"].get("description", ""),
                item_count=item["contentDetails"]["itemCount"],
                privacy=item["status"]["privacyStatus"],
            ))
        request = client.playlists().list_next(request, response)
    return playlists


def get_playlist_items(client, playlist_id: str) -> list[PlaylistItem]:
    items = []
    request = client.playlistItems().list(
        part="snippet",
        playlistId=playlist_id,
        maxResults=50,
    )
    while request:
        response = request.execute()
        for item in response.get("items", []):
            snippet = item["snippet"]
            items.append(PlaylistItem(
                id=item["id"],
                video_id=snippet["resourceId"]["videoId"],
                title=snippet["title"],
                position=snippet["position"],
                playlist_id=playlist_id,
            ))
        request = client.playlistItems().list_next(request, response)
    return items
```

### `src/export/exporter.py`

```python
import csv
import json
from pathlib import Path

from src.models.playlist import Playlist, PlaylistItem


def export_json(
    playlists: list[Playlist],
    items_by_playlist: dict[str, list[PlaylistItem]],
    output_path: str = "data/playlists.json",
) -> None:
    data = []
    for pl in playlists:
        items = items_by_playlist.get(pl.id, [])
        data.append({
            "id": pl.id,
            "title": pl.title,
            "description": pl.description,
            "privacy": pl.privacy,
            "item_count": pl.item_count,
            "items": [
                {
                    "id": item.id,
                    "video_id": item.video_id,
                    "title": item.title,
                    "position": item.position,
                }
                for item in items
            ],
        })
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(data, indent=2, ensure_ascii=False))


def export_csv(
    playlists: list[Playlist],
    items_by_playlist: dict[str, list[PlaylistItem]],
    playlists_path: str = "data/playlists.csv",
    items_path: str = "data/playlist_items.csv",
) -> None:
    Path(playlists_path).parent.mkdir(parents=True, exist_ok=True)

    with open(playlists_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "title", "description", "privacy", "item_count"])
        writer.writeheader()
        for pl in playlists:
            writer.writerow({
                "id": pl.id,
                "title": pl.title,
                "description": pl.description,
                "privacy": pl.privacy,
                "item_count": pl.item_count,
            })

    with open(items_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["playlist_id", "playlist_title", "position", "video_id", "title"])
        writer.writeheader()
        for pl in playlists:
            for item in items_by_playlist.get(pl.id, []):
                writer.writerow({
                    "playlist_id": pl.id,
                    "playlist_title": pl.title,
                    "position": item.position,
                    "video_id": item.video_id,
                    "title": item.title,
                })
```

### `src/cli.py`

```python
import typer
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def auth(
    client_secret: str = typer.Option(
        "client_secret.json", envvar="CLIENT_SECRET_FILE", help="Path to client_secret.json"
    ),
    token_file: str = typer.Option(
        "token.json", envvar="TOKEN_FILE", help="Path to store token.json"
    ),
    write: bool = typer.Option(False, "--write", is_flag=True, help="Request write scope"),
):
    """Authenticate with YouTube via OAuth2."""
    from src.auth.oauth import get_credentials

    readonly = not write
    try:
        get_credentials(client_secret, token_file, readonly)
        scope_label = "read-only" if readonly else "read-write"
        console.print(f"[green]Authenticated ({scope_label})[/green]")
        console.print(f"Token saved to [bold]{token_file}[/bold]")
    except FileNotFoundError:
        console.print(f"[red]Not found: {client_secret}[/red]")
        console.print(
            "Download OAuth credentials from Google Cloud Console and save as client_secret.json"
        )
        raise typer.Exit(1)


@app.command()
def list(
    client_secret: str = typer.Option(
        "client_secret.json", envvar="CLIENT_SECRET_FILE", help="Path to client_secret.json"
    ),
    token_file: str = typer.Option(
        "token.json", envvar="TOKEN_FILE", help="Path to token.json"
    ),
):
    """List all your YouTube playlists."""
    from src.auth.oauth import get_youtube_client
    from src.api.youtube import get_playlists

    client = get_youtube_client(client_secret, token_file, readonly=True)
    playlists = get_playlists(client)

    if not playlists:
        console.print("[yellow]No playlists found.[/yellow]")
        return

    console.print(f"\n[bold]Found {len(playlists)} playlist(s):[/bold]\n")
    for pl in playlists:
        console.print(f"  [cyan]{pl.title}[/cyan]  ({pl.item_count} videos)  [dim]{pl.privacy}[/dim]")
        if pl.description:
            console.print(f"    {pl.description[:80]}")
    console.print()


@app.command()
def export(
    client_secret: str = typer.Option(
        "client_secret.json", envvar="CLIENT_SECRET_FILE", help="Path to client_secret.json"
    ),
    token_file: str = typer.Option(
        "token.json", envvar="TOKEN_FILE", help="Path to token.json"
    ),
    output_dir: str = typer.Option("data", help="Directory to write output files"),
):
    """Export all playlists and their videos to JSON and CSV."""
    from src.auth.oauth import get_youtube_client
    from src.api.youtube import get_playlists, get_playlist_items
    from src.export.exporter import export_json, export_csv

    client = get_youtube_client(client_secret, token_file, readonly=True)

    console.print("\n[bold]Fetching playlists...[/bold]")
    playlists = get_playlists(client)
    console.print(f"Found {len(playlists)} playlist(s). Fetching videos...")

    items_by_playlist: dict = {}
    for i, pl in enumerate(playlists, 1):
        console.print(f"  [{i}/{len(playlists)}] {pl.title}", end="\r")
        items_by_playlist[pl.id] = get_playlist_items(client, pl.id)

    json_path = f"{output_dir}/playlists.json"
    playlists_csv = f"{output_dir}/playlists.csv"
    items_csv = f"{output_dir}/playlist_items.csv"

    export_json(playlists, items_by_playlist, json_path)
    export_csv(playlists, items_by_playlist, playlists_csv, items_csv)

    total_videos = sum(len(v) for v in items_by_playlist.values())
    console.print(f"\n[green]Exported {len(playlists)} playlists, {total_videos} videos[/green]")
    console.print(f"  {json_path}")
    console.print(f"  {playlists_csv}")
    console.print(f"  {items_csv}\n")


if __name__ == "__main__":
    app()
```

---

## Known Issues and Quirks

**Typer boolean flag bug (typer 0.12.3)**
The standard `bool = typer.Option(True, "--flag/--no-flag")` pattern throws `TypeError: Secondary flag is not valid for non-boolean flag` at startup. Workaround: use `is_flag=True` with a positive-only flag (`--write`) and derive the inverse in the function body.

**Single-command Typer behavior**
When only one `@app.command()` is registered, Typer promotes it to the default command and ignores subcommand names. Once two or more commands exist, `python -m src.cli auth` works correctly. With only one command, run `python -m src.cli` without a subcommand.

**Rich bracket stripping**
Passing `[public]` or `[private]` directly into a `console.print()` f-string causes Rich to interpret them as markup tags and strip them. Wrap privacy values in a valid Rich tag like `[dim]{pl.privacy}[/dim]` instead.

**Google Cloud JSON download broken**
As of May 2026, the "Download JSON" button in the OAuth client creation dialog does not work reliably. The workaround is to manually build `client_secret.json` from the Client ID and a newly generated Client Secret. See README Step 6 for the exact PowerShell command.

**token.json uses write scope**
The existing `token.json` was created with the full `youtube` write scope even though read-only was intended. This is because `is_flag=True` on the `--write` flag in typer 0.12.3 defaults to `True` instead of `False` in some execution paths. The token still works for all read operations. To get a clean read-only token, delete `token.json` and re-run auth without `--write`.

---

## Next Steps (in order)

### 1. Verify export works

Run and confirm three files are created in `data/`:

```powershell
python -m src.cli export
```

Expected output:
```
Fetching playlists...
Found 73 playlist(s). Fetching videos...
Exported 73 playlists, XXXX videos
  data/playlists.json
  data/playlists.csv
  data/playlist_items.csv
```

### 2. Build `src/analysis/duplicates.py`

Load `data/playlists.json` (or accept the in-memory `items_by_playlist` dict) and find videos that appear in more than one playlist. A duplicate is defined as the same `video_id` appearing in two or more playlists.

Return a list of dicts like:
```python
[
    {
        "video_id": "dQw4w9WgXcQ",
        "title": "Some Video",
        "playlists": ["Trading", "Favorites"]
    },
    ...
]
```

### 3. Build `src/analysis/planner.py`

Takes the duplicate list and produces two output files:

**`data/playlist-plan.json`** — machine-readable, used by the `apply` command:
```json
{
  "generated_at": "2026-05-04T12:00:00Z",
  "actions": [
    {
      "action": "remove_duplicate",
      "video_id": "dQw4w9WgXcQ",
      "title": "Some Video",
      "keep_in": "Favorites",
      "remove_from": ["Trading"]
    }
  ]
}
```

**`data/playlist-report.md`** — human-readable markdown, intended to be read before running `apply`. The user reviews this file to understand exactly what will change before committing.

The report must be clean, readable, and scannable. Use this exact structure:

```markdown
# YouTube Playlist Reorganization Report
Generated: 2026-05-04 12:00:00

## Summary
- Total playlists: 73
- Total videos: 1842
- Duplicate videos found: 14
- Actions planned: 14

---

## Duplicate Videos

These videos appear in more than one playlist. The plan will remove them from all but the first listed playlist.

| Video Title | Keep In | Remove From |
|---|---|---|
| Some Video Title | Favorites | Trading |
| Another Video | AI | ChatGPT, Tech |

---

## Actions Planned

### Remove Duplicates (14)

1. **Some Video Title** (`dQw4w9WgXcQ`)
   - Keep in: Favorites
   - Remove from: Trading

2. **Another Video** (`abc123`)
   - Keep in: AI
   - Remove from: ChatGPT, Tech

---

## Before You Apply

- Review each action above carefully.
- To apply these changes, run: `python -m src.cli apply --confirm`
- There is no undo. The YouTube API does not support rollbacks.
- Each removal costs 50 API quota units. Total estimated cost: 700 units.
```

Key rules for the report generator:
- "Keep in" should be the playlist where the video has the lowest position number (i.e. it was added earliest).
- If position is equal, keep the one in the playlist with more videos (the more curated list).
- Always show the estimated API quota cost at the bottom so the user knows what `apply` will consume.
- Write the file as UTF-8.

### 4. Add `analyze` command to `src/cli.py`

```python
@app.command()
def analyze(...):
    """Scan playlists for duplicates and issues."""
    # Load data/playlists.json
    # Run duplicates.find_duplicates()
    # Print summary table using rich
    # Write data/playlist-plan.json via planner.generate_plan()
```

### 5. Add `apply` command to `src/cli.py`

```python
@app.command()
def apply(
    confirm: bool = typer.Option(False, "--confirm", is_flag=True),
    ...
):
    """Apply the plan in data/playlist-plan.json to YouTube."""
    # Load data/playlist-plan.json
    # Print every action (always)
    # If not confirm: print "Run with --confirm to apply" and exit
    # If confirm: execute each action via YouTube API
```

Write operations use `playlistItems.delete` (50 units each). Warn the user about quota cost before executing.

---

## Environment

- Python 3.11 (installed via Microsoft Store)
- Windows 11
- Shell: PowerShell (not bash — heredoc syntax differs)
- Project root: `C:\Users\mick0\OneDrive\Documents\Code & Dev\GitHub\youtube-playlist-organizer`
- Google Cloud project: `coastal-well-495305-s8`
- YouTube account has 73 playlists

---

## Running the Project

All commands run from the project root in PowerShell:

```powershell
cd "C:\Users\mick0\OneDrive\Documents\Code & Dev\GitHub\youtube-playlist-organizer"

# First time setup
pip install -r requirements.txt

# Authenticate (opens browser)
python -m src.cli auth

# List playlists
python -m src.cli list

# Export all data to data/
python -m src.cli export

# (Not yet built)
python -m src.cli analyze
python -m src.cli plan
python -m src.cli apply --confirm
```