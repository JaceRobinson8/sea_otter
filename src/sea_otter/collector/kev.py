"""Fetch and snapshot the CISA Known Exploited Vulnerabilities catalog."""

import json
import logging
from datetime import date
from pathlib import Path

import httpx

from .listing import HEADERS

log = logging.getLogger(__name__)

KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"


def fetch_kev(client: httpx.Client) -> dict:
    resp = client.get(KEV_URL, headers=HEADERS, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    return resp.json()


def save_kev_snapshot(data: dict, kev_dir: Path) -> None:
    kev_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    snapshot_path = kev_dir / f"{today}.json"
    latest_path = kev_dir / "known_exploited_vulnerabilities.json"

    payload = json.dumps(data, indent=2)
    snapshot_path.write_text(payload)
    latest_path.write_text(payload)

    count = data.get("count", len(data.get("vulnerabilities", [])))
    log.info("KEV catalog saved: %d entries → %s", count, snapshot_path.name)
