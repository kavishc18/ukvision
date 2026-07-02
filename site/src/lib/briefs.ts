import fs from "node:fs";
import path from "node:path";

const BRIEFS_DIR = path.resolve(process.cwd(), "src", "content", "briefs");

export type BriefMeta = {
  slug: string;
  title: string;
  date: string;
  body: string;
};

export function loadBriefs(): BriefMeta[] {
  if (!fs.existsSync(BRIEFS_DIR)) return [];
  const files = fs.readdirSync(BRIEFS_DIR).filter((f) => f.endsWith(".md"));
  const briefs = files.map((f) => {
    const raw = fs.readFileSync(path.join(BRIEFS_DIR, f), "utf-8");
    const firstLine = raw.split("\n").find((l) => l.trim().startsWith("#")) ?? f;
    const title = firstLine.replace(/^#+\s*/, "").trim();
    const slug = f.replace(/\.md$/, "");
    return { slug, title, date: slug.replace("brief-", ""), body: raw };
  });
  briefs.sort((a, b) => b.slug.localeCompare(a.slug));
  return briefs;
}
