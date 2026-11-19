import { expect, test } from "vitest";
import type { ScoutReport, Season, TeamStats } from "../data";
import { renderReport, renderScoutPicker } from "./scouting";
import { readFav, renderVerein, writeFav } from "./verein";

const season: Season = {
  season: 2026, current_matchday: 12, updated_at: "",
  teams: {
    BVB: { name: "Borussia Dortmund", short: "Dortmund", color: "#e3b505", crest: "bvb.png" },
    FCB: { name: "FC Bayern München", short: "Bayern", color: "#dc052d", crest: "fcb.png" },
  },
};
const sit = { goals: 0, xg: 0, shots: 0, share: 0 };
export const rep = (team: string): ScoutReport => ({
  team, matches: 11, fotmob_matches: 11,
  idea: { formations: [{ formation: "4-2-3-1", games: 8 }], tags: [{ text: "Hohes Pressing", evidence: [{ label: "PPDA", value: 7.9, fmt: "dec1", rank: 2 }] }] },
  next: { id: 83255, home: "FCB", away: "BVB", kickoff: "2026-12-04T19:30:00Z", tip: [2, 1], probs: [0.55, 0.22, 0.23] },
  strengths: [{ label: "xG pro Spiel", value: 2.4, fmt: "dec2", rank: 1 }], weaknesses: [{ label: "Flankenquote", value: 0.18, fmt: "pct", rank: 17 }],
  matchplan: [{ key: "setpieces", text: "Standards suchen: Bei ruhenden Bällen lassen sie viel zu.", evidence: [{ label: "Zugelassene xG nach Standards", value: 0.41, fmt: "dec2", rank: 16 }] }],
  findings: [{ key: "setpieces", text: "Standards suchen: Bei ruhenden Bällen lassen sie viel zu.", evidence: [{ label: "Zugelassene xG nach Standards", value: 0.41, fmt: "dec2", rank: 16 }] }],
  buildup: { metrics: [{ label: "Passquote", value: 0.88, fmt: "pct", rank: 2 }], zones: { left: 40, center: 25, right: 35 } },
  scoring: { situations: { Spielaufbau: { goals: 14, xg: 12.1, shots: 120, share: 0.7 }, Konter: { goals: 3, xg: 2, shots: 15, share: 0.15 }, Standard: { goals: 2, xg: 3, shots: 30, share: 0.1 }, Elfmeter: { goals: 1, xg: 0.8, shots: 1, share: 0.05 } }, bands: [1, 2, 3, 4, 5, 5], goals: 20, inside_box: 0.7, metrics: [] },
  conceding: { situations: null, bands: [0, 0, 1, 1, 2, 4], goals: 8, opp_zones: null, metrics: [] },
  setpieces: { metrics: [], goals_for: 2, goals_against: 3, corners_against: 4.1 },
  key_players: [{ id: 194165, name: "Harry Kane", pos: "ST", minutes: 900, goals: 12, assists: 2, rating: 8.1, xg90: 0.95, xa90: 0.2, why: ["Tore (99. Perzentil)"] }],
  lines: { Angriff: { id: 194165, name: "Harry Kane", rating: 8.1, minutes: 900 } },
  load: [{ id: 194165, name: "Harry Kane", minutes: 270, full: true }],
  absences: [{ name: "Jamal Musiala", kind: "Verletzung", note: "Wadenbeinbruch" }],
  reaction: { ht_lead: { games: 6, points: 18 }, ht_draw: { games: 3, points: 5 }, ht_trail: { games: 2, points: 3 }, points_from_behind: 4, points_dropped: 1, late_for: 5, late_against: 4, goals_for: 20, goals_against: 8 },
});

test("report_renders_all_areas", () => {
  const html = renderReport(rep("FCB"), season, null);
  for (const t of ["Überblick", "Mit Ball", "Gegen den Ball", "Personal", "Spielverlauf", "Spielidee", "Spielaufbau", "So treffen sie", "So kassieren sie", "Standards", "Schlüsselspieler", "Personal &amp; Belastung", "Reaktion im Spielverlauf", "Schiedsrichter", "Matchplan"])
    expect(html).toContain(t);
  expect(html).toContain("4-2-3-1");
  expect(html).toContain("Harry Kane");
  expect(html).toContain('href="#spieler/194165"');
});

test("missing_section_says_no_data", () => {
  const html = renderReport(rep("FCB"), season, null);
  const part = html.slice(html.indexOf("So kassieren sie"));
  expect(part).toContain("Keine Schussdaten");
});

test("findings_show_evidence", () => {
  const html = renderReport(rep("FCB"), season, null);
  expect(html).toContain("Standards suchen");
  expect(html).toContain("Zugelassene xG nach Standards");
  expect(html).toContain("0,41");
  expect(html).toContain("Platz 16");
});

test("duels_only_in_club_view", () => {
  expect(renderReport(rep("FCB"), season, null)).not.toContain("Duelle");
  const mine = { ...rep("BVB"), lines: { Angriff: { id: 1, name: "Serhou Guirassy", rating: 7.4, minutes: 800 } } };
  const html = renderReport(rep("FCB"), season, mine);
  expect(html).toContain("Duelle");
  expect(html).toContain("Serhou Guirassy");
});

test("picker_lists_all_teams", () => {
  const html = renderScoutPicker(season, "#scouting/");
  expect(html).toContain('href="#scouting/BVB"');
  expect(html).toContain('href="#scouting/FCB"');
});

test("picker_without_storage", () => {
  const broken = { getItem: () => { throw new Error("blocked"); }, setItem: () => { throw new Error("blocked"); } } as unknown as Storage;
  expect(readFav(broken)).toBeNull();
  expect(() => writeFav("BVB", broken)).not.toThrow();
  const html = renderVerein(null, season, null, null, null);
  expect(html).toContain('href="#verein/BVB"');
});

const ts: TeamStats = {
  updated_at: "", categories: ["Offensive"],
  metrics: [{ key: "xg_pg", label: "xG pro Spiel", category: "Offensive", higher_is_better: true, fmt: "dec2", approx: false },
            { key: "against_pg", label: "Gegentore pro Spiel", category: "Defensive", higher_is_better: false, fmt: "dec2", approx: false }],
  teams: { BVB: { matches: 11, xg_pg: { value: 1.9, rank: 4 }, against_pg: { value: 0.8, rank: 1 } }, FCB: { matches: 11, xg_pg: { value: 2.4, rank: 1 }, against_pg: { value: 1.0, rank: 3 } } },
};

test("wir_gegen_sie_rows", () => {
  const html = renderVerein("BVB", season, rep("BVB"), rep("FCB"), ts);
  expect(html).toContain("Wir gegen sie");
  expect(html).toContain("xG pro Spiel");
  expect(html).toContain("1,90");
  expect(html).toContain("2,40");
  expect(html).toContain("Die 3 wichtigsten Erkenntnisse");
  expect(html).toContain('href="#scouting/FCB/personal"');
  expect(html).toContain('href="#status"');
});
