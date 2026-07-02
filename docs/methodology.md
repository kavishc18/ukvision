# Methodology

This tracker follows every technology, trade-digital, and education-tech
commitment made in the [India-UK Vision 2035](https://www.gov.uk/government/publications/india-uk-vision-2035/india-uk-vision-2035)
framework, published 24 July 2025. It is an independent project, not
affiliated with, endorsed by, or funded by the UK or Indian governments,
any political party, or either High Commission.

This file is the canonical source; `site/src/pages/methodology.astro`
renders the same content on the live site — keep them in sync when editing.

## What "status" means — and doesn't mean

Every commitment is assigned one of five statuses. These describe the state
of *publicly available evidence*, not a judgement on whether work is
actually happening behind the scenes. Absence of evidence is not evidence
of absence — governments do a great deal of legitimate work that isn't
publicised on a timeline this tracker can see.

| Status | Meaning |
|---|---|
| `delivered` | Commitment fulfilled, primary-source evidence |
| `in_progress` | Concrete public activity since announcement |
| `announced_only` | Restated in speeches/pressers, no delivery evidence |
| `no_public_evidence` | Nothing found since the original announcement |
| `superseded` | Rolled into or replaced by another initiative |

We deliberately do not use words like "stalled", "failed", or "broken
promise". This tracker is about delivery transparency, not scorekeeping.

## Sources

Evidence is drawn only from primary and near-primary sources:

- Hansard (UK Parliament)
- gov.uk publications
- India's Press Information Bureau (PIB)
- India's Ministry of External Affairs (MEA)
- Mainstream press reporting on the above

Every evidence entry links to its original source.

## Review process

A weekly automated pipeline (`pipeline/fetch.py` → `filter.py` →
`classify.py`) searches these sources for candidate evidence and opens a
pull request proposing additions to `data/commitments/*.yaml`. **No status
change or evidence entry is published without human review** — the
pipeline only ever appends to a commitment's `evidence:` list and, if it
thinks the status should change, adds a `pending_status_suggestion:` block
for a human to accept or reject. It never edits `status:` directly.

Monthly briefs are drafted the same way (`pipeline/brief.py`) and
hand-edited before publishing.

## Corrections

If you believe an entry is inaccurate, out of date, or missing evidence,
please email corrections@example.org (replace with the real inbox before
launch).
