"""Tests for collector/downloader.py."""

import httpx
import respx

from sea_otter.collector.downloader import download_attachments, download_file


def test_download_file_success(tmp_path):
    url = "https://www.cisa.gov/files/report.pdf"
    dest = tmp_path / "report.pdf"
    with respx.mock:
        respx.get(url).mock(return_value=httpx.Response(200, content=b"%PDF-1.4 fake content"))
        with httpx.Client() as client:
            ok = download_file(client, url, dest, delay=0)
    assert ok is True
    assert dest.exists()
    assert dest.read_bytes() == b"%PDF-1.4 fake content"


def test_download_file_skips_if_exists(tmp_path):
    url = "https://www.cisa.gov/files/report.pdf"
    dest = tmp_path / "report.pdf"
    dest.write_bytes(b"existing content")
    # No mock needed — should not make an HTTP request
    with httpx.Client() as client:
        ok = download_file(client, url, dest, delay=0)
    assert ok is True
    assert dest.read_bytes() == b"existing content"


def test_download_file_returns_false_on_persistent_error(tmp_path):
    url = "https://www.cisa.gov/files/report.pdf"
    dest = tmp_path / "report.pdf"
    with respx.mock:
        respx.get(url).mock(return_value=httpx.Response(404))
        with httpx.Client() as client:
            ok = download_file(client, url, dest, delay=0)
    assert ok is False
    assert not dest.exists()


def test_download_attachments_saves_multiple_files(tmp_path):
    urls = [
        "https://www.cisa.gov/files/report.pdf",
        "https://www.cisa.gov/files/bundle.json",
    ]
    advisory_dir = tmp_path / "advisory"
    with respx.mock:
        respx.get(urls[0]).mock(return_value=httpx.Response(200, content=b"pdf"))
        respx.get(urls[1]).mock(return_value=httpx.Response(200, content=b"{}"))
        with httpx.Client() as client:
            saved = download_attachments(client, urls, advisory_dir, delay=0)

    assert "report.pdf" in saved
    assert "bundle.json" in saved
    assert (advisory_dir / "attachments" / "report.pdf").exists()
    assert (advisory_dir / "attachments" / "bundle.json").exists()


def test_download_attachments_partial_failure(tmp_path):
    """Failed downloads are omitted from saved list but don't abort others."""
    urls = [
        "https://www.cisa.gov/files/good.pdf",
        "https://www.cisa.gov/files/bad.pdf",
    ]
    advisory_dir = tmp_path / "advisory"
    with respx.mock:
        respx.get(urls[0]).mock(return_value=httpx.Response(200, content=b"pdf"))
        respx.get(urls[1]).mock(return_value=httpx.Response(500))
        with httpx.Client() as client:
            saved = download_attachments(client, urls, advisory_dir, delay=0)

    assert "good.pdf" in saved
    assert "bad.pdf" not in saved
