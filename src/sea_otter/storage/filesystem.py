import json
from pathlib import Path


def advisory_dir(data_root: Path, advisory_id: str) -> Path:
    """Return the directory for a given advisory id (e.g. 'alerts/2026/05/27/some-slug')."""
    parts = advisory_id.replace("\\", "/").lstrip("/").split("/")
    return data_root / "advisories" / Path(*parts)


def write_metadata(data_root: Path, advisory_id: str, metadata: dict) -> None:
    d = advisory_dir(data_root, advisory_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "metadata.json").write_text(json.dumps(metadata, indent=2, default=str))


def write_html(data_root: Path, advisory_id: str, html: str) -> None:
    d = advisory_dir(data_root, advisory_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "content.html").write_text(html, encoding="utf-8")


def attachment_path(data_root: Path, advisory_id: str, filename: str) -> Path:
    d = advisory_dir(data_root, advisory_id) / "attachments"
    d.mkdir(parents=True, exist_ok=True)
    return d / filename
