import sqlite3
from datetime import datetime, timezone
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS advisories (
    id            TEXT PRIMARY KEY,
    url           TEXT NOT NULL,
    title         TEXT,
    published     TEXT,
    advisory_type TEXT,
    collected_at  TEXT,
    has_pdf       INTEGER DEFAULT 0,
    has_stix      INTEGER DEFAULT 0
);
"""


def get_connection(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    conn.commit()
    return conn


def is_collected(conn: sqlite3.Connection, advisory_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM advisories WHERE id = ?", (advisory_id,)
    ).fetchone()
    return row is not None


def insert_advisory(conn: sqlite3.Connection, record: dict) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO advisories
            (id, url, title, published, advisory_type, collected_at, has_pdf, has_stix)
        VALUES
            (:id, :url, :title, :published, :advisory_type, :collected_at, :has_pdf, :has_stix)
        """,
        {
            "id": record["id"],
            "url": record["url"],
            "title": record.get("title"),
            "published": record.get("published"),
            "advisory_type": record.get("advisory_type"),
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "has_pdf": int(record.get("has_pdf", False)),
            "has_stix": int(record.get("has_stix", False)),
        },
    )
    conn.commit()


def get_stats(conn: sqlite3.Connection) -> dict:
    row = conn.execute(
        "SELECT COUNT(*) as total, MIN(published) as oldest, MAX(published) as newest "
        "FROM advisories"
    ).fetchone()
    by_type = conn.execute(
        "SELECT advisory_type, COUNT(*) as cnt FROM advisories GROUP BY advisory_type ORDER BY cnt DESC"
    ).fetchall()
    return {
        "total": row["total"],
        "oldest": row["oldest"],
        "newest": row["newest"],
        "by_type": {r["advisory_type"]: r["cnt"] for r in by_type},
    }


def get_latest_date(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT MAX(published) as d FROM advisories").fetchone()
    return row["d"] if row else None
