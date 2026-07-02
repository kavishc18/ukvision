"""Stage 4: draft the monthly brief from what changed in data/commitments/
since the last brief, using a large Groq model. Writes to
drafts/brief-YYYY-MM.md for a human to edit before publishing to
site/src/content/briefs/.

Run manually once a month (not on the weekly cron) — this is an editorial
step, not an automated publish.
"""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

from groq_client import BRIEF_MODEL, chat_json

REPO_ROOT = Path(__file__).resolve().parent.parent
COMMITMENTS_DIR = REPO_ROOT / "data" / "commitments"
DRAFTS_DIR = REPO_ROOT / "drafts"

SYSTEM_PROMPT = """You are drafting a monthly brief for a non-partisan, \
evidence-linked tracker of India-UK Vision 2035 technology, trade, and \
education commitments. The audience is a working peer and their staff.

Write in a neutral, factual, think-tank register — no adjectives implying \
success or failure, no editorializing, past tense for completed events. \
Use only the five statuses given: delivered, in_progress, announced_only, \
no_public_evidence, superseded. Never use words like "stalled", "failed", \
or "broken promise".

Structure the brief in markdown as:
# Vision 2035 Monthly Brief — {month_year}
## What moved this month
## No public evidence
## Suggested parliamentary questions
(5 PQs, phrased in the formal Lords/Commons "To ask His Majesty's \
Government..." style)

Respond with JSON only, in the form {{"brief_markdown": "<the full markdown \
brief as a single string>"}}. Do not add commentary outside that field.
"""


def _git_diff_since_last_brief() -> str:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "log", "-1", "--format=%H", "--", "drafts/"],
        capture_output=True,
        text=True,
    )
    last_commit = result.stdout.strip()
    diff_range = f"{last_commit}..HEAD" if last_commit else "HEAD"
    diff = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "diff", diff_range, "--", "data/commitments/"],
        capture_output=True,
        text=True,
    )
    return diff.stdout


def _no_public_evidence_list() -> list[str]:
    items = []
    for path in sorted(COMMITMENTS_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        if data.get("status") == "no_public_evidence":
            items.append(f"- {data['id']}: {data['title']}")
    return items


def main() -> None:
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

    diff = _git_diff_since_last_brief()
    no_evidence = "\n".join(_no_public_evidence_list())

    now = datetime.now(timezone.utc)
    month_year = now.strftime("%B %Y")

    user_prompt = (
        f"Month: {month_year}\n\n"
        f"Git diff of data/commitments/ since the last brief:\n{diff[:12000]}\n\n"
        f"Commitments currently marked no_public_evidence:\n{no_evidence}\n"
    )

    result = chat_json(BRIEF_MODEL, SYSTEM_PROMPT.format(month_year=month_year), user_prompt)
    markdown = result.get("brief_markdown") or next(iter(result.values()), "")

    out_path = DRAFTS_DIR / f"brief-{now.strftime('%Y-%m')}.md"
    out_path.write_text(markdown if isinstance(markdown, str) else str(markdown))
    print(f"[brief] draft written to {out_path} — edit by hand before publishing")


if __name__ == "__main__":
    main()
