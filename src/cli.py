import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
import sys

load_dotenv()

app = typer.Typer(no_args_is_help=True)
console = Console()


def safe_text(value: str) -> str:
    encoding = sys.stdout.encoding or "utf-8"
    return value.encode(encoding, errors="replace").decode(encoding)


def estimate_quota_cost(actions: list[dict]) -> int:
    cost = 0
    for action in actions:
        cost += estimate_action_quota_cost(action)
    return cost


def estimate_action_quota_cost(action: dict) -> int:
    action_name = action["action"]
    if action_name == "remove_duplicate":
        return len(action.get("remove_from", [])) * 50
    if action_name == "remove_deleted":
        return 50
    if action_name == "create_playlist":
        return 50
    if action_name == "move_to_playlist":
        return 100
    if action_name == "merge_playlist":
        return (len(action.get("move_items", [])) * 100) + (len(action.get("remove_items", [])) * 50) + 50
    return 0


def limit_actions_by_quota(actions: list[dict], max_quota_cost: int) -> tuple[list[dict], int]:
    if max_quota_cost <= 0:
        return actions, estimate_quota_cost(actions)

    selected = []
    selected_cost = 0
    for action in actions:
        action_cost = estimate_action_quota_cost(action)
        if selected and selected_cost + action_cost > max_quota_cost:
            break
        if not selected and action_cost > max_quota_cost:
            break
        selected.append(action)
        selected_cost += action_cost
    return selected, selected_cost


@app.command()
def auth(
    client_secret: str = typer.Option(
        "client_secret.json", envvar="CLIENT_SECRET_FILE", help="Path to client_secret.json"
    ),
    token_file: str = typer.Option(
        "token.json", envvar="TOKEN_FILE", help="Path to store token.json"
    ),
    write: str = typer.Option("", "--write", help="Type WRITE to request write scope"),
):
    """Authenticate with YouTube via OAuth2."""
    from src.auth.oauth import get_credentials

    readonly = write != "WRITE"
    try:
        get_credentials(client_secret, token_file, readonly)
        scope_label = "read-only" if readonly else "read-write"
        console.print(f"[green]Authenticated ({scope_label})[/green]")
        console.print(f"Token saved to [bold]{token_file}[/bold]")
    except FileNotFoundError:
        console.print(f"[red]Not found: {client_secret}[/red]")
        console.print(
            "Download OAuth credentials from Google Cloud Console and save as client_secret.json"
        )
        raise typer.Exit(1)


@app.command()
def list(
    client_secret: str = typer.Option(
        "client_secret.json", envvar="CLIENT_SECRET_FILE", help="Path to client_secret.json"
    ),
    token_file: str = typer.Option(
        "token.json", envvar="TOKEN_FILE", help="Path to token.json"
    ),
):
    """List all your YouTube playlists."""
    from src.auth.oauth import get_youtube_client
    from src.api.youtube import get_playlists

    client = get_youtube_client(client_secret, token_file, readonly=True)
    playlists = get_playlists(client)

    if not playlists:
        console.print("[yellow]No playlists found.[/yellow]")
        return

    console.print(f"\n[bold]Found {len(playlists)} playlist(s):[/bold]\n")
    for pl in playlists:
        console.print(f"  [cyan]{pl.title}[/cyan]  ({pl.item_count} videos)  [dim]{pl.privacy}[/dim]")
        if pl.description:
            console.print(f"    {pl.description[:80]}")
    console.print()


