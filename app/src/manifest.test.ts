import { readFileSync } from "node:fs";
import { expect, test } from "vitest";

// Pfade relativ halten: GitHub Pages unterscheidet Groß-/Kleinschreibung (/Matchplan/ ≠ /matchplan/).
const manifest = JSON.parse(readFileSync(new URL("../public/manifest.webmanifest", import.meta.url), "utf8"));
const viteConfig = readFileSync(new URL("../vite.config.ts", import.meta.url), "utf8");

test("manifest_paths_are_relative", () => {
  expect(manifest.start_url).toBe("./");
  expect(manifest.scope).toBe("./");
});

test("vite_base_is_relative", () => {
  expect(viteConfig).toContain('base: "./"');
});
