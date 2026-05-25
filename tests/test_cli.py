import json

from typer.testing import CliRunner

from src.cli import app, estimate_quota_cost, limit_actions_by_quota


runner = CliRunner()


def test_apply_preview_does_not_request_youtube_client(monkeypatch, tmp_path):
    plan_path = tmp_path / "playlist-plan.json"
    plan_path.write_text(
        json.dumps(
            {
                "summary": {
                    "actions": 1,
                    "deleted_videos": 0,
                    "category_moves": 0,
                    "playlist_creations": 0,
                    "playlist_merges": 0,
                    "playlist_item_moves": 0,
                    "playlist_item_removals": 1,
                },
                "actions": [
                    {
                        "action": "remove_duplicate",
                        "video_id": "video-1",
                        "title": "Example Video",
                        "keep_in": {"playlist_title": "Favorites"},
                        "remove_from": [{"playlist_title": "AI"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    def fail_get_client(*args, **kwargs):
        raise AssertionError("get_youtube_client should not be called during dry run preview")

    monkeypatch.setattr("src.auth.oauth.get_youtube_client", fail_get_client)

    result = runner.invoke(app, ["apply", "--plan-path", str(plan_path)])

    assert result.exit_code == 0
    assert "Plan actions:" in result.stdout
    assert "Dry run only." in result.stdout


def test_apply_preview_fails_when_plan_is_missing(tmp_path):
    missing_plan = tmp_path / "missing-plan.json"

    result = runner.invoke(app, ["apply", "--plan-path", str(missing_plan)])

    assert result.exit_code == 1
    assert "Run analyze first." in result.stdout


def test_limit_actions_by_quota_selects_leading_actions_only():
    actions = [
        {"action": "remove_deleted"},
        {"action": "move_to_playlist"},
        {"action": "remove_deleted"},
    ]

    selected, selected_cost = limit_actions_by_quota(actions, 150)

    assert selected == actions[:2]
    assert selected_cost == 150
    assert estimate_quota_cost(actions) == 200


def test_apply_preview_shows_quota_chunk(tmp_path):
    plan_path = tmp_path / "playlist-plan.json"
    plan_path.write_text(
        json.dumps(
            {
                "summary": {
                    "actions": 2,
                    "deleted_videos": 2,
                    "category_moves": 0,
                    "playlist_creations": 0,
                    "playlist_merges": 0,
                    "playlist_item_moves": 0,
                    "playlist_item_removals": 2,
                },
                "actions": [
                    {
                        "action": "remove_deleted",
                        "video_id": "video-1",
                        "title": "Deleted video",
                        "from_playlist": {
                            "playlist_title": "AI",
                            "playlist_item_id": "item-1",
                        },
                    },
                    {
                        "action": "remove_deleted",
                        "video_id": "video-2",
                        "title": "Deleted video",
                        "from_playlist": {
                            "playlist_title": "Training",
                            "playlist_item_id": "item-2",
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["apply", "--plan-path", str(plan_path), "--max-quota-cost", "50"],
    )

    assert result.exit_code == 0
    assert "Selected chunk:" in result.stdout
    assert "1 action(s), 50 estimated quota units" in result.stdout
    assert "Skipping 1 later action(s)" in result.stdout


def test_save_decisions_imports_approved_and_rejected_rows(tmp_path):
    review_csv = tmp_path / "playlist-review.csv"
    decisions_output = tmp_path / "review-decisions.json"
    review_csv.write_text(
        "\n".join(
            [
                "review_type,decision_key,review_status,title,video_id,source_playlist,target_playlist,reason",
                "category_move,key-approved,approved,Prompt Video,video-1,AI,Prompt Engineering,Prompt match",
                "category_move,key-rejected,rejected,ChatGPT Video,video-2,AI,ChatGPT,ChatGPT match",
                "category_move,key-undecided,undecided,Other Video,video-3,AI,Other,Other match",
            ]
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "save-decisions",
            "--review-csv",
            str(review_csv),
            "--decisions-output",
            str(decisions_output),
        ],
    )

    payload = json.loads(decisions_output.read_text(encoding="utf-8"))

    assert result.exit_code == 0
    assert "Saved 2 review decision(s)" in result.stdout
    assert [decision["decision_key"] for decision in payload["decisions"]] == [
        "key-rejected",
        "key-approved",
    ]


def test_decide_saves_one_review_decision(tmp_path):
    review_csv = tmp_path / "playlist-review.csv"
    decisions_output = tmp_path / "review-decisions.json"
    review_csv.write_text(
        "\n".join(
            [
                "review_type,decision_key,review_status,title,video_id,source_playlist,target_playlist,reason",
                "category_move,key-approved,undecided,Prompt Video,video-1,AI,Prompt Engineering,Prompt match",
            ]
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "decide",
            "--decision-key",
            "key-approved",
            "--review-status",
            "approved",
            "--review-csv",
            str(review_csv),
            "--decisions-output",
            str(decisions_output),
        ],
    )

    payload = json.loads(decisions_output.read_text(encoding="utf-8"))

    assert result.exit_code == 0
    assert "Saved approved decision" in result.stdout
    assert payload["decisions"][0]["decision_key"] == "key-approved"


def test_validate_config_command_reports_valid_config(tmp_path):
    config_path = tmp_path / "rules.json"
    config_path.write_text(
        json.dumps(
            {
                "privacy_defaults": {"created_playlist_privacy": "private"},
                "keep_rules": {
                    "preferred_playlist_titles": ["favorites"],
                    "preferred_privacy_order": ["private", "public"],
                },
                "playlist_merge_preferences": {
                    "prefer_private_target": True,
                    "canonical_playlist_strategy": "largest_first",
                },
                "playlist_aliases": {},
                "token_aliases": {},
                "category_rules": [
                    {
                        "source_playlists": ["AI"],
                        "target_playlist": "ChatGPT",
                        "keyword_sets": [["chatgpt"]],
                        "reason": "ChatGPT content should move.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["validate-config", "--rules-config", str(config_path)])

    assert result.exit_code == 0
    assert "Config is valid" in result.stdout


def test_plan_summary_prints_counts_without_preview_table(tmp_path):
    plan_path = tmp_path / "playlist-plan.json"
    plan_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-25T00:00:00Z",
                "action_filter": ["category"],
                "summary": {
                    "actions": 1,
                    "duplicate_videos": 0,
                    "deleted_videos": 0,
                    "category_moves": 1,
                    "playlist_merges": 0,
                    "playlist_item_removals": 1,
                },
                "review": {
                    "category_move_candidates": [
                        {
                            "review_status": "approved",
                        },
                        {
                            "review_status": "undecided",
                        },
                    ],
                    "overlap_candidates": [
                        {
                            "review_status": "rejected",
                        }
                    ],
                    "liked_video_flags": [],
                },
                "actions": [
                    {
                        "action": "move_to_playlist",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["plan-summary", "--plan-path", str(plan_path)])

    assert result.exit_code == 0
    assert "Estimated quota cost:" in result.stdout
    assert "Review approved:" in result.stdout
    assert "data/playlist-report.html" in result.stdout
    assert "Video" not in result.stdout
