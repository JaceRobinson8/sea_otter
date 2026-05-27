# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

sea-otter collects the CISA cybersecurity advisory dataset for offline analysis. It scrapes all four CISA advisory types (cybersecurity advisories, alerts, ICS advisories, ICS medical advisories) plus the KEV catalog, storing raw HTML, metadata, and attachments (PDFs, etc.) on disk with a SQLite index for deduplication and querying.

## Environment & Commands

Uses `uv` for package management (Python 3.12, `.venv` in repo root).

```bash
uv sync                                         # install dependencies

# Incremental collection (resumes from last collected date)
uv run sea-otter collect

# Collect full history (first run — slow, ~900 listing pages)
uv run sea-otter collect --all

# Collect since a specific date
uv run sea-otter collect --since 2026-01-01

# Skip downloading PDFs/attachments
uv run sea-otter collect --no-attachments

# Snapshot the CISA KEV catalog
uv run sea-otter collect-kev

# Show collection stats
uv run sea-otter status
```

Cron for daily incremental updates:
```
0 8 * * * cd /path/to/sea_otter && uv run sea-otter collect
```

## Architecture

```
src/sea_otter/
  cli.py                      # click CLI — orchestrates the collection pipeline
  collector/
    listing.py                # Paginates CISA listing pages, yields advisory stubs
    advisory.py               # Scrapes individual advisory pages for content + attachment URLs
    downloader.py             # Downloads PDFs/attachments with retry and dedup
    kev.py                    # Fetches the CISA KEV JSON catalog
  storage/
    db.py                     # SQLite schema, insert/query helpers (dedup index)
    filesystem.py             # Writes HTML, metadata.json, attachments to disk

data/
  sea_otter.db                # SQLite index of all collected advisories
  advisories/                 # Raw advisory content, organized by URL path
    news-events/alerts/YYYY/MM/DD/slug/
      metadata.json           # Parsed fields (title, date, type, attachment list)
      content.html            # Full raw HTML of the advisory page
      attachments/            # Downloaded PDFs, STIX, CSV, etc.
    news-events/ics-advisories/icsa-YY-DDD-NN/
      ...
  kev/
    known_exploited_vulnerabilities.json   # Latest KEV snapshot
    YYYY-MM-DD.json                        # Historical snapshots
```

## Key Implementation Details

**Two listing feeds with different URL patterns:**
- Cybersecurity + Alerts: `https://www.cisa.gov/news-events/cybersecurity-advisories` — individual URLs are `/news-events/{type}/YYYY/MM/DD/{slug}`
- ICS + ICS Medical: `https://www.cisa.gov/news-events/ics-advisories` — individual URLs are `/news-events/ics-advisories/icsa-YY-DDD-NN`

**Bot detection:** CISA.gov requires full Chrome-like request headers (defined in `collector/listing.py:HEADERS`). Minimal headers return 403.

**Pagination:** Both listing pages use `?page=N` (0-indexed). The non-ICS listing has ~500 pages; the ICS listing has ~400 pages.

**Advisory ID:** The SQLite primary key and filesystem path are derived from the URL path with the domain stripped (e.g., `news-events/alerts/2026/05/27/some-slug`).

**`--since` behavior:** Without `--all` or `--since`, the CLI automatically resumes from the latest `published` date in the SQLite DB.
