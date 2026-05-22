from __future__ import annotations

import html
import json
import mimetypes
import subprocess
import sys
import threading
import webbrowser
from collections import defaultdict
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
CONFIG_DIR = REPO_ROOT / "config"


def read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def read_json_if_exists(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def get_tracked_files() -> list[tuple[str, Path]]:
    return [
        ("Plan JSON", DATA_DIR / "playlist-plan.json"),
        ("Report Markdown", DATA_DIR / "playlist-report.md"),
        ("Review CSV", DATA_DIR / "playlist-review.csv"),
        ("Rules Config", CONFIG_DIR / "playlist-rules.json"),
    ]


def build_cli_command(form: dict[str, str]) -> list[str]:
    action = form.get("action", "")
    command = [sys.executable, "-m", "src.cli"]

    if action == "auth_readonly":
        return command + ["auth"]
    if action == "auth_write":
        return command + ["auth", "--write", "WRITE"]
    if action == "export":
        return command + ["export"]
    if action == "analyze":
        command += ["analyze"]
        rules_config = form.get("rules_config", "config/playlist-rules.json").strip()
        if rules_config:
            command += ["--rules-config", rules_config]
        if form.get("include_category_moves") == "on":
            command += ["--include-category-moves"]
        return command
    if action == "apply_preview":
        return command + ["apply"]
    if action == "apply_live":
        if form.get("confirm_text", "") != "APPLY":
            raise ValueError("Type APPLY exactly before running a live apply.")
        return command + ["apply", "--confirm", "APPLY"]

    raise ValueError(f"Unsupported action: {action}")


def run_command(command: list[str]) -> dict[str, str | int]:
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "command": " ".join(command),
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def format_timestamp(path: Path) -> str:
    if not path.exists():
        return "-"
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")


def get_review_groups(plan: dict) -> tuple[list[dict], list[dict]]:
    review = plan.get("review", {})
    category_moves = review.get("category_move_candidates", [])
    overlap_candidates = review.get("overlap_candidates", [])

    grouped_moves: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for move in category_moves:
        key = (
            move["from_playlist"]["playlist_title"],
            move["to_playlist"]["playlist_title"],
        )
        grouped_moves[key].append(move)

    move_groups = []
    for (source, target), items in sorted(grouped_moves.items()):
        sorted_items = sorted(items, key=lambda item: (-item.get("confidence_score", 0), item["title"].lower()))
        move_groups.append(
            {
                "source": source,
                "target": target,
                "count": len(sorted_items),
                "items": sorted_items,
            }
        )

    overlap_groups: dict[str, list[dict]] = defaultdict(list)
    for overlap in overlap_candidates:
        key = "Merge Candidates" if overlap.get("merge_candidate") else "Overlap Review"
        overlap_groups[key].append(overlap)

    grouped_overlaps = []
    for group_name, items in sorted(overlap_groups.items()):
        sorted_items = sorted(
            items,
            key=lambda item: (
                not item.get("merge_candidate", False),
                -item.get("shared_videos", 0),
                item["left_playlist"].lower(),
            ),
        )
        grouped_overlaps.append({"group": group_name, "count": len(sorted_items), "items": sorted_items})

    return move_groups, grouped_overlaps


def render_file_table() -> str:
    rows = []
    for label, path in get_tracked_files():
        exists = path.exists()
        open_link = html.escape(path.name)
        download_link = "-"
        if exists:
            safe_name = html.escape(path.name)
            open_link = f'<a href="/view?name={safe_name}">{safe_name}</a>'
            download_link = f'<a href="/download?name={safe_name}" download="{safe_name}">Download</a>'

        rows.append(
            "<tr>"
            f"<td>{html.escape(label)}</td>"
            f"<td>{'Yes' if exists else 'No'}</td>"
            f"<td>{html.escape(format_timestamp(path))}</td>"
            f"<td>{open_link}</td>"
            f"<td>{download_link}</td>"
            "</tr>"
        )

    return "".join(rows)


def render_move_groups(move_groups: list[dict]) -> str:
    if not move_groups:
        return "<p class='muted'>No suggested category moves are available yet. Run Analyze first.</p>"

    sections = []
    for group in move_groups:
        rows = []
        for item in group["items"]:
            reasons = "; ".join(item.get("confidence_reasons", []))
            rows.append(
                "<tr class='filter-row' "
                f"data-filter='{html.escape((group['source'] + ' ' + group['target'] + ' ' + item['title'] + ' ' + item.get('confidence_label', '') + ' ' + reasons).lower())}'>"
                f"<td>{html.escape(item['title'])}</td>"
                f"<td>{html.escape(item.get('confidence_label', ''))}</td>"
                f"<td>{html.escape(str(item.get('confidence_score', '')))}</td>"
                f"<td>{html.escape(item['rule'])}</td>"
                f"<td>{html.escape(reasons)}</td>"
                "</tr>"
            )

        sections.append(
            "<section class='card grouped-section'>"
            f"<h3>{html.escape(group['source'])} -> {html.escape(group['target'])} ({group['count']})</h3>"
            "<table>"
            "<thead><tr><th>Video</th><th>Confidence</th><th>Score</th><th>Rule</th><th>Details</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody>"
            "</table>"
            "</section>"
        )
    return "".join(sections)


def render_overlap_groups(overlap_groups: list[dict]) -> str:
    if not overlap_groups:
        return "<p class='muted'>No overlap review data is available yet. Run Analyze first.</p>"

    sections = []
    for group in overlap_groups:
        rows = []
        for item in group["items"]:
            details = f"shared={item['shared_videos']}, jaccard={item['jaccard']}, containment={item['containment']}"
            rows.append(
                "<tr class='filter-row' "
                f"data-filter='{html.escape((group['group'] + ' ' + item['left_playlist'] + ' ' + item['right_playlist'] + ' ' + item['review_reason']).lower())}'>"
                f"<td>{html.escape(item['left_playlist'])}</td>"
                f"<td>{html.escape(item['right_playlist'])}</td>"
                f"<td>{html.escape(details)}</td>"
                f"<td>{html.escape(item['review_reason'])}</td>"
                "</tr>"
            )

        sections.append(
            "<section class='card grouped-section'>"
            f"<h3>{html.escape(group['group'])} ({group['count']})</h3>"
            "<table>"
            "<thead><tr><th>Left Playlist</th><th>Right Playlist</th><th>Overlap</th><th>Reason</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody>"
            "</table>"
            "</section>"
        )
    return "".join(sections)


def render_summary_cards(plan: dict) -> str:
    summary = plan.get("summary", {})
    cards = [
        ("Planned Actions", summary.get("actions", 0)),
        ("Suggested Moves", len(plan.get("review", {}).get("category_move_candidates", []))),
        ("Overlap Reviews", len(plan.get("review", {}).get("overlap_candidates", []))),
        ("Playlist Merges", summary.get("playlist_merges", 0)),
    ]
    return "".join(
        (
            "<div class='metric'>"
            f"<span class='metric-label'>{html.escape(label)}</span>"
            f"<span class='metric-value'>{html.escape(str(value))}</span>"
            "</div>"
        )
        for label, value in cards
    )


def render_page(result: dict[str, str | int] | None = None, error: str = "") -> str:
    plan = read_json_if_exists(DATA_DIR / "playlist-plan.json")
    move_groups, overlap_groups = get_review_groups(plan)

    result_block = ""
    if result:
        stdout = html.escape(str(result.get("stdout", "")))
        stderr = html.escape(str(result.get("stderr", "")))
        result_block = (
            "<section><h2>Last Command Result</h2>"
            f"<p><strong>Command:</strong> <code>{html.escape(str(result.get('command', '')))}</code></p>"
            f"<p><strong>Exit Code:</strong> {html.escape(str(result.get('exit_code', '')))}</p>"
            f"<h3>Stdout</h3><pre>{stdout}</pre>"
            f"<h3>Stderr</h3><pre>{stderr}</pre>"
            "</section>"
        )

    error_block = f"<p style='color:#b00020;'><strong>{html.escape(error)}</strong></p>" if error else ""

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>YouTube Playlist Organizer UI</title>
  <style>
    :root {{
      --bg: #f4f1ea;
      --surface: #fffdf8;
      --ink: #1f1d1a;
      --muted: #6d655a;
      --accent: #126b5f;
      --accent-2: #d9efe6;
      --border: #d7d0c5;
      --danger: #9a2f20;
    }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background: linear-gradient(180deg, #efe8dc 0%, var(--bg) 100%);
      color: var(--ink);
    }}
    main {{
      max-width: 1250px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    h1, h2, h3 {{
      margin-top: 0;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px;
      margin: 16px 0 24px;
    }}
    .metric, .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 18px;
      box-shadow: 0 10px 30px rgba(35, 30, 20, 0.06);
    }}
    .metric-label {{
      display: block;
      color: var(--muted);
      font-size: 0.9rem;
      margin-bottom: 8px;
    }}
    .metric-value {{
      font-size: 1.8rem;
      font-weight: 700;
    }}
    button, .download-link {{
      background: var(--accent);
      color: white;
      border: 0;
      border-radius: 10px;
      padding: 10px 14px;
      cursor: pointer;
      font-weight: 700;
      text-decoration: none;
      display: inline-block;
    }}
    button.secondary {{
      background: #4a4f5a;
    }}
    button.danger {{
      background: var(--danger);
    }}
    input[type="text"] {{
      width: 100%;
      padding: 10px;
      border: 1px solid var(--border);
      border-radius: 10px;
      margin: 8px 0 12px;
      box-sizing: border-box;
    }}
    label {{
      display: block;
      margin: 10px 0;
      font-weight: 700;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--surface);
      border-radius: 16px;
      overflow: hidden;
    }}
    th, td {{
      text-align: left;
      padding: 12px;
      border-bottom: 1px solid var(--border);
      vertical-align: top;
    }}
    pre {{
      white-space: pre-wrap;
      word-break: break-word;
      background: #121212;
      color: #f6f3ee;
      padding: 14px;
      border-radius: 12px;
      overflow: auto;
    }}
    .muted {{ color: var(--muted); }}
    .toolbar {{
      display: flex;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
      margin-bottom: 16px;
    }}
    .toolbar input {{
      max-width: 420px;
      margin: 0;
    }}
    .grouped-section {{
      margin-bottom: 18px;
    }}
  </style>
