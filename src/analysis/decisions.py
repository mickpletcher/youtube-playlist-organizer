from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VALID_REVIEW_STATUSES = {"approved", "rejected", "undecided"}
PERSISTED_REVIEW_STATUSES = {"approved", "rejected"}


def normalize_review_status(value: str | None) -> str:
    status = (value or "").strip().lower()
    return status if status in VALID_REVIEW_STATUSES else "undecided"


def build_decision_key(
    review_type: str,
    video_id: str = "",
    title: str = "",
    source_playlist: str = "",
    target_playlist: str = "",
) -> str:
    raw_key = "|".join(
        [
            review_type.strip().lower(),
            video_id.strip(),
            title.strip().lower(),
            source_playlist.strip().lower(),
            target_playlist.strip().lower(),
        ]
    )
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]


def decision_key_for_category_move(action: dict[str, Any]) -> str:
    return build_decision_key(
        review_type="category_move",
        video_id=action.get("video_id", ""),
        title=action.get("title", ""),
        source_playlist=action.get("from_playlist", {}).get("playlist_title", ""),
        target_playlist=action.get("to_playlist", {}).get("playlist_title", ""),
    )


def decision_key_for_overlap(review: dict[str, Any]) -> str:
    return build_decision_key(
        review_type="overlap",
        source_playlist=review.get("left_playlist", ""),
        target_playlist=review.get("right_playlist", ""),
    )


def decision_key_for_liked_video_flag(item: dict[str, Any]) -> str:
    return build_decision_key(
        review_type="liked_video_flag",
        video_id=item.get("video_id", ""),
        title=item.get("title", ""),
        source_playlist=item.get("playlist_title", ""),
    )


def load_review_decisions(path: str | None = None) -> dict[str, dict[str, Any]]:
    if not path:
        return {}

    decisions_path = Path(path)
    if not decisions_path.exists():
        return {}

    payload = json.loads(decisions_path.read_text(encoding="utf-8"))
    decisions = {}
    for decision in payload.get("decisions", []):
        status = normalize_review_status(decision.get("review_status"))
        if status not in PERSISTED_REVIEW_STATUSES:
            continue
        decision_key = decision.get("decision_key", "")
        if decision_key:
            decisions[decision_key] = {**decision, "review_status": status}
    return decisions


def apply_decision_metadata(item: dict[str, Any], decision_key: str, decisions: dict[str, dict[str, Any]]) -> None:
    decision = decisions.get(decision_key, {})
    item["decision_key"] = decision_key
    item["review_status"] = decision.get("review_status", "undecided")
    if decision.get("updated_at"):
        item["decision_updated_at"] = decision["updated_at"]


def save_decisions_from_review_csv(review_csv: str, decisions_output: str) -> int:
    decisions = load_review_decisions(decisions_output)
    now = datetime.now(timezone.utc).isoformat()

    with open(review_csv, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            status = normalize_review_status(row.get("review_status"))
            decision_key = row.get("decision_key", "").strip()
            if not decision_key or status not in PERSISTED_REVIEW_STATUSES:
                continue

            decisions[decision_key] = {
                "decision_key": decision_key,
                "review_type": row.get("review_type", ""),
                "review_status": status,
                "title": row.get("title", ""),
                "video_id": row.get("video_id", ""),
                "source_playlist": row.get("source_playlist", ""),
                "target_playlist": row.get("target_playlist", ""),
                "reason": row.get("reason", ""),
                "updated_at": now,
            }

    output_path = Path(decisions_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ordered_decisions = sorted(
        decisions.values(),
        key=lambda decision: (
            decision.get("review_type", ""),
            decision.get("source_playlist", "").lower(),
            decision.get("target_playlist", "").lower(),
            decision.get("title", "").lower(),
            decision.get("decision_key", ""),
        ),
    )
    output_path.write_text(
        json.dumps(
            {
                "updated_at": now,
                "decisions": ordered_decisions,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return len(ordered_decisions)


def save_decision_by_key(
    decision_key: str,
    review_status: str,
    review_csv: str,
    decisions_output: str,
) -> dict[str, Any]:
    status = normalize_review_status(review_status)
    if status not in PERSISTED_REVIEW_STATUSES:
        raise ValueError("review_status must be approved or rejected.")

    with open(review_csv, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    matching_row = next((row for row in rows if row.get("decision_key", "").strip() == decision_key), None)
    if not matching_row:
        raise KeyError(decision_key)

    decisions = load_review_decisions(decisions_output)
    now = datetime.now(timezone.utc).isoformat()
    decision = {
        "decision_key": decision_key,
        "review_type": matching_row.get("review_type", ""),
        "review_status": status,
        "title": matching_row.get("title", ""),
        "video_id": matching_row.get("video_id", ""),
        "source_playlist": matching_row.get("source_playlist", ""),
        "target_playlist": matching_row.get("target_playlist", ""),
        "reason": matching_row.get("reason", ""),
        "updated_at": now,
    }
    decisions[decision_key] = decision

    output_path = Path(decisions_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "updated_at": now,
                "decisions": sorted(
                    decisions.values(),
                    key=lambda item: (
                        item.get("review_type", ""),
                        item.get("source_playlist", "").lower(),
                        item.get("target_playlist", "").lower(),
                        item.get("title", "").lower(),
                        item.get("decision_key", ""),
                    ),
                ),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return decision
