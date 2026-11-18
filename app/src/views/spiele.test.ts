import { expect, test } from "vitest";
import type { Match, Season } from "../data";
import { renderMatch, renderMatchday } from "./spiele";

const season: Season = {
  season: 2026, current_matchday: 10, updated_at: "2026-11-18T16:00:00+00:00",
  teams: {
    BVB: { name: "Borussia Dortmund", short: "Dortmund", color: "#e3b505", crest: "bvb.png" },
    SVE: { name: "SV 07 Elversberg", short: "Elversberg", color: "#1c1c1c", crest: "sve.png" },
    FCB: { name: "FC Bayern München", short: "Bayern", color: "#dc052d", crest: "fcb.png" },
    KOE: { name: "1. FC Köln", short: "Köln", color: "#ed1c24", crest: "koe.png" },
  },
};
const done: Match = {
  id: 83228, kickoff: "2026-11-07T14:30:00Z", home: "BVB", away: "SVE", finished: true, score: [2, 1], halftime: [0, 0],
  goals: [
    { minute: 55, team: "BVB", scorer: "F. Nmecha", penalty: true, own_goal: false },
    { minute: 81, team: "SVE", scorer: "R. Khedira", penalty: false, own_goal: true },
  ],
};
const open: Match = { id: 83237, kickoff: null, home: "FCB", away: "KOE", finished: false, score: null, halftime: null, goals: [] };
const soon: Match = { ...open, id: 83238, kickoff: "2026-11-20T19:30:00Z" };

test("renders_score_for_finished_match", () => {
  expect(renderMatchday(9, [done], season)).toContain("2:1");
});

test("renders_open_kickoff", () => {
  const html = renderMatchday(10, [open], season);
  expect(html).toContain("Termin offen");
  expect(html).not.toContain("0:0");
});

test("renders_kickoff_time_for_upcoming", () => {
  expect(renderMatchday(10, [soon], season)).toContain("Fr. 20.11., 20:30");
});

test("links_to_match_page_and_neighbour_matchdays", () => {
  const html = renderMatchday(9, [done], season);
  expect(html).toContain('href="#spiel/83228"');
  expect(html).toContain('href="#spiele/8"');
  expect(html).toContain('href="#spiele/10"');
});

test("renders_goal_markers_for_penalty_and_own_goal", () => {
  const html = renderMatch(done, season, null, null);
  expect(html).toContain("55'");
  expect(html).toContain("Elfmeter");
  expect(html).toContain("Eigentor");
  expect(html).toContain("Halbzeit 0:0");
});

test("upcoming_match_without_lineups_says_so", () => {
  expect(renderMatch(soon, season, null, null)).toContain("Noch keine voraussichtliche Aufstellung");
});
