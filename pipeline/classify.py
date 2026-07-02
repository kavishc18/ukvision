"""Stage 2: classify filtered items against tracked commitments and append
proposed evidence entries directly into data/commitments/*.yaml.

This script never writes a final `status:` change by itself — it only
appends to the `evidence:` list and, if the model suggests a status
different from the current one, adds a `pending_status_suggestion:` field
for a human to review. The GitHub Actions workflow turns the resulting
working-tree diff into a PR (peter-evans/create-pull-request) — nothing
here talks to GitHub directly. A human approves every PR before any
status changes take effect.
"""
from __future__ import annotations

import email.utils
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

from pipeline.groq_client import CLASSIFY_MODEL, chat_json

REPO_ROOT = Path(__file__).resolve().parent.parent
INBOX_DIR = REPO_ROOT / "data" / "inbox"
COMMITMENTS_DIR = REPO_ROOT / "data" / "commitments"

MAX_ARTICLE_CHARS = 3000 * 4  # ~3k tokens
SLEEP_BETWEEN_ITEMS = 1.5  # be gentle on the free-tier TPD limit

SYSTEM_PROMPT_TEMPLATE = """You are a research assistant for a non-partisan \
policy tracker monitoring delivery of the India-UK Vision 2035 agreement.

Given a news item and a list of tracked commitments, identify which \
commitments (if any) the item provides evidence about.

Rules:
- Only match if the item contains a concrete fact (funding, launch, \
meeting outcome, project, ratification step). Restatements of ambition \
are NOT evidence — mark suggests_status "announced_only".
- evidence_summary: one sentence, purely factual, past tense, no opinion \
words, must be a paraphrase, not a quotation.
- suggests_status must be exactly one of: delivered, in_progress, \
announced_only, no_public_evidence, superseded.
- If nothing matches, return {{"matched_commitments": []}}.
- Respond with JSON only.

COMMITMENTS:
{id_title_list}
"""


def _latest_relevant_file() -> Path | None:
    files = sorted(INBOX_DIR.glob("relevant-*.jsonl"))
    return files[-1] if files else None


def _load_commitments() -> dict[str, dict]:
    commitments = {}
    for path in COMMITMENTS_DIR.glob("*.yaml"):
        data = yaml.safe_load(path.read_text())
        commitments[data["id"]] = {"path": path, "data": data}
    return commitments


def _id_title_list(commitments: dict[str, dict]) -> str:
    return "\n".join(f"{cid}: {c['data']['title']}" for cid, c in sorted(commitments.items()))


def _as_commitment_id(entry) -> str | None:
    """The model is asked for plain ID strings but JSON mode doesn't
    guarantee shape — tolerate {"id": "..."} / {"commitment_id": "..."}
    objects instead of crashing the whole run on one malformed item."""
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        for key in ("id", "commitment_id", "cid"):
            if isinstance(entry.get(key), str):
                return entry[key]
    return None


def _normalize_date(raw: str) -> str:
    """Item dates arrive either already ISO (gov.uk) or RFC822 (Google
    News RSS, e.g. "Fri, 05 Jul 2026 12:34:56 GMT"). A naive [:10] slice
    silently mangles the RFC822 form into garbage like "Fri, 05 Ju" — parse
    properly and fall back to today only if nothing usable is found."""
    raw = (raw or "").strip()
    if not raw:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
        return raw[:10]
    try:
        parsed = email.utils.parsedate_to_datetime(raw)
        if parsed is not None:
            return parsed.strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        pass
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def classify_item(item: dict, commitments: dict[str, dict]) -> dict:
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(id_title_list=_id_title_list(commitments))
    article_text = (item.get("snippet", "") or item.get("title", ""))[:MAX_ARTICLE_CHARS]
    user_prompt = (
        f"ITEM ({item.get('source_type', 'other')}, {item.get('date', 'unknown date')}):\n"
        f"Title: {item.get('title', '')}\n"
        f"URL: {item.get('url', '')}\n"
        f"Text: {article_text}"
    )
    return chat_json(CLASSIFY_MODEL, system_prompt, user_prompt)


def append_evidence(commitment_path: Path, item: dict, result: dict) -> bool:
    # A blank summary or missing URL is worse than no evidence at all —
    # it would sit on the live site looking sourced when it isn't. Reject
    # rather than write a placeholder a human reviewer has to catch later.
    summary = (result.get("evidence_summary") or "").strip()
    if not summary or not item.get("url"):
        return False

    data = yaml.safe_load(commitment_path.read_text())
    data.setdefault("evidence", [])

    existing_urls = {e.get("url") for e in data["evidence"]}
    if item.get("url") in existing_urls:
        return False

    data["evidence"].append(
        {
            "date": _normalize_date(item.get("date", "")),
            "url": item.get("url", ""),
            "source_type": item.get("source_type", "other"),
            "summary": summary,
        }
    )

    suggested = result.get("suggests_status")
    if suggested and suggested != data.get("status"):
        data["pending_status_suggestion"] = {
            "suggested_status": suggested,
            "confidence": result.get("confidence", "unknown"),
            "source_url": item.get("url", ""),
            "note": "Proposed by the weekly classify pipeline — review before accepting.",
        }

    commitment_path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    return True


def main() -> None:
    src = _latest_relevant_file()
    if src is None:
        print("[classify] no filtered inbox file found, nothing to do")
        return

    items = [json.loads(line) for line in src.read_text().splitlines() if line.strip()]
    if not items:
        print("[classify] filtered inbox empty")
        return

    commitments = _load_commitments()
    changed = 0
    total = len(items)

    for idx, item in enumerate(items, start=1):
        try:
            result = classify_item(item, commitments)
        except Exception as e:
            print(f"[classify] {idx}/{total}: FAILED ({e})", flush=True)
            if idx < total:
                time.sleep(SLEEP_BETWEEN_ITEMS)
            continue

        raw_matched = result.get("matched_commitments", []) or []
        matched = [_as_commitment_id(m) for m in raw_matched]
        matched = [m for m in matched if m]

        appended_here = 0
        try:
            for cid in matched:
                if cid not in commitments:
                    continue
                if not result.get("quote_free", True):
                    continue
                if append_evidence(commitments[cid]["path"], item, result):
                    changed += 1
                    appended_here += 1
        except Exception as e:
            print(f"[classify] {idx}/{total}: FAILED while appending ({e})", flush=True)

        if appended_here:
            print(f"[classify] {idx}/{total}: matched {matched}", flush=True)
        elif idx % 20 == 0:
            print(f"[classify] {idx}/{total}: no match", flush=True)

        if idx < total:
            time.sleep(SLEEP_BETWEEN_ITEMS)

    print(f"[classify] appended {changed} evidence entries across commitment files")


if __name__ == "__main__":
    main()
