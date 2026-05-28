"""Scrape an individual CISA advisory page."""

import logging
import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from .listing import HEADERS

log = logging.getLogger(__name__)

BASE_URL = "https://www.cisa.gov"

# File extensions we consider attachments worth downloading
ATTACHMENT_EXTENSIONS = {
    ".pdf",
    ".json",
    ".xml",
    ".stix",
    ".csv",
    ".zip",
    ".txt",
    ".yar",
    ".yara",
    ".snort",
    ".sigma",
}


def _is_attachment(href: str) -> bool:
    path = urlparse(href).path.lower()
    return any(path.endswith(ext) for ext in ATTACHMENT_EXTENSIONS)


def _absolute(href: str) -> str:
    if href.startswith("http"):
        return href
    return urljoin(BASE_URL, href)


def scrape_advisory(client: httpx.Client, url: str) -> dict | None:
    """
    Fetch and parse an advisory page.
    Returns a dict with keys: title, published, body_html, attachment_urls, has_pdf, has_stix.
    Returns None on HTTP error.
    """
    try:
        resp = client.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        log.warning("HTTP error on %s: %s", url, exc)
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Title
    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else None

    # Published date — normalize to YYYY-MM-DD
    published = None
    time_tag = soup.find("time", datetime=True)
    if time_tag:
        published = time_tag["datetime"][:10]
    if not published:
        meta_date = soup.find("meta", {"name": re.compile(r"date", re.I)})
        if meta_date:
            published = meta_date.get("content", "")[:10]

    # Body HTML — grab the main content area
    body_html = ""
    main = (
        soup.find("main") or soup.find("article") or soup.find(id=re.compile(r"main|content", re.I))
    )
    if main:
        body_html = str(main)
    else:
        body_html = str(soup.body) if soup.body else ""

    # Attachment links
    attachment_urls = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if _is_attachment(href):
            attachment_urls.append(_absolute(href))

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for u in attachment_urls:
        if u not in seen:
            seen.add(u)
            deduped.append(u)

    has_pdf = any(urlparse(u).path.lower().endswith(".pdf") for u in deduped)
    has_stix = any(urlparse(u).path.lower().endswith((".stix", ".json", ".xml")) for u in deduped)

    return {
        "title": title,
        "published": published,
        "body_html": body_html,
        "raw_html": resp.text,
        "attachment_urls": deduped,
        "has_pdf": has_pdf,
        "has_stix": has_stix,
    }
