"""Tests for collector/advisory.py — advisory page scraping."""

import httpx
import respx

from sea_otter.collector.advisory import scrape_advisory
from tests.fixtures import ADVISORY_PAGE, ADVISORY_PAGE_NO_ATTACHMENTS

URL = "https://www.cisa.gov/news-events/alerts/2026/05/27/some-advisory"


def test_scrape_advisory_title():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, text=ADVISORY_PAGE))
        with httpx.Client() as client:
            result = scrape_advisory(client, URL)
    assert result["title"] == "CISA Adds Three Known Exploited Vulnerabilities to Catalog"


def test_scrape_advisory_published_date():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, text=ADVISORY_PAGE))
        with httpx.Client() as client:
            result = scrape_advisory(client, URL)
    assert result["published"] == "2026-05-27"


def test_scrape_advisory_attachment_urls():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, text=ADVISORY_PAGE))
        with httpx.Client() as client:
            result = scrape_advisory(client, URL)
    assert any("report.pdf" in u for u in result["attachment_urls"])
    assert any("stix-bundle.json" in u for u in result["attachment_urls"])


def test_scrape_advisory_external_links_excluded():
    """Non-attachment external links should not appear in attachment_urls."""
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, text=ADVISORY_PAGE))
        with httpx.Client() as client:
            result = scrape_advisory(client, URL)
    assert not any("external.example.com" in u for u in result["attachment_urls"])


def test_scrape_advisory_has_pdf_flag():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, text=ADVISORY_PAGE))
        with httpx.Client() as client:
            result = scrape_advisory(client, URL)
    assert result["has_pdf"] is True


def test_scrape_advisory_has_stix_flag():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, text=ADVISORY_PAGE))
        with httpx.Client() as client:
            result = scrape_advisory(client, URL)
    assert result["has_stix"] is True


def test_scrape_advisory_no_attachments():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, text=ADVISORY_PAGE_NO_ATTACHMENTS))
        with httpx.Client() as client:
            result = scrape_advisory(client, URL)
    assert result["attachment_urls"] == []
    assert result["has_pdf"] is False
    assert result["has_stix"] is False


def test_scrape_advisory_attachment_deduplication():
    html = ADVISORY_PAGE.replace(
        "</main>",
        '<a href="/sites/default/files/publications/report.pdf">Duplicate PDF link</a></main>',
    )
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, text=html))
        with httpx.Client() as client:
            result = scrape_advisory(client, URL)
    pdf_urls = [u for u in result["attachment_urls"] if u.endswith(".pdf")]
    assert len(pdf_urls) == len(set(pdf_urls))


def test_scrape_advisory_returns_none_on_http_error():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(403))
        with httpx.Client() as client:
            result = scrape_advisory(client, URL)
    assert result is None


def test_scrape_advisory_body_html_present():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, text=ADVISORY_PAGE))
        with httpx.Client() as client:
            result = scrape_advisory(client, URL)
    assert "<main>" in result["body_html"]
    assert len(result["body_html"]) > 0
