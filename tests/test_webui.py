from src.webui.server import build_cli_command, get_review_groups


def test_build_cli_command_for_analyze_with_category_moves():
    command = build_cli_command(
        {
            "action": "analyze",
            "rules_config": "config/playlist-rules.json",
            "include_category_moves": "on",
        }
    )

    assert command[3] == "analyze"
    assert "--rules-config" in command
    assert "config/playlist-rules.json" in command
    assert "--include-category-moves" in command


def test_build_cli_command_for_analyze_filters():
    command = build_cli_command(
        {
            "action": "analyze",
            "rules_config": "config/playlist-rules.json",
            "only_deleted": "on",
            "only_category_suggestions": "on",
        }
    )

    assert "--only-deleted" in command
    assert "--only-category-suggestions" in command


def test_build_cli_command_for_validate_and_save_decisions():
    validate_command = build_cli_command(
        {
            "action": "validate_config",
            "rules_config": "config/playlist-rules.json",
        }
    )
    save_command = build_cli_command({"action": "save_decisions"})

    assert validate_command[3] == "validate-config"
    assert save_command[3] == "save-decisions"


def test_build_cli_command_rejects_live_apply_without_confirmation():
    try:
        build_cli_command({"action": "apply_live", "confirm_text": "NOPE"})
    except ValueError as exc:
        assert "Type APPLY exactly" in str(exc)
    else:
        raise AssertionError("Expected live apply confirmation failure")


def test_get_review_groups_groups_moves_and_overlap_candidates():
    plan = {
        "review": {
            "category_move_candidates": [
                {
                    "title": "Video A",
                    "confidence_score": 90,
                    "from_playlist": {"playlist_title": "AI"},
                    "to_playlist": {"playlist_title": "ChatGPT"},
                    "confidence_reasons": ["matched keywords"],
                    "confidence_label": "high",
                    "rule": "Move AI to ChatGPT",
                },
                {
                    "title": "Video B",
                    "confidence_score": 70,
                    "from_playlist": {"playlist_title": "AI"},
                    "to_playlist": {"playlist_title": "ChatGPT"},
                    "confidence_reasons": ["matched keywords"],
                    "confidence_label": "medium",
                    "rule": "Move AI to ChatGPT",
                },
            ],
            "overlap_candidates": [
                {
                    "left_playlist": "RV",
                    "right_playlist": "RVing",
                    "merge_candidate": True,
                    "shared_videos": 2,
                    "jaccard": 0.5,
                    "containment": 1.0,
                    "review_reason": "normalized titles match",
                },
                {
                    "left_playlist": "Training",
                    "right_playlist": "Workout",
                    "merge_candidate": False,
                    "shared_videos": 5,
                    "jaccard": 0.2,
                    "containment": 0.3,
                    "review_reason": "shared videos",
                },
            ],
        }
    }

    move_groups, overlap_groups = get_review_groups(plan)

    assert len(move_groups) == 1
    assert move_groups[0]["source"] == "AI"
    assert move_groups[0]["target"] == "ChatGPT"
    assert move_groups[0]["count"] == 2
    assert move_groups[0]["items"][0]["title"] == "Video A"

    assert len(overlap_groups) == 2
    assert overlap_groups[0]["group"] == "Merge Candidates"
    assert overlap_groups[1]["group"] == "Overlap Review"
