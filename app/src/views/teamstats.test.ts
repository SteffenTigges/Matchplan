import { expect, test } from "vitest";
import type { TeamStats } from "../data";
import { renderMetricRanking, renderTeamStats } from "./teamstats";

const stats: TeamStats = {
  updated_at: "2026-11-18T16:00:00+00:00",
  categories: ["Allgemein", "Offensive", "Gegen den Ball"],
  metrics: [
    { key: "points", label: "Punkte", category: "Allgemein", higher_is_better: true, fmt: "int", approx: false },
    { key: "possession", label: "Ballbesitz Ø", category: "Allgemein", higher_is_better: true, fmt: "pct", approx: false },
    { key: "xg_pg", label: "xG pro Spiel", category: "Offensive", higher_is_better: true, fmt: "dec2", approx: false },
    { key: "field_tilt", label: "Field Tilt", category: "Gegen den Ball", higher_is_better: true, fmt: "pct", approx: true },
  ],
  teams: { TSG: { matches: 9, points: { value: 12, rank: 8 }, possession: { value: 0.534, rank: 3 }, xg_pg: { value: 1.6789, rank: 15 }, field_tilt: { value: 0.61, rank: 2 } } },
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
  expect(html).toContain('class="chip good" href="#rang/possession/TSG"');
  expect(html).toContain('class="chip bad" href="#rang/xg_pg/TSG"');
  expect(html).toContain('class="chip mid" href="#rang/points/TSG"');
});

test("marks_approximations", () => {
  expect(renderTeamStats("TSG", stats)).toContain('Field Tilt<span class="tag">Näherung</span>');
});

test("unknown_team_returns_empty", () => {
  expect(renderTeamStats("XXX", stats)).toBe("");
});

test("metrics_without_value_are_hidden", () => {
  const s = { ...stats, teams: { TSG: { ...stats.teams.TSG, field_tilt: { value: null, rank: null } } } } as unknown as TeamStats;
  expect(renderTeamStats("TSG", s)).not.toContain("Field Tilt");
});

test("ranking_lists_all_teams_sorted_and_highlights_team", () => {
  const s2: TeamStats = { ...stats, teams: { ...stats.teams, FCB: { matches: 9, xg_pg: { value: 2.9, rank: 1 } }, SVE: { matches: 8, xg_pg: { value: 0.8, rank: 18 } } } };
  const season = { season: 2026, current_matchday: 12, updated_at: "", teams: { FCB: { name: "FC Bayern", short: "Bayern", color: "#d00", crest: "" }, TSG: { name: "TSG", short: "Hoffenheim", color: "#16b", crest: "" }, SVE: { name: "SVE", short: "Elversberg", color: "#111", crest: "" } } };
  const html = renderMetricRanking("xg_pg", "TSG", s2, season);
  expect(html.indexOf("Bayern")).toBeLessThan(html.indexOf("Hoffenheim"));
  expect(html.indexOf("Hoffenheim")).toBeLessThan(html.indexOf("Elversberg"));
  expect(html).toContain('class="item me" href="#team/TSG"');
  expect(html).toContain("2,90");
  expect(html).toContain("höher ist besser");
});
