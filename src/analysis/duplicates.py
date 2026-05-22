import json
from pathlib import Path
from typing import Any


def load_export(path: str = "data/playlists.json") -> list[dict[str, Any]]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def find_duplicates(playlists_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    video_map: dict[str, dict[str, Any]] = {}

    for playlist in playlists_data:
        playlist_id = playlist["id"]
        playlist_title = playlist["title"]
        playlist_privacy = playlist.get("privacy", "")
        for item in playlist.get("items", []):
            video_id = item.get("video_id")
            if not video_id:
                continue

            entry = video_map.setdefault(
                video_id,
                {
                    "video_id": video_id,
                    "title": item.get("title", ""),
                    "occurrences": [],
                },
            )

            if not entry["title"] and item.get("title"):
                entry["title"] = item["title"]

            entry["occurrences"].append(
                {
                    "playlist_id": playlist_id,
                    "playlist_title": playlist_title,
                    "playlist_privacy": playlist_privacy,
                    "playlist_item_id": item["id"],
                    "position": item.get("position", 0),
                }
            )

    duplicates = []
    for entry in video_map.values():
        if len(entry["occurrences"]) < 2:
            continue

        sorted_occurrences = sorted(
            entry["occurrences"],
            key=lambda occurrence: (
                occurrence["playlist_title"].lower(),
                occurrence["position"],
                occurrence["playlist_id"],
            ),
        )
        duplicates.append(
            {
                "video_id": entry["video_id"],
                "title": entry["title"],
                "playlist_count": len(sorted_occurrences),
                "playlists": [occurrence["playlist_title"] for occurrence in sorted_occurrences],
                "occurrences": sorted_occurrences,
            }
        )

    duplicates.sort(
        key=lambda duplicate: (
            -duplicate["playlist_count"],
            duplicate["title"].lower(),
            duplicate["video_id"],
        )
    )
    return duplicates
