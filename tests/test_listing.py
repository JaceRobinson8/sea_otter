"""Tests for collector/listing.py — HTML parsing and pagination."""

from sea_otter.collector.listing import (
    _parse_date,
    _parse_ics_page,
    _parse_non_ics_page,
    _type_from_url,
)
from tests.fixtures import CYBERSECURITY_LISTING_PAGE, ICS_LISTING_PAGE

# --- Unit tests: pure parsing helpers ---


def test_parse_date_iso():
    assert _parse_date("2026-05-27") == "2026-05-27"


def test_parse_date_long_month():
    assert _parse_date("May 27, 2026") == "2026-05-27"


def test_parse_date_abbrev_month():
    assert _parse_date("Jan 3, 2025") == "2025-01-03"


def test_parse_date_empty():
    assert _parse_date("") is None


def test_type_from_url_alert():
    assert _type_from_url("/news-events/alerts/2026/05/27/some-slug") == "alert"


def test_type_from_url_cybersecurity_advisory():
    assert (
        _type_from_url("/news-events/cybersecurity-advisories/2026/05/20/aa26-140a")
        == "cybersecurity-advisory"
    )


def test_type_from_url_ics_advisory():
    assert _type_from_url("/news-events/ics-advisories/icsa-26-146-06") == "ics-advisory"


def test_type_from_url_ics_medical():
    assert (
        _type_from_url("/news-events/ics-medical-advisories/icsma-26-146-01")
        == "ics-medical-advisory"
    )


# --- Unit tests: HTML page parsers ---


def test_parse_non_ics_page_count():
    items = _parse_non_ics_page(CYBERSECURITY_LISTING_PAGE)
    assert len(items) == 2


def test_parse_non_ics_page_alert_fields():
    items = _parse_non_ics_page(CYBERSECURITY_LISTING_PAGE)
    alert = next(i for i in items if i["advisory_type"] == "alert")
    assert alert["published"] == "2026-05-27"
    assert alert["title"] == "CISA Adds Three Known Exploited Vulnerabilities to Catalog"
    assert (
        alert["url"]
        == "https://www.cisa.gov/news-events/alerts/2026/05/27/cisa-adds-three-known-exploited-vulnerabilities-catalog"
    )
    assert (
        alert["id"]
        == "news-events/alerts/2026/05/27/cisa-adds-three-known-exploited-vulnerabilities-catalog"
    )


def test_parse_non_ics_page_advisory_fields():
    items = _parse_non_ics_page(CYBERSECURITY_LISTING_PAGE)
    advisory = next(i for i in items if i["advisory_type"] == "cybersecurity-advisory")
    assert advisory["published"] == "2026-05-20"


def test_parse_non_ics_page_deduplication():
    # Duplicate link in HTML should only appear once
    html = CYBERSECURITY_LISTING_PAGE.replace(
        "</main>",
        """
        <div class="c-teaser__content">
          <div class="c-teaser__date"><time datetime="2026-05-27T12:00:00Z">May 27, 2026</time></div>
          <a href="/news-events/alerts/2026/05/27/cisa-adds-three-known-exploited-vulnerabilities-catalog">Duplicate</a>
        </div>
        </main>""",
    )
    items = _parse_non_ics_page(html)
    urls = [i["url"] for i in items]
    assert len(urls) == len(set(urls))


def test_parse_ics_page_count():
    items = _parse_ics_page(ICS_LISTING_PAGE)
    assert len(items) == 2


def test_parse_ics_page_advisory_fields():
    items = _parse_ics_page(ICS_LISTING_PAGE)
    ics = next(i for i in items if i["advisory_type"] == "ics-advisory")
    assert ics["published"] == "2026-05-26"
    assert ics["title"] == "ABB LVS MConfig"
    assert ics["id"] == "news-events/ics-advisories/icsa-26-146-06"


def test_parse_ics_page_medical_type():
    items = _parse_ics_page(ICS_LISTING_PAGE)
    medical = next(i for i in items if "medical" in i["id"])
    assert medical["advisory_type"] == "ics-medical-advisory"


def test_parse_non_ics_page_empty_html():
    assert _parse_non_ics_page("<html><body></body></html>") == []


def test_parse_ics_page_empty_html():
    assert _parse_ics_page("<html><body></body></html>") == []