@app.command()
def export(
    client_secret: str = typer.Option(
        "client_secret.json", envvar="CLIENT_SECRET_FILE", help="Path to client_secret.json"
    ),
    token_file: str = typer.Option(
        "token.json", envvar="TOKEN_FILE", help="Path to token.json"
    ),
    output_dir: str = typer.Option("data", help="Directory to write output files"),
):
    """Export all playlists and their videos to JSON and CSV."""
    from src.auth.oauth import get_youtube_client
    from src.api.youtube import get_liked_playlist, get_playlists, get_playlist_items
    from src.export.exporter import export_json, export_csv

    client = get_youtube_client(client_secret, token_file, readonly=True)

    console.print("\n[bold]Fetching playlists...[/bold]")
    playlists = get_playlists(client)
    liked_playlist = get_liked_playlist(client)
    if liked_playlist and all(playlist.id != liked_playlist.id for playlist in playlists):
        playlists.append(liked_playlist)
    console.print(f"Found {len(playlists)} playlist(s). Fetching videos...")

    items_by_playlist: dict = {}
    for i, pl in enumerate(playlists, 1):
        console.print(f"  [{i}/{len(playlists)}] {pl.title}", end="\r")
        items_by_playlist[pl.id] = get_playlist_items(client, pl.id)

    json_path = f"{output_dir}/playlists.json"
    playlists_csv = f"{output_dir}/playlists.csv"
    items_csv = f"{output_dir}/playlist_items.csv"

    export_json(playlists, items_by_playlist, json_path)
    export_csv(playlists, items_by_playlist, playlists_csv, items_csv)

    total_videos = sum(len(v) for v in items_by_playlist.values())
    console.print(f"\n[green]Exported {len(playlists)} playlists, {total_videos} videos[/green]")
    console.print(f"  {json_path}")
    console.print(f"  {playlists_csv}")
    console.print(f"  {items_csv}\n")


@app.command()
def analyze(
    input_json: str = typer.Option("data/playlists.json", help="Path to exported playlists JSON"),
    plan_output: str = typer.Option("data/playlist-plan.json", help="Path to write plan JSON"),
    report_output: str = typer.Option("data/playlist-report.md", help="Path to write review report"),
    review_csv_output: str = typer.Option("data/playlist-review.csv", help="Path to write review CSV"),
    decisions_file: str = typer.Option(
        "data/review-decisions.json",
        help="Path to saved review decisions from earlier analysis runs",
    ),
    rules_config: str = typer.Option(
        "config/playlist-rules.json",
        help="Path to category and playlist normalization rules in JSON or YAML format",
    ),
    include_category_moves: bool = typer.Option(
        False,
        "--include-category-moves",
        help="Add rule based reorganization moves to the apply plan",
    ),
    only_duplicates: bool = typer.Option(False, "--only-duplicates", help="Only plan duplicate cleanup actions"),
    only_deleted: bool = typer.Option(False, "--only-deleted", help="Only plan deleted video cleanup actions"),
    only_merges: bool = typer.Option(False, "--only-merges", help="Only plan duplicate playlist merge actions"),
    only_category_suggestions: bool = typer.Option(
        False,
        "--only-category-suggestions",
        help="Only generate category move suggestions and approved category move actions",
    ),
    move_review_output: str = typer.Option(
        "data/playlist-move-review.md",
        help="Path to write grouped category move review markdown",
    ),
    html_report_output: str = typer.Option(
        "data/playlist-report.html",
        help="Path to write optional HTML review report",
    ),
):
    """Scan playlists for duplicates and write a plan."""
    from src.analysis.duplicates import find_duplicates, load_export
    from src.analysis.planner import (
        build_action_filter,
        generate_plan,
        write_html_report,
        write_move_review,
        write_plan,
        write_report,
        write_review_csv,
    )

    try:
        playlists_data = load_export(input_json)
    except FileNotFoundError:
        console.print(f"[red]Not found: {input_json}[/red]")
        console.print("Run export first.")
        raise typer.Exit(1)

    duplicates = find_duplicates(playlists_data)
    try:
        plan = generate_plan(
            duplicates,
            playlists_data,
            include_category_moves=include_category_moves,
            rules_config_path=rules_config,
            decisions_path=decisions_file,
            action_filter=build_action_filter(
                only_duplicates=only_duplicates,
                only_deleted=only_deleted,
                only_merges=only_merges,
                only_category_suggestions=only_category_suggestions,
            ),
        )
    except FileNotFoundError:
        console.print(f"[red]Not found: {rules_config}[/red]")
        console.print("Create the rules config file or point analyze at a valid JSON or YAML config.")
        raise typer.Exit(1)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    write_plan(plan, plan_output)
    write_report(plan, report_output)
    write_review_csv(plan, review_csv_output)
    write_move_review(plan, move_review_output)
    write_html_report(plan, html_report_output)

    summary = plan["summary"]
    action_filter = set(plan.get("action_filter", []))
    console.print(f"\n[bold]Duplicate videos:[/bold] {summary.get('duplicate_videos', 0)}")
    console.print(f"[bold]Deleted videos:[/bold] {summary.get('deleted_videos', 0)}")
    console.print(f"[bold]Category moves:[/bold] {summary.get('category_moves', 0)}")
    console.print(
        f"[bold]Suggested category moves for review:[/bold] "
        f"{len(plan.get('review', {}).get('category_move_candidates', []))}"
    )
    console.print(f"[bold]Playlist merges:[/bold] {summary.get('playlist_merges', 0)}")
    console.print(f"[bold]Playlist item moves:[/bold] {summary.get('playlist_item_moves', 0)}")
    console.print(f"[bold]Planned removals:[/bold] {summary.get('playlist_item_removals', 0)}")
    console.print(f"[bold]Playlist creations:[/bold] {summary.get('playlist_creations', 0)}")

    if "duplicates" in action_filter and duplicates:
        table = Table(show_header=True, header_style="bold")
        table.add_column("Video", overflow="fold")
        table.add_column("Playlists", overflow="fold")

        for duplicate in duplicates[:20]:
            table.add_row(
                duplicate["title"] or duplicate["video_id"],
                ", ".join(duplicate["playlists"]),
            )

        console.print()
        console.print(table)
        if len(duplicates) > 20:
            console.print(f"\nShowing 20 of {len(duplicates)} duplicate videos.")

    console.print(f"\n[green]Plan written to[/green] {plan_output}")
    console.print(f"[green]Review report written to[/green] {report_output}")
    console.print(f"[green]Review CSV written to[/green] {review_csv_output}")
    console.print(f"[green]Move review written to[/green] {move_review_output}")
    console.print(f"[green]HTML report written to[/green] {html_report_output}\n")