</head>
<body>
  <main>
    <h1>YouTube Playlist Organizer UI</h1>
    <p class="muted">This is a local web wrapper for the existing CLI. It runs only on localhost and uses the same files and commands as the terminal workflow.</p>
    {error_block}

    <section class="metrics">
      {render_summary_cards(plan)}
    </section>

    <section class="grid">
      <form method="post" action="/run" class="card">
        <h2>Authentication</h2>
        <p class="muted">Read only is enough for export, analyze, and preview. Write access is only needed for a real apply.</p>
        <input type="hidden" name="action" value="auth_readonly">
        <button type="submit">Authenticate Read Only</button>
      </form>
      <form method="post" action="/run" class="card">
        <h2>Write Access</h2>
        <p class="muted">Only do this when you are ready to make live YouTube changes.</p>
        <input type="hidden" name="action" value="auth_write">
        <button type="submit" class="secondary">Authenticate Write Access</button>
      </form>
      <form method="post" action="/run" class="card">
        <h2>Export</h2>
        <p class="muted">Fetch all playlists and playlist items into the data folder.</p>
        <input type="hidden" name="action" value="export">
        <button type="submit">Run Export</button>
      </form>
    </section>

    <section class="grid">
      <form method="post" action="/run" class="card">
        <h2>Analyze</h2>
        <label for="rules_config">Rules Config Path</label>
        <input id="rules_config" type="text" name="rules_config" value="config/playlist-rules.json">
        <label><input type="checkbox" name="include_category_moves"> Include category moves in the apply plan</label>
        <input type="hidden" name="action" value="analyze">
        <button type="submit">Run Analyze</button>
      </form>
      <form method="post" action="/run" class="card">
        <h2>Preview Apply</h2>
        <p class="muted">This is a dry run. It prints the current plan summary and makes no live changes.</p>
        <input type="hidden" name="action" value="apply_preview">
        <button type="submit" class="secondary">Preview Apply</button>
      </form>
      <form method="post" action="/run" class="card">
        <h2>Live Apply</h2>
        <p class="muted">This will make live YouTube changes if the current plan is valid.</p>
        <label for="confirm_text">Type APPLY</label>
        <input id="confirm_text" type="text" name="confirm_text" value="">
        <input type="hidden" name="action" value="apply_live">
        <button type="submit" class="danger">Apply Live Changes</button>
      </form>
    </section>

    <section id="moves-section">
      <h2>Tracked Files</h2>
      <table>
        <thead>
          <tr><th>File</th><th>Exists</th><th>Modified</th><th>Open</th><th>Download</th></tr>
        </thead>
        <tbody>
          {render_file_table()}
        </tbody>
      </table>
    </section>

    <section id="overlap-section">
      <div class="toolbar">
        <h2 style="margin:0;">Suggested Reorganization</h2>
        <input id="moves-filter" type="text" placeholder="Filter by playlist, video title, or confidence">
        <a class="download-link" href="/download?name=playlist-review.csv" download="playlist-review.csv">Download Review CSV</a>
        <a class="download-link" href="/download?name=playlist-report.md" download="playlist-report.md">Download Report</a>
      </div>
      {render_move_groups(move_groups)}
    </section>

    <section>
      <div class="toolbar">
        <h2 style="margin:0;">Overlap Review</h2>
        <input id="overlap-filter" type="text" placeholder="Filter by playlist names or review reason">
        <a class="download-link" href="/download?name=playlist-plan.json" download="playlist-plan.json">Download Plan JSON</a>
      </div>
      {render_overlap_groups(overlap_groups)}
    </section>

    {result_block}
  </main>
  <script>
    function attachFilter(inputId, sectionSelector) {{
      const input = document.getElementById(inputId);
      if (!input) return;
      input.addEventListener('input', () => {{
        const term = input.value.trim().toLowerCase();
        document.querySelectorAll(sectionSelector + ' .filter-row').forEach((row) => {{
          const haystack = row.getAttribute('data-filter') || '';
          row.style.display = !term || haystack.includes(term) ? '' : 'none';
        }});
      }});
    }}
    attachFilter('moves-filter', '#moves-section');
    attachFilter('overlap-filter', '#overlap-section');
  </script>
