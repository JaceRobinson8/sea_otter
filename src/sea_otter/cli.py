"""sea-otter CLI — CISA advisory dataset collector."""

import logging
import time
from datetime import date, datetime
from pathlib import Path
from typing import Annotated

import httpx
import typer
from tqdm import tqdm

from .collector.advisory import scrape_advisory
from .collector.downloader import download_attachments
from .collector.kev import fetch_kev, save_kev_snapshot
from .collector.listing import iter_cybersecurity_advisories, iter_ics_advisories
from .storage import db as db_mod
from .storage.filesystem import advisory_dir, write_html, write_metadata

DATA_ROOT = Path(__file__).parent.parent.parent / "data"
DB_PATH = DATA_ROOT / "sea_otter.db"

app = typer.Typer(
    help="sea-otter: collect CISA cybersecurity advisories.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


def _make_client() -> httpx.Client:
    return httpx.Client(http2=False)


def _collect_stubs(client, since: date | None, delay: float) -> list[dict]:
    """Collect all advisory stubs from both listing feeds."""
    stubs = []
    typer.echo("  Scanning cybersecurity advisories listing...")
    for stub in iter_cybersecurity_advisories(client, since=since, delay=delay):
        stubs.append(stub)
    typer.echo(f"    Found {len(stubs)} cybersecurity advisory stubs")

    ics_start = len(stubs)
    typer.echo("  Scanning ICS advisories listing...")
    for stub in iter_ics_advisories(client, since=since, delay=delay):
        stubs.append(stub)
    typer.echo(f"    Found {len(stubs) - ics_start} ICS advisory stubs")

    return stubs


@app.callback()
def _main(
    verbose: Annotated[bool, typer.Option("-v", "--verbose", help="Enable debug logging.")] = False,
):
    """sea-otter: collect CISA cybersecurity advisories."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )


@app.command()
def collect(
    since: Annotated[
        str | None,
        typer.Option(
            "--since",
            metavar="YYYY-MM-DD",
            help="Only collect advisories published on or after this date. Defaults to last collected date.",
        ),
    ] = None,
    collect_all: Annotated[
        bool, typer.Option("--all", help="Collect full history (ignores --since).")
    ] = False,
    delay: Annotated[
        float, typer.Option("--delay", help="Seconds to wait between requests.")
    ] = 1.5,
    no_attachments: Annotated[
        bool, typer.Option("--no-attachments", help="Skip downloading PDF/attachment files.")
    ] = False,
):
    """Collect CISA advisories. Resumes from where it left off (dedup via SQLite)."""
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    conn = db_mod.get_connection(DB_PATH)

    since_date: date | None = None
    if not collect_all:
        if since:
            since_date = datetime.strptime(since, "%Y-%m-%d").date()
        else:
            last = db_mod.get_latest_date(conn)
            if last:
                since_date = datetime.strptime(last, "%Y-%m-%d").date()
                typer.echo(f"Resuming from last collected date: {since_date}")

    with _make_client() as client:
        stubs = _collect_stubs(client, since=since_date, delay=delay)
        typer.echo(f"\nTotal stubs: {len(stubs)}. Scraping new advisories...")

        collected = 0
        skipped = 0

        for stub in tqdm(stubs, desc="Scraping", unit="advisory"):
            advisory_id = stub["id"]

            if db_mod.is_collected(conn, advisory_id):
                skipped += 1
                continue

            time.sleep(delay)
            detail = scrape_advisory(client, stub["url"])
            if detail is None:
                continue

            record = {**stub, **detail}
            if detail.get("published"):
                record["published"] = detail["published"]

            adir = advisory_dir(DATA_ROOT, advisory_id)
            write_html(DATA_ROOT, advisory_id, detail["raw_html"])
            write_metadata(
                DATA_ROOT,
                advisory_id,
                {k: v for k, v in record.items() if k not in ("body_html", "raw_html")},
            )

            if not no_attachments and detail["attachment_urls"]:
                saved = download_attachments(client, detail["attachment_urls"], adir, delay=delay)
                record["attachments"] = saved

            db_mod.insert_advisory(conn, record)
            collected += 1

    conn.close()
    typer.echo(f"\nDone. collected={collected}, skipped(already_have)={skipped}")


@app.command("collect-kev")
def collect_kev():
    """Fetch and snapshot the CISA Known Exploited Vulnerabilities catalog."""
    kev_dir = DATA_ROOT / "kev"
    with _make_client() as client:
        typer.echo("Fetching KEV catalog...")
        data = fetch_kev(client)
        save_kev_snapshot(data, kev_dir)
    typer.echo("Done.")


@app.command()
def status():
    """Show collection statistics."""
    if not DB_PATH.exists():
        typer.echo("No database found. Run `sea-otter collect` first.")
        return

    conn = db_mod.get_connection(DB_PATH)
    stats = db_mod.get_stats(conn)
    conn.close()

    typer.echo(f"Total advisories : {stats['total']}")
    typer.echo(f"Date range       : {stats['oldest']} → {stats['newest']}")
    typer.echo("By type:")
    for atype, cnt in stats["by_type"].items():
        typer.echo(f"  {atype:<40} {cnt}")


def main() -> None:
    app()