@app.command()
def plan_summary(
    plan_path: str = typer.Option("data/playlist-plan.json", help="Path to plan JSON"),
):
    """Print a compact plan summary without preview tables."""
    import json
    from pathlib import Path

    plan_file = Path(plan_path)
    if not plan_file.exists():
        console.print(f"[red]Not found: {plan_path}[/red]")
        console.print("Run analyze first.")
        raise typer.Exit(1)

    plan = json.loads(plan_file.read_text(encoding="utf-8"))
    actions = plan.get("actions", [])
    summary = plan.get("summary", {})
    review = plan.get("review", {})
    review_items = (
        review.get("category_move_candidates", [])
        + review.get("overlap_candidates", [])
        + review.get("liked_video_flags", [])
    )
    status_counts = {"approved": 0, "rejected": 0, "undecided": 0}
    for item in review_items:
        status = item.get("review_status", "undecided")
        if status not in status_counts:
            status = "undecided"
        status_counts[status] += 1

    console.print(f"\n[bold]Plan:[/bold] {plan_path}")
    console.print(f"[bold]Generated:[/bold] {plan.get('generated_at', '')}")
    console.print(f"[bold]Action filter:[/bold] {', '.join(plan.get('action_filter', []))}")
    console.print(f"[bold]Estimated quota cost:[/bold] {estimate_quota_cost(actions)} units")
    console.print(f"[bold]Planned actions:[/bold] {summary.get('actions', 0)}")
    console.print(f"[bold]Duplicate videos:[/bold] {summary.get('duplicate_videos', 0)}")
    console.print(f"[bold]Deleted videos:[/bold] {summary.get('deleted_videos', 0)}")
    console.print(f"[bold]Category moves:[/bold] {summary.get('category_moves', 0)}")
    console.print(f"[bold]Playlist merges:[/bold] {summary.get('playlist_merges', 0)}")
    console.print(f"[bold]Playlist item removals:[/bold] {summary.get('playlist_item_removals', 0)}")
    console.print(f"[bold]Review approved:[/bold] {status_counts['approved']}")
    console.print(f"[bold]Review rejected:[/bold] {status_counts['rejected']}")
    console.print(f"[bold]Review undecided:[/bold] {status_counts['undecided']}")
    console.print("\n[bold]Output files:[/bold]")
    console.print("  data/playlist-plan.json")
    console.print("  data/playlist-report.md")
    console.print("  data/playlist-report.html")
    console.print("  data/playlist-review.csv")
    console.print("  data/playlist-move-review.md\n")


