import { expect, test } from "vitest";
import type { Match, ModelCheck, Prediction, Season } from "../data";
import { renderAllResults, renderModelCheck, renderPriorPrediction, renderPrognosis, tipLine } from "./prognose";

const season: Season = {
  season: 2026, current_matchday: 12, updated_at: "2026-11-19T10:00:00+00:00",
  teams: {
    FCB: { name: "FC Bayern München", short: "Bayern", color: "#dc052d", crest: "fcb.png" },
    SCP: { name: "SC Paderborn 07", short: "Paderborn", color: "#005ca9", crest: "scp.png" },
  },
};
const m: Match = { id: 83255, kickoff: "2026-12-04T19:30:00Z", home: "FCB", away: "SCP", finished: false, score: null, halftime: null, goals: [] };

const matrix = Array.from({ length: 6 }, (_, i) => Array.from({ length: 6 }, (_, j) => (i === 2 && j === 0 ? 0.12 : i === 1 && j === 1 ? 0.05 : 0.02)));
const p: Prediction = {
  home: "FCB", away: "SCP", kickoff: m.kickoff, made_at: "2026-11-19T10:00:00+00:00",
  xg: [2.61, 0.74], probs: [0.78, 0.14, 0.08], tip: [2, 0], tip_prob: 0.12, matrix,
  markets: { over25: 0.61, btts: 0.38, home_clean_sheet: 0.48, away_clean_sheet: 0.07 },
  odds: { home: 0.81, draw: 0.12, away: 0.07, source: "Schnitt der Buchmacher" },
  scorers: {
    home: [{ name: "Kane", li_id: "harry-kane_1", fm_id: 2, photo: "kane.jpg", minutes: 80, lam: 0.9, p: 0.593 }],
    away: [{ name: "Muslija", li_id: "filip-muslija_2", fm_id: 3, photo: null, minutes: 80, lam: 0.2, p: 0.181 }],
  },
  xi: { home: [], away: [] },
  why: {
    attack: [1.45, 0.82], defence: [0.71, 1.25], xgf: [2.4, 1.1], xga: [0.9, 1.9], n: [11, 11], form: [2.6, 0.8],
    means: [1.72, 1.31], rho: -0.06, absence_factor: [[0.95, 1.06], [1, 1]],
    absences: { home: [{ name: "Jamal Musiala", fm_id: 5, xg_share: 0.1, minutes_share: 0.9 }], away: [] },
  },
};

test("renders_tip_and_chances", () => {
  const html = renderPrognosis(m, p, season);
  expect(html).toContain("2:0");
  expect(html).toContain("78 %");
  expect(html).toContain("Bayern gewinnt wahrscheinlich");
  expect(html).toContain('href="#prognose/83255"');
  expect(html).toContain("Wer trifft?");
  expect(html).toContain("59 %");
  expect(html).toContain("Jamal Musiala");
});

test("tip_line_for_matchday_list", () => {
  const html = tipLine(p, season);
  expect(html).toContain("Tipp 2:0");
  expect(html).toContain("Kane");
});

test("all_results_sorted_desc", () => {
  const html = renderAllResults(m, p, season);
  const first = html.indexOf("2:0");
  const second = html.indexOf("1:1");
  expect(first).toBeGreaterThan(-1);
  expect(second).toBeGreaterThan(first);
  expect(html).toContain("Über 2,5");
  expect(html).toContain("61 %");
});

test("hides_odds_when_missing", () => {
  expect(renderPrognosis(m, p, season)).toContain("Buchmacher");
  expect(renderPrognosis(m, { ...p, odds: null }, season)).not.toContain("Gegencheck");
});

test("finished_match_shows_prior_prediction", () => {
  const done: Match = { ...m, finished: true, score: [2, 0] };
  const html = renderPriorPrediction(done, { ...p, lineup_hits: { home: 9, away: null } }, season);
  expect(html).toContain("Tipp war 2:0");
  expect(html).toContain("Ergebnis genau getroffen");
  expect(html).toContain("9 von 11");
});

test("model_check_card", () => {
  const mc: ModelCheck = {
    updated_at: "2026-11-19T10:00:00+00:00",
    calibration: { home: 1.71, away: 1.33, rho: -0.06, matches: 918, seasons: "2023–2025", fetched_at: "x" },
    check: { matches: 99, tendency_rate: 0.52, exact_rate: 0.11, brier: 0.59, odds_matches: 90, brier_model_same: 0.6, brier_odds: 0.57,
      by_matchday: [{ md: 1, matches: 9, tendency: 4, exact: 1, brier: 0.63 }] },
  };
  const html = renderModelCheck(mc);
  expect(html).toContain("52 %");
  expect(html).toContain("Brier-Score");
  expect(html).toContain("0,57");
});

test("cross_check_shows_elo_without_odds", () => {
  const html = renderPrognosis(m, { ...p, odds: null, elo: { home: 1890, away: 1610, probs: [0.7, 0.18, 0.12] } }, season);
  expect(html).toContain("Gegencheck");
  expect(html).toContain("Bayern 1890");
  expect(html).toContain("70 %");
  expect(html).toContain("Buchmacherquoten folgen");
});
