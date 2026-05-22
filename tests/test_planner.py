import json

from src.analysis.duplicates import find_duplicates
from src.analysis.planner import generate_plan


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
