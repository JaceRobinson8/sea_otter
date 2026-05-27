"""Fetch and snapshot the CISA Known Exploited Vulnerabilities catalog."""

import json
from datetime import date
from pathlib import Path

import httpx

from .listing import HEADERS

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
    print(f"  KEV catalog saved: {count} entries → {snapshot_path.name}")
