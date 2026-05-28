# sea-otter

[![CI](https://github.com/JaceRobinson8/sea_otter/actions/workflows/ci.yml/badge.svg)](https://github.com/JaceRobinson8/sea_otter/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/JaceRobinson8/sea_otter/branch/main/graph/badge.svg)](https://codecov.io/gh/JaceRobinson8/sea_otter)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Collects the CISA cybersecurity advisory dataset for offline analysis. Scrapes all four advisory types, downloads attachments (PDFs, STIX bundles, etc.), and snapshots the Known Exploited Vulnerabilities (KEV) catalog. Designed to run incrementally on a schedule.

## Collected data

- **Cybersecurity Advisories** — joint advisories, malware analysis reports (AA-series)
- **Alerts** — short-notice notifications about active threats and KEV additions
- **ICS Advisories** — industrial control system vulnerabilities (ICSA-series)
- **ICS Medical Advisories** — medical device vulnerabilities (ICSMA-series)
- **KEV Catalog** — CISA's Known Exploited Vulnerabilities JSON feed

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/JaceRobinson8/sea_otter.git
cd sea_otter
uv sync
```

## Usage

```bash
# Incremental collection — resumes from last collected date automatically
uv run sea-otter collect

# Full historical backfill (first run — slow, ~900 listing pages)
uv run sea-otter collect --all

# Collect since a specific date
uv run sea-otter collect --since 2026-01-01

# Skip downloading PDF/attachment files
uv run sea-otter collect --no-attachments

# Snapshot the KEV catalog
uv run sea-otter collect-kev

# Show collection statistics
uv run sea-otter status
```

### Scheduling

Add to crontab for daily incremental updates:

```
0 8 * * * cd /path/to/sea_otter && uv run sea-otter collect
```

## Data layout

```
data/
  sea_otter.db                          # SQLite index (queryable metadata)
  advisories/
    news-events/alerts/YYYY/MM/DD/slug/
      metadata.json                     # title, date, type, attachment list
      content.html                      # full raw HTML
      attachments/                      # downloaded PDFs, STIX bundles, etc.
    news-events/ics-advisories/icsa-YY-DDD-NN/
      ...
  kev/
    known_exploited_vulnerabilities.json  # latest snapshot
    YYYY-MM-DD.json                       # dated snapshots
```

The SQLite database (`data/sea_otter.db`) is the primary index — query it to find advisories by type, date range, or attachment presence before loading raw files.

## Development

```bash
uv sync --dev
uv run pytest
```
