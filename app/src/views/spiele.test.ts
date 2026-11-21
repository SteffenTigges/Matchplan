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

test("finished_match_shows_events_xg_timeline_and_player_table", () => {
  const fm = {
    fm_id: 1, stats: {}, momentum: null, zones: null, lineups: null,
    shots: [{ team: "BVB", player: "X", min: 10, x: 90, y: 30, xg: 0.4, xgot: 0.5, situation: "RegularPlay", type: "RightFoot", result: "goal" as const, own_goal: false }],
    players: [{ id: 7, team: "BVB", name: "Karim Adeyemi", minutes: 90, rating: 7.8, goals: 1, assists: 0, xg: 0.4, xa: 0.1, shots: 2, duels_won: 4, duels_lost: 3 }],
    events: [{ type: "goal" as const, min: 10, plus: null, home: true, player: "Karim Adeyemi", player_id: 7, assist: "Julian Brandt", score: [1, 0] as [number, number], own_goal: false, penalty: false },
             { type: "card" as const, min: 50, plus: null, home: false, player: "Y", player_id: null, card: "yellow" as const }],
  };
  const html = renderMatch(done, season, null, null, fm, null);
  expect(html).toContain("Spielverlauf");
  expect(html).toContain("Vorlage Julian Brandt");
  expect(html).toContain("xG-Verlauf");
  expect(html).toContain("Spielerstatistik");
  expect(html).toContain('href="#spieler/7"');
});

test("live_match_in_list_shows_live_chip", () => {
  const live = { ...soon, kickoff: new Date(Date.now() - 20 * 60000).toISOString(), score: [1, 0] as [number, number] };
  const html = renderMatchday(10, [live], season);
  expect(html).toContain("LIVE");
  expect(html).toContain("1:0");
});
