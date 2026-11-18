import { expect, test } from "vitest";
import type { TeamStats } from "../data";
import { renderTeamStats } from "./teamstats";

const stats: TeamStats = {
  updated_at: "2026-11-18T16:00:00+00:00",
  categories: ["Allgemein", "Offensive", "Gegen den Ball"],
  metrics: [
    { key: "points", label: "Punkte", category: "Allgemein", higher_is_better: true, fmt: "int", approx: false },
    { key: "possession", label: "Ballbesitz Ø", category: "Allgemein", higher_is_better: true, fmt: "pct", approx: false },
    { key: "xg_pg", label: "xG pro Spiel", category: "Offensive", higher_is_better: true, fmt: "dec2", approx: false },
    { key: "ppda", label: "PPDA", category: "Gegen den Ball", higher_is_better: false, fmt: "dec1", approx: true },
  ],
  teams: { TSG: { matches: 9, points: { value: 12, rank: 8 }, possession: { value: 0.534, rank: 3 }, xg_pg: { value: 1.6789, rank: 15 }, ppda: { value: 9.84, rank: 2 } } },
};

test("renders_all_categories", () => {
  const html = renderTeamStats("TSG", stats);
  for (const c of stats.categories) expect(html).toContain(c);
  expect(html).toContain("53 %");
  expect(html).toContain("1,68");
  expect(html).toContain("9 Spiele");
});

test("rank_chip_colours", () => {
  const html = renderTeamStats("TSG", stats);
  expect(html).toContain('<span class="chip good">3.</span>');
  expect(html).toContain('<span class="chip bad">15.</span>');
  expect(html).toContain('<span class="chip mid">8.</span>');
});

test("marks_approximations", () => {
  expect(renderTeamStats("TSG", stats)).toContain('PPDA<span class="tag">Näherung</span>');
});

test("unknown_team_returns_empty", () => {
  expect(renderTeamStats("XXX", stats)).toBe("");
});