</body>
</html>"""


class PlaylistUiHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html(render_page())
            return
        if parsed.path in {"/view", "/download"}:
            query = parse_qs(parsed.query)
            name = query.get("name", [""])[0]
            self._serve_file(name, as_download=parsed.path == "/download")
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        if self.path != "/run":
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(content_length).decode("utf-8", errors="replace")
        parsed_form = {key: values[0] for key, values in parse_qs(payload).items()}

        try:
            command = build_cli_command(parsed_form)
            result = run_command(command)
            self._send_html(render_page(result=result))
        except ValueError as exc:
            self._send_html(render_page(error=str(exc)), status=HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args) -> None:
        return

    def _send_html(self, content: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, name: str, as_download: bool = False) -> None:
        candidate_paths = [DATA_DIR / name, CONFIG_DIR / name]
        selected_path = None
        for path in candidate_paths:
            resolved = path.resolve()
            if resolved.exists() and (DATA_DIR.resolve() in resolved.parents or CONFIG_DIR.resolve() in resolved.parents):
                selected_path = resolved
                break

        if not selected_path:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        content_type, _ = mimetypes.guess_type(selected_path.name)
        if selected_path.suffix.lower() in {".md", ".json", ".csv", ".txt"}:
            body = read_text_if_exists(selected_path).encode("utf-8")
            content_type = "text/plain; charset=utf-8"
        else:
            body = selected_path.read_bytes()
            content_type = content_type or "application/octet-stream"

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        if as_download:
            self.send_header("Content-Disposition", f'attachment; filename="{selected_path.name}"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_ui_server(host: str = "127.0.0.1", port: int = 8765, open_browser_on_start: bool = True) -> None:
    server = ThreadingHTTPServer((host, port), PlaylistUiHandler)
    if open_browser_on_start:
        threading.Timer(0.8, lambda: webbrowser.open(f"http://{host}:{port}")).start()
    print(f"UI running at http://{host}:{port}")
    server.serve_forever()
