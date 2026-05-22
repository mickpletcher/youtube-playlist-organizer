from __future__ import annotations

from typing import Any


CATEGORY_RULES = [
    {
        "source_playlists": ["AI", "Tech"],
        "target_playlist": "GitHub",
        "keyword_sets": [
            ["github"],
            ["copilot"],
            ["spec-driven"],
            ["spec driven"],
            ["/spec"],
            ["claude code"],
        ],
        "reason": "GitHub and coding workflow content should live in GitHub.",
    },
    {
        "source_playlists": ["AI", "Tech"],
        "target_playlist": "ChatGPT",
        "keyword_sets": [
            ["chatgpt"],
            ["openai"],
            ["custom gpt"],
            ["gpt"],
        ],
        "reason": "ChatGPT and OpenAI content should live in ChatGPT.",
    },
    {
        "source_playlists": ["AI", "Tech"],
        "target_playlist": "Prompt Engineering",
        "keyword_sets": [
            ["prompt"],
            ["prompts"],
        ],
        "reason": "Prompt specific content should live in Prompt Engineering.",
    },
    {
        "source_playlists": ["DIY"],
        "target_playlist": "Solar",
        "keyword_sets": [
            ["solar"],
            ["battery"],
            ["inverter"],
            ["off-grid"],
        ],
        "reason": "Solar system content should live in Solar.",
    },
    {
        "source_playlists": ["DIY"],
        "target_playlist": "Metal Fabrication",
        "keyword_sets": [
            ["weld"],
            ["welding"],
            ["fabrication"],
            ["metal"],
        ],
        "reason": "Metalwork content should live in Metal Fabrication.",
    },
    {
        "source_playlists": ["DIY"],
        "target_playlist": "Woodworking",
        "keyword_sets": [
            ["woodworking"],
            ["wood"],
            ["cabinet"],
        ],
        "reason": "Woodworking content should live in Woodworking.",
    },
    {
        "source_playlists": ["DIY"],
        "target_playlist": "DIY Closet",
        "keyword_sets": [
            ["closet"],
        ],
        "reason": "Closet build content should live in DIY Closet.",
    },
]


def matches_category_rule(title: str, rule: dict[str, Any]) -> bool:
    lowered = title.lower()
    keyword_sets = rule.get("keyword_sets", [])
    return any(all(keyword in lowered for keyword in keyword_set) for keyword_set in keyword_sets)


def build_lookup(playlists_data: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {playlist["title"]: playlist for playlist in playlists_data}


def build_target_video_ids(target: dict[str, Any] | None) -> set[str]:
    if not target:
        return set()

    return {
        item["video_id"]
        for item in target.get("items", [])
        if item.get("video_id")
    }


def find_category_moves(playlists_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    playlist_lookup = build_lookup(playlists_data)
    moves = []

    for rule in CATEGORY_RULES:
        source_playlists = rule.get("source_playlists", [])
        target = playlist_lookup.get(rule["target_playlist"])
        target_video_ids = build_target_video_ids(target)

        for source_title in source_playlists:
            source = playlist_lookup.get(source_title)
            if not source:
                continue

            for item in source.get("items", []):
                if not matches_category_rule(item.get("title", ""), rule):
                    continue
                if item["video_id"] in target_video_ids:
                    continue

                moves.append(
                    {
                        "action": "move_to_playlist",
                        "video_id": item["video_id"],
                        "title": item["title"],
                        "from_playlist": {
                            "playlist_id": source["id"],
                            "playlist_title": source["title"],
                            "playlist_privacy": source.get("privacy", ""),
                            "playlist_item_id": item["id"],
                            "position": item.get("position", 0),
                        },
                        "to_playlist": {
                            "playlist_id": (target or {}).get("id"),
                            "playlist_title": rule["target_playlist"],
                            "playlist_privacy": (target or {}).get("privacy", source.get("privacy", "private")),
                        },
                        "rule": rule["reason"],
                    }
                )

    moves.sort(
        key=lambda move: (
            move["from_playlist"]["playlist_title"].lower(),
            move["to_playlist"]["playlist_title"].lower(),
            move["title"].lower(),
            move["video_id"],
        )
    )
    return moves


def normalize_playlist_title(title: str) -> str:
    return " ".join(title.lower().split())


def find_same_title_playlist_merges(playlists_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for playlist in playlists_data:
        grouped.setdefault(normalize_playlist_title(playlist["title"]), []).append(playlist)

    merges = []
    for group in grouped.values():
        if len(group) < 2:
            continue

        ordered = sorted(
            group,
            key=lambda playlist: (
                -len(playlist.get("items", [])),
                playlist.get("privacy", "") != "private",
                playlist["id"],
            ),
        )
        target = ordered[0]
        target_video_ids = {
            item["video_id"]
            for item in target.get("items", [])
            if item.get("video_id")
        }

        for source in ordered[1:]:
            move_items = []
            remove_items = []

            for item in source.get("items", []):
                payload = {
                    "playlist_item_id": item["id"],
                    "video_id": item["video_id"],
                    "title": item["title"],
                    "position": item.get("position", 0),
                }
                if item["video_id"] in target_video_ids:
                    remove_items.append(payload)
                    continue

                move_items.append(payload)
                target_video_ids.add(item["video_id"])

            merges.append(
                {
                    "action": "merge_playlist",
                    "reason": "Duplicate playlist title",
                    "source_playlist": {
                        "playlist_id": source["id"],
                        "playlist_title": source["title"],
                        "playlist_privacy": source.get("privacy", ""),
                        "item_count": len(source.get("items", [])),
                    },
                    "target_playlist": {
                        "playlist_id": target["id"],
                        "playlist_title": target["title"],
                        "playlist_privacy": target.get("privacy", ""),
                        "item_count": len(target.get("items", [])),
                    },
                    "move_items": move_items,
                    "remove_items": remove_items,
                }
            )

    merges.sort(
        key=lambda merge: (
            merge["source_playlist"]["playlist_title"].lower(),
            merge["source_playlist"]["playlist_id"],
        )
    )
    return merges


def build_overlap_review(playlists_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    reviews = []
    for index, left in enumerate(playlists_data):
        left_videos = {
            item["video_id"]
            for item in left.get("items", [])
            if item.get("video_id")
        }
        if not left_videos:
            continue

        for right in playlists_data[index + 1:]:
            right_videos = {
                item["video_id"]
                for item in right.get("items", [])
                if item.get("video_id")
            }
            if not right_videos:
                continue

            shared = len(left_videos & right_videos)
            if shared == 0:
                continue

            union = len(left_videos | right_videos)
            jaccard = shared / union
            containment = max(shared / len(left_videos), shared / len(right_videos))
            if shared < 3 and jaccard < 0.10 and containment < 0.35:
                continue

            reviews.append(
                {
                    "left_playlist": left["title"],
                    "right_playlist": right["title"],
                    "shared_videos": shared,
                    "left_count": len(left_videos),
                    "right_count": len(right_videos),
                    "jaccard": round(jaccard, 3),
                    "containment": round(containment, 3),
                }
            )

    reviews.sort(
        key=lambda review: (
            -review["shared_videos"],
            -review["jaccard"],
            review["left_playlist"].lower(),
            review["right_playlist"].lower(),
        )
    )
    return reviews
