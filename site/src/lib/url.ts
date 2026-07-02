/** Prefix an absolute internal path (e.g. "/briefs/") with the configured
 * Astro `base` (e.g. "/ukvision/"). Astro auto-prefixes assets it manages
 * (bundled CSS/JS) but never rewrites literal hrefs written in templates —
 * every hand-written internal link must go through this. */
export function withBase(path: string): string {
  const base = import.meta.env.BASE_URL; // e.g. "/ukvision/"
  const cleanBase = base.endsWith("/") ? base : `${base}/`;
  const cleanPath = path.startsWith("/") ? path.slice(1) : path;
  return cleanBase + cleanPath;
}
