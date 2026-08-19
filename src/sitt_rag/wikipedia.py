"""Fetch and parse the "List of cryptids" taxonomy and individual cryptid articles
from Wikipedia's REST HTML API and action API.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup

from sitt_rag.config import LIST_OF_CRYPTIDS_TITLE, USER_AGENT, WIKIPEDIA_ORIGIN

# Transient failures are worth another try: rate-limiting and server-side errors.
# Everything else (404s, redirect loops, unparseable prose) is terminal on the
# first attempt — retrying it just burns wall-clock time on a run of ~1000 articles.
TRANSIENT_STATUSES = frozenset({429, 500, 502, 503, 504})
MAX_RETRIES = 3


def backoff_seconds(attempt: int) -> int:
    """Seconds to wait before retrying after a failed `attempt` (0-based): 1s, 2s, 4s, ..."""
    return 2**attempt

SKIPPED_SECTION_TITLES = {
    "see also",
    "references",
    "external links",
    "further reading",
    "notes",
    "footnotes",
    "sources",
}

_HEADERS = {"User-Agent": USER_AGENT}


@dataclass
class CryptidRef:
    name: str
    category: str
    wikipedia_title: str


@dataclass
class Section:
    title: str
    paragraphs: list[str]


@dataclass
class Article:
    title: str
    sections: list[Section]
    aliases: list[str] = field(default_factory=list)


class WikipediaError(Exception):
    pass


def _get(url: str, params: dict | None = None) -> requests.Response:
    """GET `url`, retrying transient failures with exponential backoff.

    Timeouts, connection errors, and `TRANSIENT_STATUSES` responses are retried
    up to `MAX_RETRIES` times, sleeping 1s/2s/4s in between. Permanent failures
    — 4xx other than rate-limiting, redirect loops — raise on the first attempt.
    """
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params=params, headers=_HEADERS, timeout=30)
        except (requests.Timeout, requests.ConnectionError) as exc:
            retriable: Exception = exc
        else:
            if resp.status_code not in TRANSIENT_STATUSES:
                resp.raise_for_status()  # permanent HTTP failure, or a clean response
                return resp
            retriable = requests.HTTPError(f"status {resp.status_code}", response=resp)

        if attempt == MAX_RETRIES:
            raise retriable
        time.sleep(backoff_seconds(attempt))

    raise AssertionError("unreachable")  # pragma: no cover


def fetch_taxonomy() -> list[CryptidRef]:
    """Fetch the "List of cryptids" page and return every (name, category) entry.

    Categories are the h3 headings under the "List" section; each category's table
    has a "Name" column whose first cell links to the cryptid's own article.
    """
    try:
        resp = _get(f"{WIKIPEDIA_ORIGIN}/api/rest_v1/page/html/{LIST_OF_CRYPTIDS_TITLE}")
    except requests.RequestException as exc:
        raise WikipediaError(f"failed to fetch the cryptid taxonomy: {exc}") from exc

    soup = BeautifulSoup(resp.text, "lxml")

    refs: list[CryptidRef] = []
    for h3 in soup.find_all("h3"):
        category = h3.get_text(strip=True)
        table = h3.find_next("table")
        if table is None:
            continue
        rows = table.find_all("tr")[1:]
        for row in rows:
            cells = row.find_all("td")
            if not cells:
                continue
            link = cells[0].find("a")
            if link is None or "new" in (link.get("class") or []):
                continue
            # The link text is the cryptid's name as listed; its `title` attribute is the
            # Wikipedia article it resolves to, which can differ (e.g. a cryptid documented
            # only within another article, like a person's "alleged encounter" section).
            display_name = link.get_text(strip=True)
            wikipedia_title = link.get("title") or display_name
            refs.append(CryptidRef(name=display_name, category=category, wikipedia_title=wikipedia_title))
    return refs


def _clean_paragraph_text(p) -> str:
    for tag in p.find_all(["sup", "style"]):
        tag.decompose()
    text = p.get_text(" ", strip=True)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return re.sub(r"\s{2,}", " ", text)


def fetch_article(title: str) -> Article:
    """Fetch and parse a cryptid's own Wikipedia article via the REST HTML API.

    Keeps the lead and body prose sections, split by top-level (h2) heading;
    drops "See also", "References", "External links", "Further reading",
    infobox/table markup, image captions, and citation markers.
    """
    try:
        resp = _get(f"{WIKIPEDIA_ORIGIN}/api/rest_v1/page/html/{title}")
    except requests.RequestException as exc:
        raise WikipediaError(f"failed to fetch article {title!r}: {exc}") from exc

    soup = BeautifulSoup(resp.text, "lxml")
    body = soup.find("body")
    if body is None:
        raise WikipediaError(f"article {title!r} has no body")

    top_sections = body.find_all("section", recursive=False)
    if not top_sections:
        raise WikipediaError(f"article {title!r} has no sections")

    sections: list[Section] = []
    for sec in top_sections:
        heading = sec.find(["h2"])
        heading_text = heading.get_text(strip=True) if heading else "Lead"
        if heading_text.strip().lower() in SKIPPED_SECTION_TITLES:
            continue

        paragraphs = [
            text
            for p in sec.find_all("p")
            if (text := _clean_paragraph_text(p))
        ]
        if paragraphs:
            sections.append(Section(title=heading_text, paragraphs=paragraphs))

    if not sections:
        raise WikipediaError(f"article {title!r} has no prose content")

    return Article(title=title, sections=sections)


def fetch_redirects(title: str) -> list[str]:
    """Fetch alias titles (redirects) pointing at this article via the action API."""
    try:
        resp = _get(
            f"{WIKIPEDIA_ORIGIN}/w/api.php",
            params={
                "action": "query",
                "titles": title,
                "prop": "redirects",
                "rdlimit": 500,
                "format": "json",
            },
        )
        data = resp.json()
    except requests.RequestException as exc:
        raise WikipediaError(f"failed to fetch redirects for {title!r}: {exc}") from exc
    except ValueError as exc:  # a 200 carrying something that isn't JSON
        raise WikipediaError(f"redirects response for {title!r} was not JSON: {exc}") from exc

    pages = data.get("query", {}).get("pages", {})
    aliases: list[str] = []
    for page in pages.values():
        for redirect in page.get("redirects", []):
            aliases.append(redirect["title"])
    return aliases
