import fs from "node:fs";
import path from "node:path";
import yaml from "js-yaml";

const DATA_DIR = path.resolve(process.cwd(), "..", "data", "commitments");

export type Evidence = {
  date: string;
  url: string;
  source_type: string;
  summary: string;
};

export type Commitment = {
  id: string;
  pillar: "technology" | "trade_digital" | "education_tech";
  title: string;
  commitment_text: string;
  source_url: string;
  announced: string;
  owners: string[];
  status: "delivered" | "in_progress" | "announced_only" | "no_public_evidence" | "superseded";
  status_rationale: string;
  evidence: Evidence[];
  suggested_pq?: string;
  last_reviewed: string;
};

let cache: Commitment[] | null = null;

export function loadCommitments(): Commitment[] {
  if (cache) return cache;
  const files = fs.readdirSync(DATA_DIR).filter((f) => f.endsWith(".yaml"));
  const items = files.map((f) => {
    const raw = fs.readFileSync(path.join(DATA_DIR, f), "utf-8");
    // JSON_SCHEMA keeps YAML date-looking scalars (e.g. `2026-01-30`) as
    // plain strings instead of auto-casting them to JS Date objects.
    return yaml.load(raw, { schema: yaml.JSON_SCHEMA }) as Commitment;
  });
  items.sort((a, b) => a.title.localeCompare(b.title));
  cache = items;
  return items;
}

export function getCommitment(id: string): Commitment | undefined {
  return loadCommitments().find((c) => c.id === id);
}

export function lastActivityDate(c: Commitment): string {
  if (!c.evidence || c.evidence.length === 0) return c.announced;
  return c.evidence.reduce((latest, e) => (e.date > latest ? e.date : latest), c.evidence[0].date);
}

export const PILLAR_LABELS: Record<Commitment["pillar"], string> = {
  technology: "Technology",
  trade_digital: "Trade & Digital",
  education_tech: "Education & Tech",
};

export const STATUS_LABELS: Record<Commitment["status"], string> = {
  delivered: "Delivered",
  in_progress: "In progress",
  announced_only: "Announced only",
  no_public_evidence: "No public evidence",
  superseded: "Superseded",
};
