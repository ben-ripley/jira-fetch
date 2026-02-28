import datetime
import time
from typing import Optional

from rich.console import Console

from .client import JiraClient
from .config import Settings
from .writer import OutputWriter

console = Console()


def fetch_issues(jql: str, settings: Settings, debug: bool = False) -> None:
    _now = datetime.datetime.now()
    run_id = _now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{_now.microsecond // 1000:03d}"
    client = JiraClient(settings, debug=debug)
    writer = OutputWriter(settings, run_id=run_id)

    try:
        count_data = client.post("/rest/api/3/search/approximate-count", {"jql": jql})
        total = count_data.get("count", 0)
    except RuntimeError as e:
        _log_error("approximate-count", str(e))
        total = None

    if total == 0:
        console.print("No issues found for the given JQL query.")
        return

    if total is not None:
        console.print(f"Total issues to fetch: {total}")

    issue_ids = _collect_issue_ids(jql, client, settings)
    if not issue_ids:
        console.print("No issues found for the given JQL query.")
        return

    total = len(issue_ids)
    fetched = 0
    total_comments = 0
    total_worklogs = 0
    total_changelogs = 0
    start_time = time.monotonic()

    for issue_id in issue_ids:
        try:
            issue = client.get(f"/rest/api/3/issue/{issue_id}")
        except RuntimeError as e:
            _log_error(issue_id, str(e))
            continue

        comments = _fetch_paginated(issue_id, "comment", "comments", client, settings)
        issue["comments"] = comments
        total_comments += len(comments)

        if settings.INCLUDE_WORKLOGS:
            worklogs = _fetch_paginated(issue_id, "worklog", "worklogs", client, settings)
            issue["worklogs"] = worklogs
            total_worklogs += len(worklogs)

        if settings.INCLUDE_CHANGELOGS:
            changelogs = _fetch_paginated(issue_id, "changelog", "values", client, settings)
            issue["changelogs"] = changelogs
            total_changelogs += len(changelogs)

        writer.add_issues([issue])
        fetched += 1
        pct = fetched / total * 100
        eta_str = _format_eta(fetched, total, start_time)
        print(f"Progress: {fetched}/{total} ({pct:.1f}%)   ETA: {eta_str}", end="\r", flush=True)

        time.sleep(settings.REQUEST_DELAY_SECONDS)

    writer.flush()
    print()

    summary = f"Done. Fetched: {fetched} issues, {total_comments} comments"
    if settings.INCLUDE_WORKLOGS:
        summary += f", {total_worklogs} worklogs"
    if settings.INCLUDE_CHANGELOGS:
        summary += f", {total_changelogs} changelogs"
    console.print(summary + ".")


def _collect_issue_ids(jql: str, client: JiraClient, settings: Settings) -> list[str]:
    page_size = settings.JIRA_MAX_RESULTS_PER_PAGE
    next_page_token = None
    ids = []

    while True:
        body: dict = {"jql": jql, "maxResults": page_size}
        if next_page_token:
            body["nextPageToken"] = next_page_token

        try:
            data = client.post("/rest/api/3/search/jql", body)
        except RuntimeError as e:
            _log_error("search", str(e))
            break

        issues = data.get("issues", [])
        ids.extend(issue["id"] for issue in issues)

        if data.get("isLast", False):
            break

        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break

        time.sleep(settings.REQUEST_DELAY_SECONDS)

    return ids


def _fetch_paginated(
    issue_id: str,
    path_suffix: str,
    response_key: str,
    client: JiraClient,
    settings: Settings,
) -> list:
    results = []
    start_at = 0
    page_size = settings.JIRA_MAX_RESULTS_PER_PAGE

    while True:
        try:
            data = client.get(
                f"/rest/api/3/issue/{issue_id}/{path_suffix}",
                params={"startAt": start_at, "maxResults": page_size},
            )
        except RuntimeError as e:
            _log_error(f"{issue_id}/{path_suffix}@{start_at}", str(e))
            break

        page = data.get(response_key, [])
        results.extend(page)
        start_at += len(page)

        if start_at >= data.get("total", 0) or not page:
            break

        time.sleep(settings.REQUEST_DELAY_SECONDS)

    return results


def _format_eta(fetched: int, total: int, start_time: float) -> str:
    elapsed = time.monotonic() - start_time
    if fetched == 0 or elapsed == 0:
        return "calculating..."
    rate = fetched / elapsed  # issues per second
    remaining_seconds = (total - fetched) / rate
    eta_clock = datetime.datetime.now() + datetime.timedelta(seconds=remaining_seconds)

    hours, remainder = divmod(int(remaining_seconds), 3600)
    minutes = remainder // 60
    if hours > 0:
        timespan = f"{hours}h {minutes} mins"
    elif minutes > 0:
        timespan = f"{minutes} mins"
    else:
        timespan = f"{int(remaining_seconds)}s"

    clock = eta_clock.strftime("%-I:%M %p")
    return f"{timespan} - {clock}"


def _log_error(context: str, message: str) -> None:
    timestamp = datetime.datetime.now().isoformat()
    with open("error.log", "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] context={context} error={message}\n")
