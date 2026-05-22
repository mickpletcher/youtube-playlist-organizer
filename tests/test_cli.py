import json

from typer.testing import CliRunner

from src.cli import app


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