@app.command()
def validate_config(
    rules_config: str = typer.Option(
        "config/playlist-rules.json",
        help="Path to category and playlist normalization rules in JSON or YAML format",
    ),
):
    """Validate the rules config before running analyze."""
    from src.analysis.rules import load_rules_config, validate_rules_config

    try:
        config = load_rules_config(rules_config)
    except FileNotFoundError:
        console.print(f"[red]Not found: {rules_config}[/red]")
        raise typer.Exit(1)
    except (RuntimeError, ValueError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    errors = validate_rules_config(config)
    if errors:
        console.print(f"[red]Config validation failed: {rules_config}[/red]")
        for error in errors:
            console.print(f"- {error}")
        raise typer.Exit(1)

    console.print(f"[green]Config is valid:[/green] {rules_config}")


@app.command()
def save_decisions(
    review_csv: str = typer.Option("data/playlist-review.csv", help="Path to edited review CSV"),
    decisions_output: str = typer.Option(
        "data/review-decisions.json",
        help="Path to write saved approved and rejected decisions",
    ),
):
    """Save approved or rejected review CSV rows for future analyze runs."""
    from src.analysis.decisions import save_decisions_from_review_csv

    try:
        count = save_decisions_from_review_csv(review_csv, decisions_output)
    except FileNotFoundError:
        console.print(f"[red]Not found: {review_csv}[/red]")
        console.print("Run analyze first, then mark review_status values in the review CSV.")
        raise typer.Exit(1)

    console.print(f"[green]Saved {count} review decision(s) to {decisions_output}[/green]")
    console.print("Future analyze runs will use those decisions by default.\n")


@app.command()
def decide(
    decision_key: str = typer.Option(..., "--decision-key", help="Decision key from data/playlist-review.csv"),
    review_status: str = typer.Option(..., "--review-status", help="approved or rejected"),
    review_csv: str = typer.Option("data/playlist-review.csv", help="Path to review CSV"),
    decisions_output: str = typer.Option(
        "data/review-decisions.json",
        help="Path to write saved approved and rejected decisions",
    ),
):
    """Approve or reject one review row by decision key."""
    from src.analysis.decisions import save_decision_by_key

    try:
        decision = save_decision_by_key(decision_key, review_status, review_csv, decisions_output)
    except FileNotFoundError:
        console.print(f"[red]Not found: {review_csv}[/red]")
        raise typer.Exit(1)
    except KeyError:
        console.print(f"[red]Decision key not found in review CSV: {decision_key}[/red]")
        raise typer.Exit(1)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    console.print(
        f"[green]Saved {decision['review_status']} decision for[/green] "
        f"{decision.get('title', decision_key)}"
    )


@app.command()
def apply(
    client_secret: str = typer.Option(
        "client_secret.json", envvar="CLIENT_SECRET_FILE", help="Path to client_secret.json"
    ),
    token_file: str = typer.Option(
        "token.json", envvar="TOKEN_FILE", help="Path to token.json"
    ),
    plan_path: str = typer.Option("data/playlist-plan.json", help="Path to plan JSON"),
    confirm: str = typer.Option("", "--confirm", help="Type APPLY to apply changes"),
    max_quota_cost: int = typer.Option(
        0,
        "--max-quota-cost",
        min=0,
        help="Apply only the first actions that fit this quota cost. Use 0 for the full plan.",
    ),
    snapshot_dir: str = typer.Option("data/snapshots", help="Directory for automatic rollback snapshots"),
    skip_rollback_snapshot: bool = typer.Option(
        False,
        "--skip-rollback-snapshot",
        help="Do not copy current local data files before a confirmed live apply",
    ),
):
    """Apply the generated plan to YouTube."""
    import json
    from pathlib import Path

    from src.api.youtube import (
        add_video_to_playlist,
        create_playlist,
        delete_playlist,
        delete_playlist_item,
        YouTubeQuotaExceeded,
    )
    from src.auth.oauth import get_youtube_client

    plan_file = Path(plan_path)
    if not plan_file.exists():
        console.print(f"[red]Not found: {plan_path}[/red]")
        console.print("Run analyze first.")
        raise typer.Exit(1)

    plan = json.loads(plan_file.read_text(encoding="utf-8"))
    actions = plan.get("actions", [])
    summary = plan.get("summary", {})
    deleted_videos = summary.get("deleted_videos", 0)
    category_moves = summary.get("category_moves", 0)
    playlist_creations = summary.get("playlist_creations", 0)
    playlist_merges = summary.get("playlist_merges", 0)
    playlist_item_moves = summary.get("playlist_item_moves", 0)
    removals = summary.get("playlist_item_removals", 0)

    selected_actions, selected_quota_cost = limit_actions_by_quota(actions, max_quota_cost)

    console.print(f"\n[bold]Plan actions:[/bold] {len(actions)}")
    console.print(f"[bold]Deleted videos:[/bold] {deleted_videos}")
    console.print(f"[bold]Playlist merges:[/bold] {playlist_merges}")
    console.print(f"[bold]Playlist item moves:[/bold] {playlist_item_moves}")
    console.print(f"[bold]Playlist item removals:[/bold] {removals}")
    console.print(f"[bold]Category moves:[/bold] {category_moves}")
    console.print(f"[bold]Playlist creations:[/bold] {playlist_creations}")
    console.print(f"[bold]Estimated quota cost:[/bold] {estimate_quota_cost(actions)} units")
    if max_quota_cost > 0:
        console.print(
            f"[bold]Selected chunk:[/bold] {len(selected_actions)} action(s), "
            f"{selected_quota_cost} estimated quota units"
        )
        skipped = len(actions) - len(selected_actions)
        if skipped:
            console.print(f"[yellow]Skipping {skipped} later action(s) in this run.[/yellow]")
    console.print()

    preview_table = Table(show_header=True, header_style="bold")
    preview_table.add_column("Video", overflow="fold")
    preview_table.add_column("Keep In", overflow="fold")
    preview_table.add_column("Remove From", overflow="fold")

    for action in selected_actions[:20]:
        if action["action"] == "remove_duplicate":
            preview_table.add_row(
                action["title"] or action["video_id"],
                action["keep_in"]["playlist_title"],
                ", ".join(item["playlist_title"] for item in action["remove_from"]),
            )
        elif action["action"] == "remove_deleted":
            preview_table.add_row(
                action["title"] or action["video_id"],
                "remove from playlist",
                action["from_playlist"]["playlist_title"],
            )
        elif action["action"] == "move_to_playlist":
            preview_table.add_row(
                action["title"] or action["video_id"],
                action["to_playlist"]["playlist_title"],
                action["from_playlist"]["playlist_title"],
            )
        elif action["action"] == "create_playlist":
            preview_table.add_row(
                action["title"],
                action["title"],
                "create playlist",
            )
        elif action["action"] == "merge_playlist":
            preview_table.add_row(
                action["source_playlist"]["playlist_title"],
                action["target_playlist"]["playlist_title"],
                (
                    f"merge playlist, move {len(action['move_items'])}, "
                    f"remove {len(action['remove_items'])}"
                ),
            )

    if actions:
        console.print(preview_table)
        if len(selected_actions) > 20:
            console.print(f"\nShowing 20 of {len(selected_actions)} selected actions.")
    if max_quota_cost > 0 and not selected_actions:
        console.print("\n[red]No actions fit the requested quota budget.[/red]")
        raise typer.Exit(1)

    if confirm != "APPLY":
        console.print("\n[yellow]Dry run only. Re run with --confirm to apply changes.[/yellow]\n")
        raise typer.Exit()

    if not skip_rollback_snapshot:
        from src.analysis.planner import create_rollback_snapshot

        snapshot_path = create_rollback_snapshot(snapshot_dir)
        console.print(f"[green]Rollback snapshot written to[/green] {snapshot_path}")

    client = get_youtube_client(client_secret, token_file, readonly=False)
    created_playlists: dict[str, str] = {}

    completed = 0
    try:
        for action in selected_actions:
            if action["action"] == "create_playlist":
                playlist_id = create_playlist(
                    client,
                    title=action["title"],
                    privacy=action.get("privacy", "private"),
                )
                created_playlists[action["title"]] = playlist_id
                console.print(f"Created [bold]{action['title']}[/bold]")
                continue

            if action["action"] == "remove_duplicate":
                for item in action.get("remove_from", []):
                    deleted = delete_playlist_item(client, item["playlist_item_id"])
                    if not deleted:
                        console.print(
                            f"Skipped missing item for [cyan]{safe_text(action['title'] or action['video_id'])}[/cyan] in "
                            f"[bold]{item['playlist_title']}[/bold]"
                        )
                        continue

                    completed += 1
                    console.print(
                        f"Removed [cyan]{safe_text(action['title'] or action['video_id'])}[/cyan] from "
                        f"[bold]{item['playlist_title']}[/bold]"
                    )
                continue

            if action["action"] == "remove_deleted":
                deleted = delete_playlist_item(client, action["from_playlist"]["playlist_item_id"])
                if not deleted:
                    console.print(
                        f"Skipped missing deleted entry in [bold]{action['from_playlist']['playlist_title']}[/bold]"
                    )
                    continue

                completed += 1
                console.print(
                    f"Removed deleted entry from [bold]{action['from_playlist']['playlist_title']}[/bold]"
                )
                continue

            if action["action"] == "move_to_playlist":
                target_playlist_id = action["to_playlist"].get("playlist_id") or created_playlists.get(
                    action["to_playlist"]["playlist_title"]
                )
                if not target_playlist_id:
                    console.print(
                        f"[red]Missing target playlist for {safe_text(action['title'])}: "
                        f"{action['to_playlist']['playlist_title']}[/red]"
                    )
                    raise typer.Exit(1)

                add_video_to_playlist(client, target_playlist_id, action["video_id"])
                deleted = delete_playlist_item(client, action["from_playlist"]["playlist_item_id"])
                completed += 1
                console.print(
                    f"Moved [cyan]{safe_text(action['title'])}[/cyan] from "
                    f"[bold]{action['from_playlist']['playlist_title']}[/bold] to "
                    f"[bold]{action['to_playlist']['playlist_title']}[/bold]"
                )
                if not deleted:
                    console.print(
                        f"Skipped source removal because the item was already missing from "
                        f"[bold]{action['from_playlist']['playlist_title']}[/bold]"
                    )
                continue

            if action["action"] == "merge_playlist":
                target_playlist_id = action["target_playlist"]["playlist_id"]
                source_playlist = action["source_playlist"]

                for item in action.get("move_items", []):
                    add_video_to_playlist(client, target_playlist_id, item["video_id"])
                    deleted = delete_playlist_item(client, item["playlist_item_id"])
                    completed += 1
                    console.print(
                        f"Moved [cyan]{safe_text(item['title'] or item['video_id'])}[/cyan] from "
                        f"[bold]{source_playlist['playlist_title']}[/bold] to "
                        f"[bold]{action['target_playlist']['playlist_title']}[/bold]"
                    )
                    if not deleted:
                        console.print(
                            f"Skipped source removal because the item was already missing from "
                            f"[bold]{source_playlist['playlist_title']}[/bold]"
                        )

                for item in action.get("remove_items", []):
                    deleted = delete_playlist_item(client, item["playlist_item_id"])
                    if not deleted:
                        console.print(
                            f"Skipped duplicate cleanup because the item was already missing from "
                            f"[bold]{source_playlist['playlist_title']}[/bold]"
                        )
                        continue

                    completed += 1
                    console.print(
                        f"Removed duplicate [cyan]{safe_text(item['title'] or item['video_id'])}[/cyan] from "
                        f"[bold]{source_playlist['playlist_title']}[/bold]"
                    )

                delete_playlist(client, source_playlist["playlist_id"])
                console.print(f"Deleted merged playlist [bold]{source_playlist['playlist_title']}[/bold]")
    except YouTubeQuotaExceeded as exc:
        console.print(f"\n[red]{exc}[/red]")
        console.print(f"[yellow]Applied {completed} change(s) before quota stopped the run.[/yellow]")
        console.print("Do not rerun the same plan. After quota resets, run export, analyze, review, then apply a small chunk.")
        raise typer.Exit(1) from exc

    console.print(f"\n[green]Applied {completed} change(s).[/green]\n")


@app.command()
def ui(
    host: str = typer.Option("127.0.0.1", help="Host for the local web UI"),
    port: int = typer.Option(8765, help="Port for the local web UI"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Do not open the browser automatically"),
):
    """Start the local web UI for non terminal users."""
    from src.webui.server import run_ui_server

    console.print(f"[green]Starting UI at http://{host}:{port}[/green]")
    run_ui_server(host=host, port=port, open_browser_on_start=not no_browser)


if __name__ == "__main__":
    app()
