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
