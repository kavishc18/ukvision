import { defineConfig } from "astro/config";

export default defineConfig({
  // Deployed as a GitHub Pages *project* site (kavishc18.github.io/ukvision/),
  // not a root/user site — both site and base must reflect the /ukvision
  // subpath or every asset and internal link resolves to the domain root.
  site: "https://kavishc18.github.io",
  base: "/ukvision",
  outDir: "./dist",
  build: {
    format: "directory",
  },
});
