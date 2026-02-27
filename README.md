# jira-fetch

A Python CLI tool that exports Jira issues matching a JQL query to paginated JSON files. Designed for bulk data extraction — migrations, audits, reporting pipelines, or any workflow that needs raw Jira issue data outside of the Jira UI.

## How it works

Fetching runs in three phases:

1. **Count** — calls `POST /rest/api/3/search/approximate-count` to get the total number of matching issues upfront
2. **Collect IDs** — paginates through `POST /rest/api/3/search/jql` using cursor-based pagination (`nextPageToken`) to collect all matching issue IDs
3. **Fetch full detail** — calls `GET /rest/api/3/issue/{id}` for each issue individually to retrieve all fields

Output is written in batches to `output/` as JSON files named with a UTC timestamp and page index, e.g. `2026-02-27T17:07:17.730Z-1.json`. Each run produces its own timestamped set of files so successive runs never overwrite each other.

## Features

- **Resilient** — retries on `5xx` and network errors with exponential backoff; respects `429 Retry-After` headers; skips and logs individual issue failures without aborting the run
- **Rate-limit friendly** — configurable delay between requests
- **Progress display** — live progress line with issue count, percentage, and ETA shown as both a timespan and clock time
- **Debug mode** — `--debug` flag prints full request/response details for troubleshooting
- **Typed config** — all settings loaded from `.env` via `pydantic-settings` with validation at startup

## Project structure

```
jira-fetch/
├── pyproject.toml
├── .env                   # credentials (gitignored)
├── .env.example           # template
├── output/                # written at runtime (gitignored)
│   └── 2026-02-27T17:07:17.730Z-1.json
├── error.log              # failed requests (gitignored)
└── jira_fetch/
    ├── cli.py             # Click entry point
    ├── config.py          # pydantic-settings config
    ├── client.py          # HTTP client with retry/backoff
    ├── fetcher.py         # orchestration, pagination, progress
    └── writer.py          # buffered JSON file output
```

## Installation

Requires Python 3.10+. Python 3.13 via Homebrew recommended.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Configuration

```bash
cp .env.example .env
```

Edit `.env` with your Jira credentials:

```ini
# Required
JIRA_BASE_URL=https://your-org.atlassian.net
JIRA_USER_EMAIL=you@example.com
JIRA_API_TOKEN=your_api_token_here

# Optional
JIRA_MAX_RESULTS_PER_PAGE=100
OUTPUT_ISSUES_PER_FILE=250
OUTPUT_DIR=./output
RETRY_MAX_ATTEMPTS=3
RETRY_BACKOFF_BASE=2.0
RETRY_BACKOFF_MAX=60.0
REQUEST_DELAY_SECONDS=0.5
```

Generate an API token at: https://id.atlassian.com/manage-profile/security/api-tokens

## Usage

```bash
# Basic
jira-fetch --jql 'project = MYPROJ AND status = "In Progress"'

# Override output directory
jira-fetch --jql 'project = MYPROJ' --output-dir ./exports

# Debug mode (prints request/response details)
jira-fetch --jql 'project = MYPROJ' --debug

# Help
jira-fetch --help
```

### Example output

```
jira-fetch

Total issues to fetch: 1032
Progress: 256/1032 (24.8%)   ETA: 18 mins - 2:46 PM
...
Done. Wrote 1032 issues.
```

Output files contain arrays of full Jira issue objects as returned by the REST API:

```json
[
  {
    "id": "1494942",
    "key": "MYPROJ-123",
    "fields": {
      "summary": "...",
      "status": { ... },
      ...
    }
  },
  ...
]
```

## Error handling

| Scenario | Behaviour |
|---|---|
| Missing or invalid credentials | Clear message at startup, `exit 1` |
| `429` rate limited | Sleeps for `Retry-After` duration, then retries |
| `5xx` / network error | Exponential backoff up to `RETRY_MAX_ATTEMPTS` retries |
| Retries exhausted on an issue | Logged to `error.log`, issue skipped, run continues |
| Zero results | Prints message, exits cleanly |

Failed issues are appended to `error.log` with a timestamp and issue ID so they can be investigated or re-fetched after the run.

---

## Prompt

This project was generated using the following prompt with [Claude Code](https://claude.ai/claude-code):

> **Build a Python CLI tool called `jira-fetch`.**
>
> **Setup:**
> - `pyproject.toml` with `hatchling`, entry point `jira-fetch = "jira_fetch.cli:main"`
> - Dependencies: `requests>=2.32`, `pydantic-settings>=2.0`, `click>=8.0`, `rich>=13.0`
> - `.env` / `.env.example` for credentials, `.gitignore` excluding `.env`, `output/`, `error.log`
>
> **Config (`pydantic-settings`):**
> - Required: `JIRA_BASE_URL`, `JIRA_USER_EMAIL`, `JIRA_API_TOKEN`
> - Optional: `JIRA_MAX_RESULTS_PER_PAGE=100`, `OUTPUT_ISSUES_PER_FILE=250`, `OUTPUT_DIR=./output`, `RETRY_MAX_ATTEMPTS=3`, `RETRY_BACKOFF_BASE=2.0`, `RETRY_BACKOFF_MAX=60.0`, `REQUEST_DELAY_SECONDS=0.5`
> - Strip trailing slash from `JIRA_BASE_URL`
>
> **HTTP client:**
> - `requests.Session` with Basic Auth
> - Separate `get(path)` and `post(path, body)` methods
> - Retry logic: `429` → sleep `Retry-After` (default 60s) and retry; `5xx` / network error → exponential backoff up to `RETRY_MAX_ATTEMPTS`; `4xx` (non-429) → raise immediately, do not retry
> - `timeout=30` on all requests
> - Optional `debug` flag that prints method, URL, request body, status, and response body (first 2000 chars) for each request
>
> **Fetching flow:**
> 1. Call `POST /rest/api/3/search/approximate-count` with `{"jql": "..."}` to get the total issue count upfront
> 2. Paginate `POST /rest/api/3/search/jql` with `{"jql": "...", "maxResults": N, "nextPageToken": "..."}` to collect all issue IDs — this API returns `isLast: true` (not a `total`) to signal the final page; do not use `startAt`
> 3. For each issue ID, fetch full detail via `GET /rest/api/3/issue/{id}`
> 4. Sleep `REQUEST_DELAY_SECONDS` between requests
>
> **Output:**
> - Buffer issues and flush to disk in batches of `OUTPUT_ISSUES_PER_FILE`
> - Filename format: `{run_id}-{n}.json` where `run_id` is the UTC start time in ISO 8601 format e.g. `2026-02-27T17:07:17.730Z`
> - `json.dump` with `indent=2, ensure_ascii=False`
>
> **Progress display:**
> - Print total before fetching begins
> - Per-issue progress line: `Progress: 32/181 (17.7%)   ETA: 3h 24 mins - 4:38 PM`
> - ETA calculated from actual observed rate; clock time in local time
> - On completion: `Done. Wrote N issues.`
>
> **Error handling:**
> - Config failure → clear message + `sys.exit(1)`; `--help` must work without `.env`
> - Exhausted retries on an individual issue → log to `error.log` (append, with timestamp and issue ID), skip and continue
> - Zero results → print message, exit cleanly
>
> **CLI (`click`):**
> - `--jql` (required)
> - `--output-dir` (optional override)
> - `--debug` flag (enables HTTP debug logging)
