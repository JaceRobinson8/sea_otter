"""Tests for storage/db.py and storage/filesystem.py."""

import json
import sqlite3
from pathlib import Path

import pytest

from sea_otter.storage.db import get_connection, get_latest_date, get_stats, insert_advisory, is_collected
from sea_otter.storage.filesystem import advisory_dir, attachment_path, write_html, write_metadata


# --- DB tests ---

@pytest.fixture
def conn(tmp_path):
    return get_connection(tmp_path / "test.db")


def _record(**overrides):
    base = {
        "id": "news-events/alerts/2026/05/27/some-slug",
        "url": "https://www.cisa.gov/news-events/alerts/2026/05/27/some-slug",
        "title": "Test Advisory",
        "published": "2026-05-27",
        "advisory_type": "alert",
        "has_pdf": True,
        "has_stix": False,
    }
    return {**base, **overrides}


def test_is_collected_false_when_empty(conn):
    assert is_collected(conn, "news-events/alerts/2026/05/27/some-slug") is False


def test_insert_and_is_collected(conn):
    insert_advisory(conn, _record())
    assert is_collected(conn, "news-events/alerts/2026/05/27/some-slug") is True


def test_insert_advisory_idempotent(conn):
    insert_advisory(conn, _record())
    insert_advisory(conn, _record(title="Updated Title"))
    row = conn.execute("SELECT title FROM advisories WHERE id = ?", (_record()["id"],)).fetchone()
    assert row["title"] == "Updated Title"


def test_get_stats_empty(conn):
    stats = get_stats(conn)
    assert stats["total"] == 0
    assert stats["oldest"] is None
    assert stats["newest"] is None


def test_get_stats_counts_by_type(conn):
    insert_advisory(conn, _record(id="a1", url="u1", advisory_type="alert"))
    insert_advisory(conn, _record(id="a2", url="u2", advisory_type="alert"))
    insert_advisory(conn, _record(id="a3", url="u3", advisory_type="ics-advisory"))

    stats = get_stats(conn)
    assert stats["total"] == 3
    assert stats["by_type"]["alert"] == 2
    assert stats["by_type"]["ics-advisory"] == 1


def test_get_latest_date_none_when_empty(conn):
    assert get_latest_date(conn) is None


def test_get_latest_date_returns_max(conn):
    insert_advisory(conn, _record(id="a1", url="u1", published="2026-01-01"))
    insert_advisory(conn, _record(id="a2", url="u2", published="2026-05-27"))
    insert_advisory(conn, _record(id="a3", url="u3", published="2026-03-15"))
    assert get_latest_date(conn) == "2026-05-27"


def test_get_connection_creates_db_file(tmp_path):
    db_path = tmp_path / "subdir" / "sea_otter.db"
    conn = get_connection(db_path)
    conn.close()
    assert db_path.exists()


# --- Filesystem tests ---

@pytest.fixture
def data_root(tmp_path):
    return tmp_path / "data"


def test_advisory_dir_path(data_root):
    path = advisory_dir(data_root, "news-events/alerts/2026/05/27/some-slug")
    assert path == data_root / "advisories" / "news-events" / "alerts" / "2026" / "05" / "27" / "some-slug"


def test_write_metadata_creates_file(data_root):
    meta = {"title": "Test", "published": "2026-05-27"}
    write_metadata(data_root, "news-events/alerts/2026/05/27/some-slug", meta)
    dest = advisory_dir(data_root, "news-events/alerts/2026/05/27/some-slug") / "metadata.json"
    assert dest.exists()
    assert json.loads(dest.read_text())["title"] == "Test"


def test_write_html_creates_file(data_root):
    write_html(data_root, "news-events/alerts/2026/05/27/some-slug", "<html>test</html>")
    dest = advisory_dir(data_root, "news-events/alerts/2026/05/27/some-slug") / "content.html"
    assert dest.exists()
    assert dest.read_text() == "<html>test</html>"


def test_attachment_path_creates_subdir(data_root):
    path = attachment_path(data_root, "news-events/alerts/2026/05/27/some-slug", "report.pdf")
    assert path.parent.name == "attachments"
    assert path.parent.exists()
    assert path.name == "report.pdf"


def test_write_metadata_creates_parent_dirs(data_root):
    """Deep advisory ID paths should be created automatically."""
    write_metadata(data_root, "news-events/ics-advisories/icsa-26-146-06", {"x": 1})
    dest = advisory_dir(data_root, "news-events/ics-advisories/icsa-26-146-06") / "metadata.json"
    assert dest.exists()
