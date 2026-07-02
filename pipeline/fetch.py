"""Fetch candidate news/evidence items from free sources and write them to
data/inbox/YYYY-MM-DD.jsonl, deduped by URL hash against the last 90 days
of inbox files.

Sources implemented: gov.uk Search API, Google News RSS. Hansard and
TheyWorkForYou are stubbed with fetch_hansard()/fetch_theyworkforyou() —
both are free but need a bit more query-shaping per commitment; wire them
in when the two easy sources are running end-to-end (see README).
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser

REPO_ROOT = Path(__file__).resolve().parent.parent
INBOX_DIR = REPO_ROOT / "data" / "inbox"
RETENTION_DAYS = 90

GOVUK_QUERIES = [
    "India technology",
    "Vision 2035",
    "Technology Security Initiative",
    "UK-India",
]

GOOGLE_NEWS_QUERIES = [
    '"vision 2035" UK India',
    "Technology Security Initiative UK India",
    "UK India AI",
    "CETA India UK",
]


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.strip().lower().encode("utf-8")).hexdigest()[:16]


def _existing_hashes() -> set[str]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    hashes: set[str] = set()
    if not INBOX_DIR.exists():
        return hashes
    for path in INBOX_DIR.glob("*.jsonl"):
        try:
            file_date = datetime.strptime(path.stem, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if file_date < cutoff:
            continue
        with path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                hashes.add(item["url_hash"])
    return hashes


def _prune_old_files() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    if not INBOX_DIR.exists():
        return
    for path in INBOX_DIR.glob("*.jsonl"):
        try:
            file_date = datetime.strptime(path.stem, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if file_date < cutoff:
            path.unlink()


def fetch_govuk(query: str) -> list[dict]:
    url = "https://www.gov.uk/api/search.json?" + urllib.parse.urlencode(
        {"q": query, "order": "-public_timestamp", "count": 50}
    )
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read())
    items = []
    for result in data.get("results", []):
        link = result.get("link", "")
        if link.startswith("/"):
            link = "https://www.gov.uk" + link
        items.append(
            {
                "source_type": "gov_uk",
                "url": link,
                "title": result.get("title", ""),
                "snippet": result.get("description", ""),
                "date": result.get("public_timestamp", ""),
                "fetched_query": query,
            }
        )
    return items


def fetch_google_news(query: str) -> list[dict]:
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": query, "hl": "en-GB", "gl": "GB", "ceid": "GB:en"}
    )
    feed = feedparser.parse(url)
    items = []
    for entry in feed.entries:
        items.append(
            {
                "source_type": "press",
                "url": entry.get("link", ""),
                "title": entry.get("title", ""),
                "snippet": entry.get("summary", ""),
                "date": entry.get("published", ""),
                "fetched_query": query,
            }
        )
    return items


def fetch_hansard(query: str) -> list[dict]:
    """TODO: wire up hansard-api.parliament.uk search endpoints."""
    return []


def fetch_theyworkforyou(query: str) -> list[dict]:
    """TODO: wire up theyworkforyou.com/api (needs a free API key)."""
    return []


def main() -> None:
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    _prune_old_files()
    seen = _existing_hashes()

    collected: list[dict] = []
    for query in GOVUK_QUERIES:
        try:
            collected.extend(fetch_govuk(query))
        except Exception as e:
            print(f"[fetch] gov.uk query failed ({query!r}): {e}")
    for query in GOOGLE_NEWS_QUERIES:
        try:
            collected.extend(fetch_google_news(query))
        except Exception as e:
            print(f"[fetch] Google News query failed ({query!r}): {e}")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = INBOX_DIR / f"{today}.jsonl"

    new_count = 0
    with out_path.open("a") as f:
        for item in collected:
            if not item.get("url"):
                continue
            h = _url_hash(item["url"])
            if h in seen:
                continue
            seen.add(h)
            item["url_hash"] = h
            item["fetched_at"] = datetime.now(timezone.utc).isoformat()
            f.write(json.dumps(item) + "\n")
            new_count += 1

    print(f"[fetch] wrote {new_count} new items to {out_path}")


if __name__ == "__main__":
    main()
