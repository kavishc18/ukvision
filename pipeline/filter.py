"""Stage 1: cheap relevance filter over today's inbox using a small Groq model.

Reads the newest data/inbox/*.jsonl file, batches items 10 at a time,
and writes only the ones the model marks relevant to
data/inbox/relevant-YYYY-MM-DD.jsonl for classify.py to pick up.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from groq_client import FILTER_MODEL, chat_json

REPO_ROOT = Path(__file__).resolve().parent.parent
INBOX_DIR = REPO_ROOT / "data" / "inbox"

BATCH_SIZE = 10

SYSTEM_PROMPT = """You are a relevance filter for a non-partisan policy \
tracker monitoring delivery of the India-UK Vision 2035 agreement \
(technology, trade, and education-tech commitments only).

Given a numbered list of news headlines + snippets, decide which ones \
could plausibly contain concrete evidence about progress on a UK-India \
technology, trade/digital, or education-tech commitment (funding, \
launch, meeting outcome, ratification step, named project). General \
UK-India diplomacy with no tech/trade/education angle is NOT relevant.

Respond with JSON only, in the form:
{"results": [{"index": 1, "relevant": true}, {"index": 2, "relevant": false}, ...]}
"""


def _latest_inbox_file() -> Path | None:
    files = sorted(INBOX_DIR.glob("20*-*-*.jsonl"))
    files = [f for f in files if not f.stem.startswith("relevant-")]
    return files[-1] if files else None


def _batches(items: list[dict], size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def main() -> None:
    src = _latest_inbox_file()
    if src is None:
        print("[filter] no inbox file found, nothing to do")
        return

    items = [json.loads(line) for line in src.read_text().splitlines() if line.strip()]
    if not items:
        print("[filter] inbox file empty")
        return

    relevant: list[dict] = []
    for batch in _batches(items, BATCH_SIZE):
        numbered = "\n".join(
            f"{i + 1}. {it['title']} — {it.get('snippet', '')[:200]}"
            for i, it in enumerate(batch)
        )
        result = chat_json(FILTER_MODEL, SYSTEM_PROMPT, numbered)
        flags = {r["index"]: r["relevant"] for r in result.get("results", [])}
        for i, it in enumerate(batch):
            if flags.get(i + 1):
                relevant.append(it)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = INBOX_DIR / f"relevant-{today}.jsonl"
    with out_path.open("w") as f:
        for it in relevant:
            f.write(json.dumps(it) + "\n")

    print(f"[filter] {len(relevant)}/{len(items)} items passed relevance filter -> {out_path}")


if __name__ == "__main__":
    main()
