from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.analysis.rules import (
    build_overlap_review,
    find_category_moves,
    find_same_title_playlist_merges,
)


STOP_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "your",
    "you",
    "are",
    "how",
    "what",
    "why",
    "when",
    "into",
    "than",
    "over",
    "best",
    "worst",
    "full",
    "guide",
    "video",
    "videos",
    "using",
    "use",
    "new",
    "get",
    "make",
    "made",
    "just",
    "more",
    "less",
    "most",
    "its",
    "it's",
    "it",
    "my",
    "our",
    "their",
    "his",
    "her",
    "about",
    "after",
    "before",
    "does",
    "will",
    "they",
    "them",
    "these",
    "those",
    "all",
    "top",
    "real",
    "part",
    "vs",
    "out",
    "off",
    "too",
    "not",
    "can",
    "has",
    "had",
    "have",
    "was",
    "were",
    "who",
    "where",
    "which",
    "but",
    "only",
    "need",
    "know",
    "tips",
    "easy",
    "ultimate",
    "beginner",
    "beginners",
    "step",
    "steps",
    "minutes",
    "minute",
    "here",
    "here's",
    "there",
    "a",
    "an",
    "at",
    "by",
    "is",
    "as",
    "be",
    "if",
    "to",
    "of",
    "on",
    "in",
}

GENERIC_PLAYLISTS = {
    "favorites",
    "goals",
    "training",
    "workout",
    "health",
    "tech",
    "automation",
    "ai",
    "diy",
}


