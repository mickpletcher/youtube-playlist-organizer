from __future__ import annotations

import csv
import html
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.analysis.decisions import (
    apply_decision_metadata,
    decision_key_for_category_move,
    decision_key_for_liked_video_flag,
    decision_key_for_overlap,
    load_review_decisions,
)
from src.analysis.rules import (
    build_overlap_review,
    find_category_moves,
    find_liked_video_flags,
    find_same_title_playlist_merges,
    get_keep_rules,
    get_privacy_defaults,
    load_rules_config,
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
    rules_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    occurrences = duplicate["occurrences"]
    keep_rules = get_keep_rules(rules_config)
    preferred_titles = [
        title.strip().lower()
        for title in keep_rules.get("preferred_playlist_titles", [])
        if title.strip()
    ]

    for preferred_title in preferred_titles:
        matching = [
            occurrence
            for occurrence in occurrences
            if occurrence["playlist_title"].strip().lower() == preferred_title
        ]
        if matching:
            return matching[0]

    preferred_privacy_order = [
        privacy.strip().lower()
        for privacy in keep_rules.get("preferred_privacy_order", [])
        if privacy.strip()
    ]
    for preferred_privacy in preferred_privacy_order:
        matching = [
            occurrence
            for occurrence in occurrences
            if occurrence.get("playlist_privacy", "").strip().lower() == preferred_privacy
        ]
        if matching:
            occurrences = matching
            break

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


def build_action_filter(
    only_duplicates: bool = False,
    only_deleted: bool = False,
    only_merges: bool = False,
    only_category_suggestions: bool = False,
) -> set[str]:
    selected = set()
    if only_duplicates:
        selected.add("duplicates")
    if only_deleted:
        selected.add("deleted")
    if only_merges:
        selected.add("merges")
    if only_category_suggestions:
        selected.add("category")
    return selected or {"duplicates", "deleted", "merges", "category"}


def create_rollback_snapshot(
    snapshot_dir: str = "data/snapshots",
    source_paths: list[str] | None = None,
) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = Path(snapshot_dir) / timestamp
    destination.mkdir(parents=True, exist_ok=True)

    paths = source_paths or [
        "data/playlists.json",
        "data/playlist-plan.json",
        "data/playlist-report.md",
        "data/playlist-review.csv",
        "data/playlist-move-review.md",
        "data/review-decisions.json",
    ]
    manifest = []
    for source_path in paths:
        source = Path(source_path)
        if not source.exists():
            continue
        target = destination / source.name
        shutil.copy2(source, target)
        manifest.append({"source": str(source), "snapshot": str(target)})

    (destination / "manifest.json").write_text(
        json.dumps(
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "files": manifest,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return destination


def generate_plan(
    duplicates: list[dict[str, Any]],
    playlists_data: list[dict[str, Any]],
    include_category_moves: bool = False,
    rules_config_path: str | None = None,
    decisions_path: str | None = None,
    action_filter: set[str] | None = None,
) -> dict[str, Any]:
    profiles = build_playlist_profiles(playlists_data)
    rules_config = load_rules_config(rules_config_path)
    review_decisions = load_review_decisions(decisions_path)
    action_filter = action_filter or {"duplicates", "deleted", "merges", "category"}
    actions = []
    seen_playlist_creations = set()

    if "duplicates" in action_filter:
        for duplicate in duplicates:
            keep_in = choose_keep_occurrence(duplicate, profiles, rules_config)
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

    if "deleted" in action_filter:
        actions.extend(find_deleted_video_items(playlists_data))

    duplicate_lookup = build_duplicate_lookup(actions)
    category_moves = find_category_moves(playlists_data, rules_config)
    planned_category_moves = []
    rejected_category_moves = 0
    for move in category_moves:
        if should_skip_move_due_to_duplicate(move, duplicate_lookup):
            continue

        decision_key = decision_key_for_category_move(move)
        apply_decision_metadata(move, decision_key, review_decisions)
        if move["review_status"] == "rejected":
            rejected_category_moves += 1
            continue

        planned_category_moves.append(move)
        if "category" not in action_filter or (not include_category_moves and move["review_status"] != "approved"):
            continue

        target_title = move["to_playlist"]["playlist_title"]
        if not move["to_playlist"].get("playlist_id") and target_title not in seen_playlist_creations:
            privacy_defaults = get_privacy_defaults(rules_config)
            actions.append(
                {
                    "action": "create_playlist",
                    "title": target_title,
                    "privacy": privacy_defaults.get(
                        "created_playlist_privacy",
                        move["to_playlist"]["playlist_privacy"],
                    ),
                    "reason": "Category rule requires a dedicated playlist",
                }
            )
            seen_playlist_creations.add(target_title)

        actions.append(move)

    if "merges" in action_filter:
        merge_actions = find_same_title_playlist_merges(playlists_data, rules_config)
        actions.extend(merge_actions)

    summary = summarize_actions(actions)
    overlap_review = build_overlap_review(playlists_data, rules_config)
    liked_video_flags = find_liked_video_flags(playlists_data, rules_config)
    for review in overlap_review:
        apply_decision_metadata(review, decision_key_for_overlap(review), review_decisions)
    for item in liked_video_flags:
        apply_decision_metadata(item, decision_key_for_liked_video_flag(item), review_decisions)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "review": {
            "overlap_candidates": overlap_review,
            "category_move_candidates": planned_category_moves,
            "liked_video_flags": liked_video_flags,
            "rejected_category_moves": rejected_category_moves,
        },
        "rules_config_path": rules_config_path or "auto",
        "decisions_path": decisions_path or "none",
        "action_filter": sorted(action_filter),
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
    liked_video_flags = plan.get("review", {}).get("liked_video_flags", [])
    rejected_category_moves = plan.get("review", {}).get("rejected_category_moves", 0)
    actions = plan.get("actions", [])
    duplicate_actions = [action for action in actions if action["action"] == "remove_duplicate"]
    deleted_actions = [action for action in actions if action["action"] == "remove_deleted"]
    move_actions = [action for action in actions if action["action"] == "move_to_playlist"]
    merge_actions = [action for action in actions if action["action"] == "merge_playlist"]

    lines = [
        "# Playlist Analysis Report",
        "",
        f"Generated: `{plan['generated_at']}`",
        f"Rules config: `{plan.get('rules_config_path', 'auto')}`",
        f"Review decisions: `{plan.get('decisions_path', 'none')}`",
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
        f"- Previously approved category moves queued: {sum(1 for action in move_actions if action.get('review_status') == 'approved')}",
        f"- Rejected category moves skipped: {rejected_category_moves}",
        f"- Liked video self image review flags: {len(liked_video_flags)}",
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
                f"Normalized match: `{action['normalized_title']}`. "
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
            confidence_reasons = "; ".join(action.get("confidence_reasons", []))
            lines.append(
                f"- `{action['title']}`: `{action['from_playlist']['playlist_title']}` -> "
                f"`{action['to_playlist']['playlist_title']}`. "
                f"Review status: {action.get('review_status', 'undecided')}. "
                f"Confidence: {action.get('confidence_label', 'unknown')} ({action.get('confidence_score', 0)}). "
                f"Reason: {action['rule']}. Details: {confidence_reasons}"
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
            confidence_reasons = "; ".join(action.get("confidence_reasons", []))
            lines.append(
                f"- `{action['title']}`: `{action['from_playlist']['playlist_title']}` -> "
                f"`{action['to_playlist']['playlist_title']}`. "
                f"Review status: {action.get('review_status', 'undecided')}. "
                f"Confidence: {action.get('confidence_label', 'unknown')} ({action.get('confidence_score', 0)}). "
                f"Reason: {action['rule']}. Details: {confidence_reasons}"
            )
        if len(category_move_candidates) > 25:
            lines.append(
                f"- ... {len(category_move_candidates) - 25} more suggested category moves in the JSON plan review section."
            )
        lines.append("")

    if liked_video_flags:
        lines.extend(
            [
                "## Liked Video Self Image Review",
                "",
                "These are review only flags from the liked videos playlist. Nothing here is auto removed.",
                "",
            ]
        )
        for item in liked_video_flags[:25]:
            matched = ", ".join(item.get("matched_keywords", []))
            lines.append(
                f"- `{item['title']}`: severity {item['severity']}, confidence "
                f"{item['confidence_label']} ({item['confidence_score']}). "
                f"Reason: {item['reason']} Matched: {matched}"
            )
        if len(liked_video_flags) > 25:
            lines.append(
                f"- ... {len(liked_video_flags) - 25} more liked video review flags in the JSON plan review section."
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
                f"{review['shared_videos']} shared, jaccard {review['jaccard']}, containment {review['containment']}. "
                f"Reason: {review['review_reason']}"
            )
        if len(overlap_candidates) > 20:
            lines.append(f"- ... {len(overlap_candidates) - 20} more overlap pairs in the JSON plan review section.")
    else:
        lines.append("- No strong overlap pairs found.")

    lines.append("")

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def write_review_csv(
    plan: dict[str, Any],
    path: str = "data/playlist-review.csv",
) -> None:
    rows = []

    for action in plan.get("review", {}).get("category_move_candidates", []):
        rows.append(
            {
                "review_type": "category_move",
                "decision_key": action.get("decision_key", ""),
                "review_status": action.get("review_status", "undecided"),
                "title": action["title"],
                "video_id": action.get("video_id", ""),
                "source_playlist": action["from_playlist"]["playlist_title"],
                "target_playlist": action["to_playlist"]["playlist_title"],
                "confidence_label": action.get("confidence_label", ""),
                "confidence_score": action.get("confidence_score", ""),
                "reason": action["rule"],
                "details": "; ".join(action.get("confidence_reasons", [])),
                "shared_videos": "",
                "jaccard": "",
                "containment": "",
                "merge_candidate": "",
            }
        )

    for review in plan.get("review", {}).get("overlap_candidates", []):
        rows.append(
            {
                "review_type": "overlap",
                "decision_key": review.get("decision_key", ""),
                "review_status": review.get("review_status", "undecided"),
                "title": "",
                "video_id": "",
                "source_playlist": review["left_playlist"],
                "target_playlist": review["right_playlist"],
                "confidence_label": "",
                "confidence_score": "",
                "reason": review["review_reason"],
                "details": (
                    f"left_normalized={review['left_normalized']}; "
                    f"right_normalized={review['right_normalized']}"
                ),
                "shared_videos": review["shared_videos"],
                "jaccard": review["jaccard"],
                "containment": review["containment"],
                "merge_candidate": review["merge_candidate"],
            }
        )

    for item in plan.get("review", {}).get("liked_video_flags", []):
        rows.append(
            {
                "review_type": "liked_video_flag",
                "decision_key": item.get("decision_key", ""),
                "review_status": item.get("review_status", "undecided"),
                "title": item["title"],
                "video_id": item.get("video_id", ""),
                "source_playlist": item["playlist_title"],
                "target_playlist": "",
                "confidence_label": item.get("confidence_label", ""),
                "confidence_score": item.get("confidence_score", ""),
                "reason": item["reason"],
                "details": (
                    f"severity={item['severity']}; "
                    f"matched_keywords={', '.join(item.get('matched_keywords', []))}"
                ),
                "shared_videos": "",
                "jaccard": "",
                "containment": "",
                "merge_candidate": "",
            }
        )

    fieldnames = [
        "review_type",
        "decision_key",
        "review_status",
        "title",
        "video_id",
        "source_playlist",
        "target_playlist",
        "confidence_label",
        "confidence_score",
        "reason",
        "details",
        "shared_videos",
        "jaccard",
        "containment",
        "merge_candidate",
    ]

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_move_review(
    plan: dict[str, Any],
    path: str = "data/playlist-move-review.md",
) -> None:
    moves = plan.get("review", {}).get("category_move_candidates", [])
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for move in moves:
        key = (
            move["from_playlist"]["playlist_title"],
            move["to_playlist"]["playlist_title"],
        )
        grouped.setdefault(key, []).append(move)

    lines = [
        "# Playlist Move Review",
        "",
        f"Generated: `{plan['generated_at']}`",
        f"Review decisions: `{plan.get('decisions_path', 'none')}`",
        "",
        "Edit `data/playlist-review.csv` to set `review_status` to `approved`, `rejected`, or `undecided`.",
        "Then run `python -m src.cli save-decisions`.",
        "",
    ]

    if not grouped:
        lines.append("No suggested category moves found.")
    for (source, target), items in sorted(grouped.items()):
        lines.extend(
            [
                f"## {source} -> {target}",
                "",
            ]
        )
        for item in sorted(items, key=lambda value: (-value.get("confidence_score", 0), value["title"].lower())):
            negatives = "; ".join(
                f"{', '.join(match['keywords'])} (-{match['weight']})"
                for match in item.get("negative_keyword_matches", [])
            )
            negative_text = f" Negative matches: {negatives}." if negatives else ""
            lines.append(
                f"- `{item['title']}` | status `{item.get('review_status', 'undecided')}` | "
                f"confidence {item.get('confidence_label', 'unknown')} ({item.get('confidence_score', 0)}) | "
                f"decision `{item.get('decision_key', '')}`.{negative_text}"
            )
        lines.append("")

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def write_html_report(
    plan: dict[str, Any],
    path: str = "data/playlist-report.html",
) -> None:
    summary = plan.get("summary", {})
    review = plan.get("review", {})
    actions = plan.get("actions", [])
    category_moves = review.get("category_move_candidates", [])
    overlap_candidates = review.get("overlap_candidates", [])
    liked_video_flags = review.get("liked_video_flags", [])

    def esc(value: Any) -> str:
        return html.escape(str(value))

    metric_rows = "".join(
        f"<tr><th>{esc(label)}</th><td>{esc(value)}</td></tr>"
        for label, value in [
            ("Planned actions", summary.get("actions", 0)),
            ("Duplicate videos", summary.get("duplicate_videos", 0)),
            ("Deleted videos", summary.get("deleted_videos", 0)),
            ("Category moves", summary.get("category_moves", 0)),
            ("Playlist merges", summary.get("playlist_merges", 0)),
            ("Playlist item moves", summary.get("playlist_item_moves", 0)),
            ("Playlist item removals", summary.get("playlist_item_removals", 0)),
            ("Suggested category moves", len(category_moves)),
            ("Rejected category moves skipped", review.get("rejected_category_moves", 0)),
            ("Liked video review flags", len(liked_video_flags)),
        ]
    )

    action_rows = "".join(
        f"<tr><td>{esc(action.get('action', ''))}</td><td>{esc(action.get('title', action.get('video_id', '')))}</td></tr>"
        for action in actions[:50]
    )
    move_rows = "".join(
        "<tr>"
        f"<td>{esc(move.get('title', ''))}</td>"
        f"<td>{esc(move.get('from_playlist', {}).get('playlist_title', ''))}</td>"
        f"<td>{esc(move.get('to_playlist', {}).get('playlist_title', ''))}</td>"
        f"<td>{esc(move.get('review_status', 'undecided'))}</td>"
        f"<td>{esc(move.get('confidence_score', ''))}</td>"
        "</tr>"
        for move in category_moves[:100]
    )
    overlap_rows = "".join(
        "<tr>"
        f"<td>{esc(item.get('left_playlist', ''))}</td>"
        f"<td>{esc(item.get('right_playlist', ''))}</td>"
        f"<td>{esc(item.get('shared_videos', ''))}</td>"
        f"<td>{esc(item.get('review_reason', ''))}</td>"
        "</tr>"
        for item in overlap_candidates[:100]
    )

    content = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Playlist Analysis Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2933; }}
    h1, h2 {{ color: #17324d; }}
    table {{ border-collapse: collapse; width: 100%; margin: 16px 0 28px; }}
    th, td {{ border: 1px solid #c9d2dc; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #eef3f8; }}
    .muted {{ color: #637083; }}
  </style>
</head>
<body>
  <h1>Playlist Analysis Report</h1>
  <p class="muted">Generated: {esc(plan.get('generated_at', ''))}</p>
  <p class="muted">Rules config: {esc(plan.get('rules_config_path', 'auto'))}</p>
  <p class="muted">Review decisions: {esc(plan.get('decisions_path', 'none'))}</p>

  <h2>Summary</h2>
  <table>{metric_rows}</table>

  <h2>Planned Actions</h2>
  <table><thead><tr><th>Action</th><th>Video or Playlist</th></tr></thead><tbody>{action_rows}</tbody></table>

  <h2>Suggested Category Moves</h2>
  <table><thead><tr><th>Video</th><th>Source</th><th>Target</th><th>Status</th><th>Score</th></tr></thead><tbody>{move_rows}</tbody></table>

  <h2>Overlap Review</h2>
  <table><thead><tr><th>Left</th><th>Right</th><th>Shared Videos</th><th>Reason</th></tr></thead><tbody>{overlap_rows}</tbody></table>
</body>
</html>"""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(content, encoding="utf-8")
