"""Shared HTML fixtures that mirror CISA's real page structure."""

# Matches the c-teaser structure used on CISA listing pages
CYBERSECURITY_LISTING_PAGE = """
<html><body>
<main>
  <div class="c-teaser__content">
    <div class="c-teaser__eyebrow">
      <div class="c-teaser__date"><time datetime="2026-05-27T12:00:00Z">May 27, 2026</time></div>
      <div class="c-teaser__meta">Alert</div>
    </div>
    <h3 class="c-teaser__title">
      <a href="/news-events/alerts/2026/05/27/cisa-adds-three-known-exploited-vulnerabilities-catalog">
        <span>CISA Adds Three Known Exploited Vulnerabilities to Catalog</span>
      </a>
    </h3>
  </div>
  <div class="c-teaser__content">
    <div class="c-teaser__eyebrow">
      <div class="c-teaser__date"><time datetime="2026-05-20T12:00:00Z">May 20, 2026</time></div>
      <div class="c-teaser__meta">Advisory</div>
    </div>
    <h3 class="c-teaser__title">
      <a href="/news-events/cybersecurity-advisories/2026/05/20/aa26-140a">
        <span>APT Group Targeting Critical Infrastructure</span>
      </a>
    </h3>
  </div>
</main>
</body></html>
"""

ICS_LISTING_PAGE = """
<html><body>
<main>
  <div class="c-teaser__content">
    <div class="c-teaser__eyebrow">
      <div class="c-teaser__date"><time datetime="2026-05-26T12:00:00Z">May 26, 2026</time></div>
      <div class="c-teaser__meta">ICS Advisory | ICSA-26-146-06</div>
    </div>
    <h3 class="c-teaser__title">
      <a href="/news-events/ics-advisories/icsa-26-146-06">
        <span>ABB LVS MConfig</span>
      </a>
    </h3>
  </div>
  <div class="c-teaser__content">
    <div class="c-teaser__eyebrow">
      <div class="c-teaser__date"><time datetime="2026-05-26T12:00:00Z">May 26, 2026</time></div>
      <div class="c-teaser__meta">ICS Medical Advisory | ICSMA-26-146-01</div>
    </div>
    <h3 class="c-teaser__title">
      <a href="/news-events/ics-medical-advisories/icsma-26-146-01">
        <span>Siemens Healthineers Device</span>
      </a>
    </h3>
  </div>
</main>
</body></html>
"""

ADVISORY_PAGE = """
<html><body>
<main>
  <h1>CISA Adds Three Known Exploited Vulnerabilities to Catalog</h1>
  <div class="advisory-meta">
    <time datetime="2026-05-27T12:00:00Z">May 27, 2026</time>
  </div>
  <div class="advisory-body">
    <p>CISA has added three new vulnerabilities to its Known Exploited Vulnerabilities Catalog.</p>
    <ul>
      <li>CVE-2024-1234</li>
      <li>CVE-2024-5678</li>
    </ul>
    <a href="/sites/default/files/publications/report.pdf">Download PDF Report</a>
    <a href="/sites/default/files/feeds/stix-bundle.json">Download STIX Bundle</a>
    <a href="https://external.example.com/resource">External Link</a>
  </div>
</main>
</body></html>
"""

ADVISORY_PAGE_NO_ATTACHMENTS = """
<html><body>
<main>
  <h1>Advisory With No Attachments</h1>
  <time datetime="2026-04-01T12:00:00Z">April 1, 2026</time>
  <p>Some advisory content with no linked files.</p>
</main>
</body></html>
"""