def tokenize(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[A-Za-z0-9']+", text.lower())
        if len(token) > 2 and token not in STOP_WORDS
    ]


def build_playlist_profiles(playlists_data: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    profiles = {}

    for playlist in playlists_data:
        token_counter = Counter()
        for item in playlist.get("items", []):
            token_counter.update(tokenize(item.get("title", "")))

        profiles[playlist["id"]] = {
            "title": playlist["title"],
            "privacy": playlist.get("privacy", ""),
            "title_tokens": set(tokenize(playlist["title"])),
            "profile_tokens": {token for token, _ in token_counter.most_common(30)},
            "item_count": len(playlist.get("items", [])),
        }

    return profiles


def score_occurrence(
    occurrence: dict[str, Any],
    video_title: str,
    profiles: dict[str, dict[str, Any]],
) -> tuple[float, str]:
    profile = profiles[occurrence["playlist_id"]]
    video_tokens = set(tokenize(video_title))
    title_overlap = len(video_tokens & profile["title_tokens"])
    profile_overlap = len(video_tokens & profile["profile_tokens"])
    generic_penalty = 1 if profile["title"].strip().lower() in GENERIC_PLAYLISTS else 0

    score = (
        title_overlap * 10
        + profile_overlap * 2
        - generic_penalty * 3
        - (profile["item_count"] / 1000.0)
    )
    reason = (
        f"title_overlap={title_overlap}, "
        f"profile_overlap={profile_overlap}, "
        f"generic_penalty={generic_penalty}, "
        f"item_count={profile['item_count']}"
    )
    return score, reason


def choose_keep_occurrence(
    duplicate: dict[str, Any],
    profiles: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    occurrences = duplicate["occurrences"]
    favorites = [
        occurrence
        for occurrence in occurrences
        if occurrence["playlist_title"].strip().lower() == "favorites"
    ]
    if favorites:
        return favorites[0]

    private_occurrences = [
        occurrence
        for occurrence in occurrences
        if occurrence.get("playlist_privacy", "").strip().lower() == "private"
    ]
    if private_occurrences:
        occurrences = private_occurrences

    scored_occurrences = []
    for occurrence in occurrences:
        score, reason = score_occurrence(occurrence, duplicate["title"], profiles)
        scored_occurrences.append((score, reason, occurrence))

    scored_occurrences.sort(
        key=lambda entry: (
            -entry[0],
            entry[2]["playlist_title"].lower(),
            entry[2]["position"],
            entry[2]["playlist_id"],
        )
    )
    keep_in = dict(scored_occurrences[0][2])
    keep_in["match_reason"] = scored_occurrences[0][1]
    keep_in["match_score"] = scored_occurrences[0][0]
    return keep_in


def find_deleted_video_items(playlists_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions = []

    for playlist in playlists_data:
        for item in playlist.get("items", []):
            if item.get("title", "").strip() != "Deleted video":
                continue

            actions.append(
                {
                    "action": "remove_deleted",
                    "video_id": item.get("video_id", ""),
                    "title": item.get("title", ""),
                    "from_playlist": {
                        "playlist_id": playlist["id"],
                        "playlist_title": playlist["title"],
                        "playlist_privacy": playlist.get("privacy", ""),
                        "playlist_item_id": item["id"],
                        "position": item.get("position", 0),
                    },
                }
            )

    actions.sort(
        key=lambda action: (
            action["from_playlist"]["playlist_title"].lower(),
            action["from_playlist"]["position"],
            action["video_id"],
            action["from_playlist"]["playlist_item_id"],
        )
    )
    return actions


def should_skip_move_due_to_duplicate(
    move: dict[str, Any],
    duplicate_lookup: dict[tuple[str, str], dict[str, Any]],
) -> bool:
    key = (move["from_playlist"]["playlist_item_id"], move["video_id"])
    duplicate_action = duplicate_lookup.get(key)
    if not duplicate_action:
        return False

    keep_playlist_id = duplicate_action["keep_in"]["playlist_id"]
    return keep_playlist_id == move["to_playlist"].get("playlist_id")


def build_duplicate_lookup(actions: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    lookup = {}
    for action in actions:
        if action["action"] != "remove_duplicate":
            continue
        for item in action.get("remove_from", []):
            lookup[(item["playlist_item_id"], action["video_id"])] = action
    return lookup


def summarize_actions(actions: list[dict[str, Any]]) -> dict[str, int]:
    duplicate_actions = [action for action in actions if action["action"] == "remove_duplicate"]
    deleted_actions = [action for action in actions if action["action"] == "remove_deleted"]
    move_actions = [action for action in actions if action["action"] == "move_to_playlist"]
    merge_actions = [action for action in actions if action["action"] == "merge_playlist"]

    merge_move_items = sum(len(action.get("move_items", [])) for action in merge_actions)
    merge_remove_items = sum(len(action.get("remove_items", [])) for action in merge_actions)

    return {
        "actions": len(actions),
        "duplicate_videos": len(duplicate_actions),
        "deleted_videos": len(deleted_actions),
        "category_moves": len(move_actions),
        "playlist_merges": len(merge_actions),
        "playlist_creations": sum(1 for action in actions if action["action"] == "create_playlist"),
        "playlist_deletions": len(merge_actions),
        "playlist_item_moves": len(move_actions) + merge_move_items,
        "playlist_item_removals": (
            sum(len(action.get("remove_from", [])) for action in duplicate_actions)
            + len(deleted_actions)
            + merge_remove_items
        ),
    }


def generate_plan(
    duplicates: list[dict[str, Any]],
    playlists_data: list[dict[str, Any]],
    include_category_moves: bool = False,
) -> dict[str, Any]:
    profiles = build_playlist_profiles(playlists_data)
    actions = []
    seen_playlist_creations = set()

    for duplicate in duplicates:
        keep_in = choose_keep_occurrence(duplicate, profiles)
        remove_from = [
            occurrence
            for occurrence in duplicate["occurrences"]
            if occurrence["playlist_item_id"] != keep_in["playlist_item_id"]
        ]
        if not remove_from:
            continue

        actions.append(
            {
                "action": "remove_duplicate",
                "video_id": duplicate["video_id"],
                "title": duplicate["title"],
                "keep_in": keep_in,
                "remove_from": remove_from,
            }
        )

    actions.extend(find_deleted_video_items(playlists_data))

    duplicate_lookup = build_duplicate_lookup(actions)
    category_moves = find_category_moves(playlists_data)
    planned_category_moves = []
    for move in category_moves:
        if should_skip_move_due_to_duplicate(move, duplicate_lookup):
            continue

        planned_category_moves.append(move)
        if not include_category_moves:
            continue

        target_title = move["to_playlist"]["playlist_title"]
        if not move["to_playlist"].get("playlist_id") and target_title not in seen_playlist_creations:
            actions.append(
                {
                    "action": "create_playlist",
                    "title": target_title,
                    "privacy": move["to_playlist"]["playlist_privacy"],
                    "reason": "Category rule requires a dedicated playlist",
                }
            )
            seen_playlist_creations.add(target_title)

        actions.append(move)

    merge_actions = find_same_title_playlist_merges(playlists_data)
    actions.extend(merge_actions)

    summary = summarize_actions(actions)
    overlap_review = build_overlap_review(playlists_data)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "review": {
            "overlap_candidates": overlap_review,
            "category_move_candidates": planned_category_moves,
        },
        "actions": actions,
    }


def write_plan(plan: dict[str, Any], path: str = "data/playlist-plan.json") -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")


def write_report(
    plan: dict[str, Any],
    path: str = "data/playlist-report.md",
) -> None:
    summary = plan["summary"]
    overlap_candidates = plan.get("review", {}).get("overlap_candidates", [])
    category_move_candidates = plan.get("review", {}).get("category_move_candidates", [])
    actions = plan.get("actions", [])
    duplicate_actions = [action for action in actions if action["action"] == "remove_duplicate"]
    deleted_actions = [action for action in actions if action["action"] == "remove_deleted"]
    move_actions = [action for action in actions if action["action"] == "move_to_playlist"]
    merge_actions = [action for action in actions if action["action"] == "merge_playlist"]

    lines = [
        "# Playlist Analysis Report",
        "",
        f"Generated: `{plan['generated_at']}`",
        "",
        "## Snapshot",
        "",
        f"- Planned actions: {summary['actions']}",
        f"- Duplicate videos: {summary['duplicate_videos']}",
        f"- Deleted videos: {summary['deleted_videos']}",
        f"- Category moves: {summary['category_moves']}",
        f"- Playlist merges: {summary['playlist_merges']}",
        f"- Playlist item moves: {summary['playlist_item_moves']}",
        f"- Playlist item removals: {summary['playlist_item_removals']}",
        f"- Suggested category moves not yet queued: {len(category_move_candidates) if not move_actions else 0}",
        "",
        "## Automatic Actions",
        "",
        "These are safe enough to review and then apply with confirmation.",
        "",
    ]

    if merge_actions:
        lines.extend(
            [
                "### Duplicate Playlist Title Merges",
                "",
            ]
        )
        for action in merge_actions:
            source = action["source_playlist"]
            target = action["target_playlist"]
            lines.append(
                f"- Merge `{source['playlist_title']}` ({source['item_count']} items) into "
                f"`{target['playlist_title']}` ({target['item_count']} items). "
                f"Move {len(action['move_items'])} unique items and remove {len(action['remove_items'])} duplicates."
            )
        lines.append("")

    if move_actions:
        lines.extend(
            [
                "### Category Moves",
                "",
            ]
        )
        for action in move_actions[:25]:
            lines.append(
                f"- `{action['title']}`: `{action['from_playlist']['playlist_title']}` -> "
                f"`{action['to_playlist']['playlist_title']}`. Reason: {action['rule']}"
            )
        if len(move_actions) > 25:
            lines.append(f"- ... {len(move_actions) - 25} more category move actions in the JSON plan.")
        lines.append("")

    if category_move_candidates and not move_actions:
        lines.extend(
            [
                "## Suggested Reorganization",
                "",
                "These are not in the apply plan yet. Review them first. If they look right, rerun analyze with category moves enabled.",
                "",
            ]
        )
        for action in category_move_candidates[:25]:
            lines.append(
                f"- `{action['title']}`: `{action['from_playlist']['playlist_title']}` -> "
                f"`{action['to_playlist']['playlist_title']}`. Reason: {action['rule']}"
            )
        if len(category_move_candidates) > 25:
            lines.append(
                f"- ... {len(category_move_candidates) - 25} more suggested category moves in the JSON plan review section."
            )
        lines.append("")

    if duplicate_actions:
        lines.extend(
            [
                "### Duplicate Video Cleanup",
                "",
            ]
        )
        for action in duplicate_actions[:20]:
            remove_titles = ", ".join(item["playlist_title"] for item in action["remove_from"])
            lines.append(
                f"- Keep `{action['title'] or action['video_id']}` in `{action['keep_in']['playlist_title']}` and remove from {remove_titles}."
            )
        if len(duplicate_actions) > 20:
            lines.append(f"- ... {len(duplicate_actions) - 20} more duplicate cleanup actions in the JSON plan.")
        lines.append("")

    if deleted_actions:
        lines.extend(
            [
                "### Deleted Video Cleanup",
                "",
            ]
        )
        for action in deleted_actions[:20]:
            lines.append(f"- Remove deleted entry from `{action['from_playlist']['playlist_title']}`.")
        if len(deleted_actions) > 20:
            lines.append(f"- ... {len(deleted_actions) - 20} more deleted video removals in the JSON plan.")
        lines.append("")

    lines.extend(
        [
            "## Manual Review Candidates",
            "",
            "These are not auto applied. They are the likely playlist compaction targets to review by hand.",
            "",
        ]
    )

    if overlap_candidates:
        for review in overlap_candidates[:20]:
            lines.append(
                f"- `{review['left_playlist']}` vs `{review['right_playlist']}`: "
                f"{review['shared_videos']} shared, jaccard {review['jaccard']}, containment {review['containment']}."
            )
        if len(overlap_candidates) > 20:
            lines.append(f"- ... {len(overlap_candidates) - 20} more overlap pairs in the JSON plan review section.")
    else:
        lines.append("- No strong overlap pairs found.")

    lines.append("")

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines), encoding="utf-8")
