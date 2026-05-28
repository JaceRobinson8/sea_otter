"""Download file attachments with retry and deduplication."""

import logging
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

from .listing import HEADERS

log = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 3.0


def _safe_filename(url: str) -> str:
    """Derive a safe local filename from a URL."""
    name = Path(urlparse(url).path).name
    # Strip query params that sometimes appear in path-encoded form
    name = name.split("?")[0] or "attachment"
    return name


def download_file(client: httpx.Client, url: str, dest: Path, delay: float = 1.0) -> bool:
    """
    Download a file to dest. Returns True on success.
    Skips if dest already exists (dedup).
    """
    if dest.exists():
        return True

    dest.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with client.stream(
                "GET", url, headers=HEADERS, timeout=60, follow_redirects=True
            ) as resp:
                resp.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=65536):
                        f.write(chunk)
            time.sleep(delay)
            return True
        except httpx.HTTPError as exc:
            log.warning("Attempt %d/%d failed for %s: %s", attempt, MAX_RETRIES, url, exc)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)

    return False


def download_attachments(
    client: httpx.Client,
    attachment_urls: list[str],
    advisory_dir: Path,
    delay: float = 1.0,
) -> list[str]:
    """Download all attachment URLs into advisory_dir/attachments/. Returns list of saved filenames."""
    saved = []
    attachments_dir = advisory_dir / "attachments"
    attachments_dir.mkdir(parents=True, exist_ok=True)

    for url in attachment_urls:
        filename = _safe_filename(url)
        dest = attachments_dir / filename
        ok = download_file(client, url, dest, delay=delay)
        if ok:
            saved.append(filename)

    return saved
