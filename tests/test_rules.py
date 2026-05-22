from src.analysis.rules import find_category_moves, load_rules_config, normalize_playlist_title


def test_load_rules_config_supports_yaml_and_alias_normalization(tmp_path):
    config_path = tmp_path / "rules.yaml"
    config_path.write_text(
        "\n".join(
            [
                "privacy_defaults:",
                "  created_playlist_privacy: private",
                "keep_rules:",
                "  preferred_playlist_titles:",
                "    - favorites",
                "  preferred_privacy_order:",
                "    - private",
                "playlist_merge_preferences:",
                "  prefer_private_target: true",
                "playlist_aliases:",
                "  rving: rv",
                "token_aliases:",
                "  recipes: recipe",
                "category_rules: []",
            ]
        ),
        encoding="utf-8",
    )

    config = load_rules_config(str(config_path))

    assert normalize_playlist_title("RVing", config) == "rv"
    assert normalize_playlist_title("Recipes", config) == "recipe"


def test_find_category_moves_uses_config_rules_and_confidence(tmp_path):
    config = {
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
                "target_playlist": "ChatGPT",
                "keyword_sets": [["chatgpt"], ["custom gpt"]],
                "reason": "ChatGPT content should live in ChatGPT.",
            }
        ],
    }

    playlists_data = [
        {
            "id": "ai-id",
            "title": "AI",
            "privacy": "public",
            "items": [
                {
                    "id": "ai-item-1",
                    "video_id": "video-1",
                    "title": "How to Create Custom GPTs in ChatGPT",
                    "position": 0,
                }
            ],
        },
        {
            "id": "chatgpt-id",
            "title": "ChatGPT",
            "privacy": "private",
            "items": [],
        },
    ]

    moves = find_category_moves(playlists_data, config)

    assert len(moves) == 1
    assert moves[0]["to_playlist"]["playlist_title"] == "ChatGPT"
    assert moves[0]["confidence_label"] == "high"
    assert moves[0]["confidence_score"] >= 80
    assert "target playlist already exists" in moves[0]["confidence_reasons"]
