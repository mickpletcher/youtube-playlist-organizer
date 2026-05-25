from src.analysis.rules import find_category_moves, load_rules_config, normalize_playlist_title, validate_rules_config


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


def test_weighted_negative_keywords_skip_false_positive():
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
                "source_playlists": ["Tech"],
                "target_playlist": "ChatGPT",
                "keyword_sets": [["gpt"]],
                "negative_keyword_sets": [
                    {
                        "keywords": ["gpt", "partition"],
                        "weight": 70,
                        "reason": "Not AI content.",
                    }
                ],
                "reason": "ChatGPT content should live in ChatGPT.",
            }
        ],
    }
    playlists_data = [
        {
            "id": "tech-id",
            "title": "Tech",
            "privacy": "public",
            "items": [
                {
                    "id": "tech-item-1",
                    "video_id": "video-1",
                    "title": "Fix GPT partition tables",
                    "position": 0,
                }
            ],
        }
    ]

    assert find_category_moves(playlists_data, config) == []


def test_validate_rules_config_reports_invalid_values():
    errors = validate_rules_config(
        {
            "privacy_defaults": {"created_playlist_privacy": "friends"},
            "keep_rules": {
                "preferred_playlist_titles": "favorites",
                "preferred_privacy_order": ["private", "friends"],
            },
            "playlist_merge_preferences": {"canonical_playlist_strategy": "newest"},
            "playlist_aliases": [],
            "token_aliases": {},
            "category_rules": [
                {
                    "source_playlists": [],
                    "target_playlist": "",
                    "keyword_sets": [["valid"], "invalid"],
                    "negative_keyword_sets": [{"keywords": ["bad"], "weight": 101}],
                }
            ],
        }
    )

    assert "privacy_defaults.created_playlist_privacy must be private, unlisted, or public." in errors
    assert "keep_rules.preferred_playlist_titles must be a list." in errors
    assert "playlist_merge_preferences.canonical_playlist_strategy must be largest_first." in errors
    assert "category_rules[1].negative_keyword_sets[1] weight must be an integer from 1 to 100." in errors


def test_category_suggestion_filters_block_sensitive_source_playlists():
    config = {
        "privacy_defaults": {"created_playlist_privacy": "private"},
        "keep_rules": {
            "preferred_playlist_titles": ["favorites"],
            "preferred_privacy_order": ["private", "public"],
        },
        "playlist_merge_preferences": {"prefer_private_target": True},
        "category_suggestion_filters": {
            "source_playlist_allowlist": [],
            "source_playlist_blocklist": ["Favorites"],
            "target_playlist_allowlist": [],
            "target_playlist_blocklist": [],
        },
        "playlist_aliases": {},
        "token_aliases": {},
        "category_rules": [
            {
                "source_playlists": ["Favorites"],
                "target_playlist": "ChatGPT",
                "keyword_sets": [["chatgpt"]],
                "reason": "ChatGPT content should move.",
            }
        ],
    }
    playlists_data = [
        {
            "id": "favorites-id",
            "title": "Favorites",
            "privacy": "private",
            "items": [
                {
                    "id": "favorites-item-1",
                    "video_id": "video-1",
                    "title": "ChatGPT Tutorial",
                    "position": 0,
                }
            ],
        }
    ]

    assert find_category_moves(playlists_data, config) == []


def test_category_suggestion_filters_allow_only_named_targets():
    config = {
        "privacy_defaults": {"created_playlist_privacy": "private"},
        "keep_rules": {
            "preferred_playlist_titles": ["favorites"],
            "preferred_privacy_order": ["private", "public"],
        },
        "playlist_merge_preferences": {"prefer_private_target": True},
        "category_suggestion_filters": {
            "source_playlist_allowlist": [],
            "source_playlist_blocklist": [],
            "target_playlist_allowlist": ["Prompt Engineering"],
            "target_playlist_blocklist": [],
        },
        "playlist_aliases": {},
        "token_aliases": {},
        "category_rules": [
            {
                "source_playlists": ["AI"],
                "target_playlist": "ChatGPT",
                "keyword_sets": [["chatgpt"]],
                "reason": "ChatGPT content should move.",
            },
            {
                "source_playlists": ["AI"],
                "target_playlist": "Prompt Engineering",
                "keyword_sets": [["prompt"]],
                "reason": "Prompt content should move.",
            },
        ],
    }
    playlists_data = [
        {
            "id": "ai-id",
            "title": "AI",
            "privacy": "public",
            "items": [
                {"id": "ai-1", "video_id": "video-1", "title": "ChatGPT Tutorial", "position": 0},
                {"id": "ai-2", "video_id": "video-2", "title": "Prompt Tutorial", "position": 1},
            ],
        }
    ]

    moves = find_category_moves(playlists_data, config)

    assert [move["to_playlist"]["playlist_title"] for move in moves] == ["Prompt Engineering"]
