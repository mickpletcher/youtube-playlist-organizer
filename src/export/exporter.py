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
    Path(output_path).write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


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
