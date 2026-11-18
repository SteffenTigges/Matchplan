import { expect, test } from "vitest";
import type { FotmobMatch, Match, Season } from "../data";
import { ratingColor, renderAnalysis } from "./analysis";

const season: Season = {
  season: 2026, current_matchday: 10, updated_at: "",
  teams: {
    TSG: { name: "TSG Hoffenheim", short: "Hoffenheim", color: "#1961b5", crest: "" },
    S04: { name: "FC Schalke 04", short: "Schalke", color: "#004d9d", crest: "" },
  },
};
const m: Match = { id: 83231, kickoff: "2026-11-08T18:30:00Z", home: "TSG", away: "S04", finished: true, score: [2, 1], halftime: [2, 0],
  goals: [{ minute: 10, team: "TSG", scorer: "F. Asllani", penalty: false, own_goal: false }] };
const fm: FotmobMatch = {
  fm_id: 1,
  stats: { BallPossesion: [49, 51], expected_goals: [2.23, 2.6], total_shots: [15, 23], accurate_passes: [{ n: 366, pct: 80 }, { n: 346, pct: 74 }], fouls: [10, 9] },
  shots: [
    { team: "TSG", player: "Fisnik Asllani", min: 10, x: 95, y: 34, xg: 0.36, xgot: 0.5, situation: "RegularPlay", type: "RightFoot", result: "goal", own_goal: false },
    { team: "S04", player: "Kenan Karaman", min: 30, x: 90, y: 30, xg: 0.05, xgot: 0.1, situation: "RegularPlay", type: "LeftFoot", result: "saved", own_goal: false },
  ],
  momentum: [[0, 0], [1, -11], [2, 5], [3, -49]],
  zones: { home: { left: 28, center: 24, right: 48 }, away: { left: 35, center: 35, right: 30 } },
  lineups: {
    home: { team: "TSG", formation: "4-2-3-1", rating: 7.4, players: [{ name: "Oliver Baumann", pos_id: 11, rating: 7.5, captain: true, x: 0.5, y: 0.1 }] },
    away: { team: "S04", formation: "3-4-2-1", rating: 6.6, players: [{ name: "Loris Karius", pos_id: 11, rating: 6.1, captain: false, x: 0.5, y: 0.1 }] },
  },
  players: [],
};

test("renders_xg_and_possession", () => {
  const html = renderAnalysis(m, fm, season);
  expect(html).toContain("2,23");
  expect(html).toContain("2,60");
  expect(html).toContain("49 %");
  expect(html).toContain("366 (80 %)");
});

test("shotmap_scales_circles_by_xg", () => {
  const html = renderAnalysis(m, fm, season);
  const radii = [...html.matchAll(/<circle class="shot[^"]*" cx="[^"]+" cy="[^"]+" r="([\d.]+)"/g)].map((x) => Number(x[1]));
  expect(radii.length).toBe(2);
  expect(radii[0]).toBeGreaterThan(radii[1]);
  expect(html).toContain('class="shot goal"');
});

test("hides_missing_sections", () => {
  const bare = { ...fm, shots: [], momentum: null, zones: null, lineups: null };
  const html = renderAnalysis(m, bare, season);
  expect(html).not.toContain("Schusskarte");
  expect(html).not.toContain("Momentum");
  expect(html).not.toContain("Angriffszonen");
  expect(html).not.toContain("Aufstellungen");
  expect(html).toContain("Statistik");
});

test("no_fotmob_data_says_so", () => {
  expect(renderAnalysis(m, null, season)).toContain("Noch keine Spielstatistik");
});

test("rating_colours_match_scale", () => {
  expect(ratingColor(8.1)).toBe("#2f6fe4");
  expect(ratingColor(7.2)).toBe("#13a150");
  expect(ratingColor(6.7)).toBe("#f08a00");
  expect(ratingColor(5.9)).toBe("#e5484d");
});

test("momentum_path_has_one_point_per_minute", () => {
  const html = renderAnalysis(m, fm, season);
  const path = html.match(/<path class="mom" d="([^"]+)"/)![1];
  expect((path.match(/[ML]/g) ?? []).length).toBe(4 + 2);
});

test("lower_is_better_rows_highlight_the_smaller_value", () => {
  const html = renderAnalysis(m, fm, season);
  const row = html.slice(html.indexOf("Fouls"));
  expect(row.indexOf('class="w"')).toBeGreaterThan(-1);
});
