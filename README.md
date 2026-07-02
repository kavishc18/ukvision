# Vision 2035 Tracker

An independent, evidence-linked tracker of every technology, trade-digital,
and education-tech commitment in the India-UK Vision 2035 framework.

See [docs/methodology.md](docs/methodology.md) for the status taxonomy,
sourcing rules, and review process — read that before touching
`data/commitments/`.

## Repo layout

```
data/commitments/*.yaml   one file per tracked commitment (the database)
data/inbox/*.jsonl        raw fetched candidate evidence, gitignored, 90-day retention
pipeline/                 fetch -> filter -> classify -> brief (Groq-powered)
site/                     Astro static site, reads ../data at build time
.github/workflows/        weekly-ingest.yml (cron -> PR), deploy.yml (push -> Pages)
docs/methodology.md       canonical methodology doc
drafts/                   brief.py output, hand-edit before publishing to site/src/content/briefs/
```

## Running the site locally

```bash
cd site
npm install
npm run dev       # http://localhost:4321
npm run build     # writes site/dist
```

The site reads commitment YAML straight from `../data/commitments` and
published briefs from `site/src/content/briefs/*.md` — no database, no API.

## Running the ingestion pipeline locally

Requires a free Groq API key from [console.groq.com](https://console.groq.com).
**Check console.groq.com/docs/models before running** — model names in
`pipeline/groq_client.py` (`FILTER_MODEL`, `CLASSIFY_MODEL`, `BRIEF_MODEL`)
rotate and may need updating.

```bash
cd "vision 2035"   # repo root
pip install -r pipeline/requirements.txt
export GROQ_API_KEY=your-key-here

python -m pipeline.fetch      # writes data/inbox/YYYY-MM-DD.jsonl
python -m pipeline.filter     # stage 1: cheap relevance filter -> relevant-YYYY-MM-DD.jsonl
python -m pipeline.classify   # stage 2: matches items to commitments, appends evidence in place
```

`classify.py` only ever appends to a commitment's `evidence:` list and adds
a `pending_status_suggestion:` block if it thinks the status should
change — it never edits `status:` directly. Review the resulting `git
diff` on `data/commitments/` by hand before committing.

Monthly, run the brief generator and hand-edit the result:

```bash
python -m pipeline.brief      # writes drafts/brief-YYYY-MM.md
```

When happy with a draft, copy/move it to
`site/src/content/briefs/brief-YYYY-MM.md` so it appears under `/briefs/`.

## GitHub Actions setup (once you have a GitHub remote)

1. Add `GROQ_API_KEY` as a repository secret (Settings → Secrets and
   variables → Actions).
2. Enable GitHub Pages, source = "GitHub Actions" (Settings → Pages).
3. `weekly-ingest.yml` runs Sunday 22:00 UTC, opens a PR with proposed
   evidence — **review and merge by hand**, never auto-merge.
4. `deploy.yml` builds and publishes `site/dist` on every push to `main`.

## Data model

Each `data/commitments/*.yaml` file follows this shape — see any existing
file for a worked example with real citations:

```yaml
id: v2035-tech-001
pillar: technology            # technology | trade_digital | education_tech
title: "..."
commitment_text: >
  Paraphrase of the commitment, not a long quote from the source doc.
source_url: https://...
announced: YYYY-MM-DD
owners: [DSIT, MeitY]
status: in_progress            # delivered | in_progress | announced_only | no_public_evidence | superseded
status_rationale: >
  Why this status, in plain, factual, past-tense language.
evidence:
  - date: YYYY-MM-DD
    url: https://...
    source_type: hansard       # hansard | gov_uk | pib | mea | press | other
    summary: "One factual sentence, no adjectives."
suggested_pq: >
  A formal "To ask His Majesty's Government..." parliamentary question.
last_reviewed: YYYY-MM-DD
```

Dates in these files must stay quoted-free plain YAML dates (`2026-04-28`,
not `"2026-04-28"`) — the site loader parses them with `js-yaml`'s
`JSON_SCHEMA` specifically so they come through as strings, not `Date`
objects. Keep that in mind if you change the loader.

## Status of this build

Seed data (`data/commitments/*.yaml`) — 21 commitments — was hand-written
from real, cited sources (Vision 2035 text, the July 2025 TSI anniversary
statement, the 28 April 2026 Westminster Hall debate, gov.uk, PIB, MEA,
and press coverage). It is not exhaustive of every possible Vision 2035
tech-pillar commitment; extend it the same way — real source first,
YAML second — rather than by generating plausible-looking entries.

The ingestion pipeline (`pipeline/`) is implemented for gov.uk Search API
and Google News RSS. Hansard and TheyWorkForYou fetchers are stubbed in
`fetch.py` (`fetch_hansard`, `fetch_theyworkforyou`) — Google News RSS
covers Indian-side press as a fallback in the meantime.

Not yet done: creating the actual GitHub remote/repo, wiring the
`GROQ_API_KEY` secret, first live run of the weekly-ingest workflow, and
the hand-written Year One Scorecard narrative (`site/src/pages/year-one.astro`
currently has live commitment tables but a placeholder narrative).
