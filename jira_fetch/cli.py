import sys

import click
from rich.console import Console

console = Console()


@click.command()
@click.option("--jql", required=True, help="JQL query string to fetch issues")
@click.option("--output-dir", default=None, help="Override output directory")
@click.option("--debug", is_flag=True, default=False, help="Print request/response details")
@click.option("--include-worklogs", is_flag=True, default=False, help="Fetch and attach worklogs to each issue")
@click.option("--include-changelogs", is_flag=True, default=False, help="Fetch and attach changelogs to each issue")
def main(jql: str, output_dir: str | None, debug: bool, include_worklogs: bool, include_changelogs: bool) -> None:
    """Fetch Jira issues matching a JQL query and write paginated JSON output files."""
    from pydantic import ValidationError
    from pydantic_settings import BaseSettings

    from .config import Settings
    from .fetcher import fetch_issues

    try:
        settings = Settings()
    except ValidationError as e:
        console.print("[red]Configuration error:[/red] missing or invalid credentials.")
        for err in e.errors():
            field = ".".join(str(loc) for loc in err["loc"])
            console.print(f"  - {field}: {err['msg']}")
        console.print("\nCopy .env.example to .env and fill in your Jira credentials.")
        sys.exit(1)

    if output_dir is not None:
        settings.OUTPUT_DIR = output_dir
    if include_worklogs:
        settings.INCLUDE_WORKLOGS = True
    if include_changelogs:
        settings.INCLUDE_CHANGELOGS = True

    console.print("[bold]jira-fetch[/bold]\n")
    fetch_issues(jql, settings, debug=debug)
