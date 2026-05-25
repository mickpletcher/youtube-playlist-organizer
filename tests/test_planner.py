import json

from src.analysis.decisions import build_decision_key
from src.analysis.duplicates import find_duplicates
from src.analysis.planner import (
    build_action_filter,
    create_rollback_snapshot,
    generate_plan,
    write_html_report,
    write_move_review,
)


def test_generate_plan_uses_keep_rules_and_created_playlist_privacy(tmp_path):
    config_path = tmp_path / "rules.json"
    config_path.write_text(
        json.dumps(
            {
                "privacy_defaults": {"created_playlist_privacy": "unlisted"},
                "keep_rules": {
                    "preferred_playlist_titles": ["favorites"],
                    "preferred_privacy_order": ["private", "public"],
                },
                "playlist_merge_preferences": {"prefer_private_target": True},
                "playlist_aliases": {},
                "token_aliases": {},
                "category_rules": [
                    {
                        "source_playlists": ["AI"],
                        "target_playlist": "Prompt Engineering",
                        "keyword_sets": [["prompt"]],
                        "reason": "Prompt content should move.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    playlists_data = [
        {
            "id": "favorites-id",
            "title": "Favorites",
            "privacy": "public",
            "items": [
                {
                    "id": "fav-item-1",
                    "video_id": "dup-video",
                    "title": "Duplicate Video",
                    "position": 0,
                }
            ],
        },
        {
            "id": "private-id",
            "title": "Private Notes",
            "privacy": "private",
            "items": [
                {
                    "id": "private-item-1",
                    "video_id": "dup-video",
                    "title": "Duplicate Video",
                    "position": 0,
                }
            ],
        },
        {
            "id": "ai-id",
            "title": "AI",
            "privacy": "public",
            "items": [
                {
                    "id": "ai-item-1",
                    "video_id": "prompt-video",
                    "title": "Prompt Engineering Tutorial",
                    "position": 0,
                }
            ],
        },
    ]

    duplicates = find_duplicates(playlists_data)
    plan = generate_plan(
        duplicates,
        playlists_data,
        include_category_moves=True,
        rules_config_path=str(config_path),
    )

    duplicate_action = next(action for action in plan["actions"] if action["action"] == "remove_duplicate")
    create_action = next(action for action in plan["actions"] if action["action"] == "create_playlist")
    move_action = next(action for action in plan["actions"] if action["action"] == "move_to_playlist")

    assert duplicate_action["keep_in"]["playlist_title"] == "Favorites"
    assert create_action["privacy"] == "unlisted"
    assert move_action["to_playlist"]["playlist_title"] == "Prompt Engineering"


def test_generate_plan_uses_merge_preferences_for_private_target(tmp_path):
    config_path = tmp_path / "rules.json"
    config_path.write_text(
        json.dumps(
            {
                "privacy_defaults": {"created_playlist_privacy": "private"},
                "keep_rules": {
                    "preferred_playlist_titles": ["favorites"],
                    "preferred_privacy_order": ["private", "public"],
                },
                "playlist_merge_preferences": {"prefer_private_target": True},
                "playlist_aliases": {"rving": "rv"},
                "token_aliases": {},
                "category_rules": [],
            }
        ),
        encoding="utf-8",
    )

    playlists_data = [
        {
            "id": "rv-public",
            "title": "RV",
            "privacy": "public",
            "items": [],
        },
        {
            "id": "rving-private",
            "title": "RVing",
            "privacy": "private",
            "items": [{"id": "rving-1", "video_id": "video-1", "title": "RV Tips", "position": 0}],
        },
    ]

    plan = generate_plan([], playlists_data, rules_config_path=str(config_path))
    merge_action = next(action for action in plan["actions"] if action["action"] == "merge_playlist")

    assert merge_action["target_playlist"]["playlist_title"] == "RVing"
    assert merge_action["source_playlist"]["playlist_title"] == "RV"


def test_generate_plan_uses_saved_review_decisions(tmp_path):
    config_path = tmp_path / "rules.json"
    config_path.write_text(
        json.dumps(
            {
                "privacy_defaults": {"created_playlist_privacy": "private"},
                "keep_rules": {
                    "preferred_playlist_titles": ["favorites"],
                    "preferred_privacy_order": ["private", "public"],
                },
                "playlist_merge_preferences": {"prefer_private_target": True},
                "playlist_aliases": {},
                "token_aliases": {},
                "category_rules": [
                    {
                        "source_playlists": ["AI"],
                        "target_playlist": "Prompt Engineering",
                        "keyword_sets": [["prompt"]],
                        "reason": "Prompt content should move.",
                    },
                    {
                        "source_playlists": ["AI"],
                        "target_playlist": "ChatGPT",
                        "keyword_sets": [["chatgpt"]],
                        "reason": "ChatGPT content should move.",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    prompt_key = build_decision_key(
        "category_move",
        video_id="prompt-video",
        title="Prompt Engineering Tutorial",
        source_playlist="AI",
        target_playlist="Prompt Engineering",
    )
    chatgpt_key = build_decision_key(
        "category_move",
        video_id="chatgpt-video",
        title="ChatGPT Tutorial",
        source_playlist="AI",
        target_playlist="ChatGPT",
    )
    decisions_path = tmp_path / "review-decisions.json"
    decisions_path.write_text(
        json.dumps(
            {
                "decisions": [
                    {"decision_key": prompt_key, "review_status": "approved"},
                    {"decision_key": chatgpt_key, "review_status": "rejected"},
                ]
            }
        ),
        encoding="utf-8",
    )

    playlists_data = [
        {
            "id": "ai-id",
            "title": "AI",
            "privacy": "private",
            "items": [
                {
                    "id": "ai-prompt",
                    "video_id": "prompt-video",
                    "title": "Prompt Engineering Tutorial",
                    "position": 0,
                },
                {
                    "id": "ai-chatgpt",
                    "video_id": "chatgpt-video",
                    "title": "ChatGPT Tutorial",
                    "position": 1,
                },
            ],
        },
    ]

    plan = generate_plan(
        [],
        playlists_data,
        include_category_moves=False,
        rules_config_path=str(config_path),
        decisions_path=str(decisions_path),
    )

    move_actions = [action for action in plan["actions"] if action["action"] == "move_to_playlist"]
    candidate_titles = [action["title"] for action in plan["review"]["category_move_candidates"]]

    assert [action["title"] for action in move_actions] == ["Prompt Engineering Tutorial"]
    assert move_actions[0]["review_status"] == "approved"
    assert candidate_titles == ["Prompt Engineering Tutorial"]
    assert plan["review"]["rejected_category_moves"] == 1


def test_generate_plan_action_filter_limits_automatic_actions(tmp_path):
    config_path = tmp_path / "rules.json"
    config_path.write_text(
        json.dumps(
            {
                "privacy_defaults": {"created_playlist_privacy": "private"},
                "keep_rules": {
                    "preferred_playlist_titles": ["favorites"],
                    "preferred_privacy_order": ["private", "public"],
                },
                "playlist_merge_preferences": {"prefer_private_target": True},
                "playlist_aliases": {"rving": "rv"},
                "token_aliases": {},
                "category_rules": [],
            }
        ),
        encoding="utf-8",
    )
    playlists_data = [
        {
            "id": "favorites-id",
            "title": "Favorites",
            "privacy": "private",
            "items": [{"id": "fav-1", "video_id": "dup", "title": "Duplicate", "position": 0}],
        },
        {
            "id": "ai-id",
            "title": "AI",
            "privacy": "public",
            "items": [
                {"id": "ai-1", "video_id": "dup", "title": "Duplicate", "position": 0},
                {"id": "ai-2", "video_id": "deleted", "title": "Deleted video", "position": 1},
            ],
        },
        {
            "id": "rv-id",
            "title": "RV",
            "privacy": "public",
            "items": [],
        },
        {
            "id": "rving-id",
            "title": "RVing",
            "privacy": "private",
            "items": [{"id": "rving-1", "video_id": "rv", "title": "RV Tips", "position": 0}],
        },
    ]
    duplicates = find_duplicates(playlists_data)

    plan = generate_plan(
        duplicates,
        playlists_data,
        rules_config_path=str(config_path),
        action_filter=build_action_filter(only_deleted=True),
    )

    assert [action["action"] for action in plan["actions"]] == ["remove_deleted"]


def test_write_move_review_groups_category_moves(tmp_path):
    output = tmp_path / "playlist-move-review.md"
    plan = {
        "generated_at": "2026-05-25T00:00:00Z",
        "decisions_path": "data/review-decisions.json",
        "review": {
            "category_move_candidates": [
                {
                    "title": "Prompt Video",
                    "decision_key": "key-1",
                    "review_status": "approved",
                    "confidence_label": "high",
                    "confidence_score": 90,
                    "from_playlist": {"playlist_title": "AI"},
                    "to_playlist": {"playlist_title": "Prompt Engineering"},
                    "negative_keyword_matches": [],
                }
            ]
        },
    }

    write_move_review(plan, str(output))

    text = output.read_text(encoding="utf-8")
    assert "## AI -> Prompt Engineering" in text
    assert "decision `key-1`" in text


def test_write_html_report_exports_review_page(tmp_path):
    output = tmp_path / "playlist-report.html"
    plan = {
        "generated_at": "2026-05-25T00:00:00Z",
        "rules_config_path": "config/playlist-rules.json",
        "decisions_path": "data/review-decisions.json",
        "summary": {
            "actions": 1,
            "duplicate_videos": 0,
            "deleted_videos": 0,
            "category_moves": 1,
            "playlist_merges": 0,
            "playlist_item_moves": 1,
            "playlist_item_removals": 1,
        },
        "actions": [{"action": "move_to_playlist", "title": "Prompt Video"}],
        "review": {
            "category_move_candidates": [
                {
                    "title": "Prompt Video",
                    "from_playlist": {"playlist_title": "AI"},
                    "to_playlist": {"playlist_title": "Prompt Engineering"},
                    "review_status": "approved",
                    "confidence_score": 90,
                }
            ],
            "overlap_candidates": [],
            "liked_video_flags": [],
            "rejected_category_moves": 0,
        },
    }

    write_html_report(plan, str(output))

    text = output.read_text(encoding="utf-8")
    assert "<h1>Playlist Analysis Report</h1>" in text
    assert "Prompt Video" in text


def test_create_rollback_snapshot_copies_existing_files(tmp_path):
    source = tmp_path / "playlist-plan.json"
    snapshot_dir = tmp_path / "snapshots"
    source.write_text('{"actions":[]}', encoding="utf-8")

    snapshot = create_rollback_snapshot(str(snapshot_dir), source_paths=[str(source), str(tmp_path / "missing.json")])

    assert (snapshot / "playlist-plan.json").exists()
    assert (snapshot / "manifest.json").exists()
