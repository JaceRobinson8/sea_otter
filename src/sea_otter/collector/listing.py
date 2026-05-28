"""Scrape CISA advisory listing pages and yield advisory stubs."""

import logging
import re
import time
from collections.abc import Iterator
from datetime import date, datetime

import httpx
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
}

BASE_URL = "https://www.cisa.gov"

# Two distinct listing endpoints — non-ICS and ICS
LISTING_URLS = {
    "cybersecurity": f"{BASE_URL}/news-events/cybersecurity-advisories",
    "ics": f"{BASE_URL}/news-events/ics-advisories",
}

# URL patterns for each listing type
# Non-ICS: /news-events/{type}/{year}/{month}/{day}/{slug}
_NON_ICS_RE = re.compile(r"/news-events/[^/]+/\d{4}/\d{2}/\d{2}/[^/]+")
# ICS: /news-events/ics-advisories/icsa-... or /news-events/ics-medical-advisories/icsma-...
_ICS_RE = re.compile(r"/news-events/ics(?:-medical)?-advisories/ics(?:a|ma)-\d{2}-\d{3}-\d{2}")

_DATE_RE = re.compile(r"[A-Z][a-z]+ \d{1,2}, \d{4}|\d{4}-\d{2}-\d{2}")


def _parse_date(text: str) -> str | None:
    text = text.strip()
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return text or None


def _advisory_id(url: str) -> str:
    return url.replace(BASE_URL, "").lstrip("/")


def _type_from_url(path: str) -> str:
    if "ics-medical" in path:
        return "ics-medical-advisory"
    if path.startswith("/news-events/ics-advisories/icsma"):
        return "ics-medical-advisory"
    if "/news-events/ics-advisories/" in path:
        return "ics-advisory"
    if "/news-events/alerts/" in path:
        return "alert"
    if "/news-events/cybersecurity-advisories/" in path:
        return "cybersecurity-advisory"
    # Derive from the path segment
    parts = path.strip("/").split("/")
    return parts[1] if len(parts) > 1 else "unknown"


def _find_date_near(tag) -> str | None:
    """Walk up the DOM to find the nearest <time datetime="..."> element."""
    container = tag.find_parent(["li", "article", "div"])
    if not container:
        return None
    time_el = container.find("time", datetime=True)
    if time_el:
        # datetime attr is ISO 8601, e.g. "2026-05-27T12:00:00Z"
        raw = time_el["datetime"][:10]  # take YYYY-MM-DD
        return raw
    # Fallback: scan for a text date match
    for el in container.find_all(["span", "div", "p"]):
        text = el.get_text(strip=True)
        m = _DATE_RE.search(text)
        if m:
            return _parse_date(m.group(0))
    return None


def _parse_non_ics_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    seen = set()
    for a in soup.find_all("a", href=_NON_ICS_RE):
        href = a["href"]
        url = href if href.startswith("http") else BASE_URL + href
        if url in seen:
            continue
        seen.add(url)
        results.append(
            {
                "id": _advisory_id(url),
                "url": url,
                "title": a.get_text(strip=True),
                "published": _find_date_near(a),
                "advisory_type": _type_from_url(href),
            }
        )
    return results


def _parse_ics_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    seen = set()
    for a in soup.find_all("a", href=_ICS_RE):
        href = a["href"]
        url = href if href.startswith("http") else BASE_URL + href
        if url in seen:
            continue
        seen.add(url)
        results.append(
            {
                "id": _advisory_id(url),
                "url": url,
                "title": a.get_text(strip=True),
                "published": _find_date_near(a),
                "advisory_type": _type_from_url(href),
            }
        )
    return results


def _iter_listing_pages(
    client: httpx.Client,
    base_url: str,
    parse_fn,
    since: date | None,
    delay: float,
) -> Iterator[dict]:
    page = 0
    while True:
        url = base_url if page == 0 else f"{base_url}?page={page}"
        try:
            resp = client.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            log.warning("HTTP error on %s: %s", url, exc)
            break

        items = parse_fn(resp.text)
        if not items:
            break

        stop = False
        for item in items:
            if since and item["published"] and item["published"] < since.isoformat():
                stop = True
                break
            yield item

        if stop:
            break

        page += 1
        time.sleep(delay)


def iter_cybersecurity_advisories(
    client: httpx.Client,
    since: date | None = None,
    delay: float = 1.5,
) -> Iterator[dict]:
    """Yield stubs from the combined cybersecurity advisories listing (alerts + advisories)."""
    yield from _iter_listing_pages(
        client, LISTING_URLS["cybersecurity"], _parse_non_ics_page, since, delay
    )


def iter_ics_advisories(
    client: httpx.Client,
    since: date | None = None,
    delay: float = 1.5,
) -> Iterator[dict]:
    """Yield stubs from the ICS advisories listing (ICS advisories + ICS medical)."""
    yield from _iter_listing_pages(client, LISTING_URLS["ics"], _parse_ics_page, since, delay)
