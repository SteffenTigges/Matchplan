import { expect, test } from "vitest";
import type { Lineups, Match, Season, TableRow } from "../data";
import { renderTable, renderTeam } from "./teams";

const keys = ["FCB", "BVB", "SCF", "RBL", "B04", "SVW", "SVE", "VFB", "TSG", "SGE", "HSV", "M05", "SCP", "FCA", "KOE", "FCU", "S04", "BMG"];
const season: Season = {
  season: 2026, current_matchday: 10, updated_at: "2026-11-18T16:00:00+00:00",
  teams: Object.fromEntries(keys.map((k) => [k, { name: `Team ${k}`, short: k, color: "#123456", crest: `${k}.png` }])),
};
const rows: TableRow[] = keys.map((k, i) => ({ rank: i + 1, team: k, played: 9, won: 1, draw: 1, lost: 1, goals: 10, against: 9, diff: 1, points: 30 - i, form: ["S", "U", "N"] }));
const matches: Match[] = [
  { id: 1, kickoff: "2026-11-07T14:30:00Z", home: "BMG", away: "HSV", finished: true, score: [1, 3], halftime: [1, 1], goals: [] },
  { id: 2, kickoff: "2026-11-21T14:30:00Z", home: "BMG", away: "BVB", finished: false, score: null, halftime: null, goals: [] },
];
const lineups: Lineups = { matchday: 10, fetched_at: "2026-11-18T16:00:00+00:00", teams: { BMG: {
  team: "Borussia Mönchengladbach", formation: "3-4-3", rows: [[{ player: { id: "a", name: "Nicolas", photo: null }, alternatives: [] }]],
  missing: [{ name: "Kō Itakura", kind: "Gelb-Rote Karte", note: "Sperre" }], updated_label: null, opponent: null, home: true, fetched_at: "2026-11-18T16:00:00+00:00" } } };

test("table_has_18_rows_in_rank_order", () => {
  const html = renderTable(rows, season);
  expect((html.match(/href="#team\//g) ?? []).length).toBe(18);
  expect(html.indexOf("#team/FCB")).toBeLessThan(html.indexOf("#team/BMG"));
});

test("form_squares_render_letters", () => {
  expect(renderTable(rows, season)).toContain('<i class="S">S</i><i class="U">U</i><i class="N">N</i>');
});

test("team_page_shows_next_match_and_absences", () => {
  const html = renderTeam("BMG", season, rows, matches, lineups);
  expect(html).toContain('href="#spiel/2"');
  expect(html).toContain("Kō Itakura");
  expect(html).toContain("3-4-3");
  expect(html).toContain("18. Platz");
});

test("team_page_lists_results", () => {
  expect(renderTeam("BMG", season, rows, matches, null)).toContain("1:3");
});
